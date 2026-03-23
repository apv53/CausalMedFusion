"""
Embedding Service Router
========================
Endpoints for extracting embeddings from raw clinical tensors stored
in the shared HDF5 vault.

- POST /v1/embed-cxr     — single CXR image embedding
- POST /v1/embed-report  — single report text embedding
- POST /v1/embed-batch   — batch embedding for multiple files of one modality
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from fastapi import APIRouter, HTTPException

# ── Ensure project root is on sys.path ──────────────────────────────
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from embedding_service.model_registry import (
    DEVICE,
    get_cxr_model,
    get_report_model,
    get_report_tokenizer,
)
from embedding_service.schemas import (
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
    CXREmbeddingRequest,
    EmbeddingResponse,
    ReportEmbeddingRequest,
)
from shared.hdf5_embeddings_manager import (
    read_raw_dataset,
    save_embedding,
)

router = APIRouter()

# ── Constants ───────────────────────────────────────────────────────

BATCH_SIZE = 16
MAX_LENGTH = 512  # RadBERT tokenizer max length


# ── Helpers ─────────────────────────────────────────────────────────

def _embed_cxr_tensor(raw_tensor: np.ndarray) -> np.ndarray:
    """
    Run a single CXR tensor through DenseNet121 → pool → normalise.

    Input : numpy array of shape (1, 224, 224)
    Output: numpy array of shape (1024,)
    """
    model = get_cxr_model()
    tensor = torch.from_numpy(raw_tensor).unsqueeze(0).to(DEVICE)  # (1, 1, 224, 224)

    with torch.no_grad():
        features = model.features(tensor)
        pooled = torch.nn.functional.adaptive_avg_pool2d(features, (1, 1))
        pooled = pooled.view(pooled.size(0), -1)
        pooled = torch.nn.functional.normalize(pooled, dim=-1)

    return pooled.cpu().numpy().squeeze(0)  # (1024,)


def _embed_report_text(text: str) -> np.ndarray:
    """
    Run a single report string through RadBERT → CLS → normalise.

    Output: numpy array of shape (768,)
    """
    model = get_report_model()
    tokenizer = get_report_tokenizer()

    inputs = tokenizer(
        text,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        cls_embedding = outputs.last_hidden_state[:, 0, :]
        cls_embedding = torch.nn.functional.normalize(cls_embedding, dim=-1)

    return cls_embedding.cpu().numpy().squeeze(0)  # (768,)


def _embed_cxr_batch(tensors: list[np.ndarray]) -> list[np.ndarray]:
    """
    Batch-embed multiple CXR tensors.

    Input : list of numpy arrays, each of shape (1, 224, 224)
    Output: list of numpy arrays, each of shape (1024,)
    """
    model = get_cxr_model()
    results = []

    for i in range(0, len(tensors), BATCH_SIZE):
        batch = tensors[i: i + BATCH_SIZE]
        stacked = torch.from_numpy(np.stack(batch, axis=0)).to(DEVICE)

        with torch.no_grad():
            features = model.features(stacked)
            pooled = torch.nn.functional.adaptive_avg_pool2d(features, (1, 1))
            pooled = pooled.view(pooled.size(0), -1)
            pooled = torch.nn.functional.normalize(pooled, dim=-1)

        for j in range(pooled.size(0)):
            results.append(pooled[j].cpu().numpy())

    return results


def _embed_report_batch(texts: list[str]) -> list[np.ndarray]:
    """
    Batch-embed multiple report texts.

    Output: list of numpy arrays, each of shape (768,)
    """
    model = get_report_model()
    tokenizer = get_report_tokenizer()
    results = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]

        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            cls = outputs.last_hidden_state[:, 0, :]
            cls = torch.nn.functional.normalize(cls, dim=-1)

        for j in range(cls.size(0)):
            results.append(cls[j].cpu().numpy())

    return results


# ── Single CXR Endpoint ────────────────────────────────────────────

@router.post(
    "/v1/embed-cxr",
    response_model=EmbeddingResponse,
    summary="Extract embedding for a single CXR image",
)
async def embed_cxr(req: CXREmbeddingRequest):
    dataset_name = f"{req.window_id}_cxr_{req.file_id}"

    # 1. Read raw tensor from vault
    try:
        raw_data, attrs = read_raw_dataset(req.visit_id, dataset_name)
    except KeyError as exc:
        raise HTTPException(404, str(exc))

    if not isinstance(raw_data, np.ndarray):
        raise HTTPException(422, f"Expected numpy array for CXR, got {type(raw_data).__name__}")

    # 2. Extract embedding
    try:
        embedding = _embed_cxr_tensor(raw_data)
    except Exception as exc:
        raise HTTPException(500, f"Embedding extraction failed: {exc}")

    # 3. Save to embeddings vault
    save_embedding(req.visit_id, dataset_name, embedding, attrs)

    return EmbeddingResponse(
        visit_id=req.visit_id,
        file_id=req.file_id,
        embedding_shape=list(embedding.shape),
    )


# ── Single Report Endpoint ──────────────────────────────────────────

@router.post(
    "/v1/embed-report",
    response_model=EmbeddingResponse,
    summary="Extract embedding for a single clinical report",
)
async def embed_report(req: ReportEmbeddingRequest):
    dataset_name = f"{req.window_id}_report_{req.file_id}"

    # 1. Read raw text from vault
    try:
        raw_data, attrs = read_raw_dataset(req.visit_id, dataset_name)
    except KeyError as exc:
        raise HTTPException(404, str(exc))

    if not isinstance(raw_data, str):
        raise HTTPException(422, f"Expected string for report, got {type(raw_data).__name__}")

    # 2. Extract embedding
    try:
        embedding = _embed_report_text(raw_data)
    except Exception as exc:
        raise HTTPException(500, f"Embedding extraction failed: {exc}")

    # 3. Save to embeddings vault
    save_embedding(req.visit_id, dataset_name, embedding, attrs)

    return EmbeddingResponse(
        visit_id=req.visit_id,
        file_id=req.file_id,
        embedding_shape=list(embedding.shape),
    )


# ── Batch Endpoint ──────────────────────────────────────────────────

@router.post(
    "/v1/embed-batch",
    response_model=BatchEmbeddingResponse,
    summary="Batch-embed multiple files of one modality",
)
async def embed_batch(req: BatchEmbeddingRequest):
    if req.modality not in ("cxr", "report"):
        raise HTTPException(422, f"Unknown modality '{req.modality}'. Expected 'cxr' or 'report'.")

    # 1. Read all raw data
    raw_items: list[tuple[str, np.ndarray | str, dict]] = []  # (dataset_name, data, attrs)
    errors: list[str] = []

    for item in req.items:
        dataset_name = f"{item.window_id}_{req.modality}_{item.file_id}"
        try:
            data, attrs = read_raw_dataset(req.visit_id, dataset_name)
            raw_items.append((dataset_name, data, attrs, item.file_id))
        except KeyError as exc:
            errors.append(f"[{dataset_name}] {exc}")

    if not raw_items:
        return BatchEmbeddingResponse(
            processed=0,
            failed=len(errors),
            errors=errors,
            status="failed" if errors else "success",
        )

    # 2. Extract embeddings in batches
    results: list[EmbeddingResponse] = []

    if req.modality == "cxr":
        tensors = [item[1] for item in raw_items]
        embeddings = _embed_cxr_batch(tensors)
    else:
        texts = [item[1] for item in raw_items]
        embeddings = _embed_report_batch(texts)

    # 3. Save each embedding
    for (dataset_name, _data, attrs, file_id), emb in zip(raw_items, embeddings):
        try:
            save_embedding(req.visit_id, dataset_name, emb, attrs)
            results.append(EmbeddingResponse(
                visit_id=req.visit_id,
                file_id=file_id,
                embedding_shape=list(emb.shape),
            ))
        except Exception as exc:
            errors.append(f"[{dataset_name}] Save failed: {exc}")

    return BatchEmbeddingResponse(
        processed=len(results),
        failed=len(errors),
        results=results,
        errors=errors,
    )
