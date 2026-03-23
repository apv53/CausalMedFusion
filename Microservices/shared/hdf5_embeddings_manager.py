"""
HDF5 Embeddings Manager
=======================
Process-safe helpers for reading raw tensors from the clinical vault
and persisting embeddings into a separate HDF5 file.

Storage layout (embeddings)
---------------------------
Groups  : ``/<visit_id>/``
Datasets: ``<window_id>_<modality>_<file_id>``
          e.g.  ``1_cxr_42``, ``2_report_55``
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from filelock import FileLock

# ── Configuration ────────────────────────────────────────────────────

_project_root = Path(__file__).resolve().parent.parent.parent

DEFAULT_RAW_VAULT_PATH = os.environ.get(
    "HDF5_VAULT_PATH",
    str(_project_root / "storage" / "clinical_tensors_raw" / "clinical_vault.h5"),
)

DEFAULT_EMBEDDINGS_PATH = os.environ.get(
    "HDF5_EMBEDDINGS_PATH",
    str(_project_root / "storage" / "clinical_embeddings" / "clinical_embeddings.h5"),
)


def _resolve(path_str: str) -> Path:
    """Resolve path and ensure parent directories exist."""
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _lock(path: Path) -> FileLock:
    return FileLock(f"{path}.lock", timeout=10)


# ── Read from Raw Vault ─────────────────────────────────────────────

def read_raw_dataset(
    visit_id: str,
    dataset_name: str,
    vault_path: str | None = None,
) -> tuple[np.ndarray | str, dict[str, Any]]:
    """
    Read a single dataset and its attributes from the raw clinical vault.

    Returns
    -------
    tuple[data, attributes]
        data: numpy array (images) or string (reports)
        attributes: dict of all HDF5 attributes on the dataset
    """
    path = _resolve(vault_path or DEFAULT_RAW_VAULT_PATH)

    with _lock(path):
        with h5py.File(str(path), "r") as f:
            if visit_id not in f:
                raise KeyError(f"Visit group '{visit_id}' not found in vault")
            grp = f[visit_id]
            if dataset_name not in grp:
                raise KeyError(f"Dataset '{dataset_name}' not found in group '{visit_id}'")

            ds = grp[dataset_name]
            data = ds[()]
            attrs = dict(ds.attrs)

            # Decode bytes to string for report data
            if isinstance(data, bytes):
                data = data.decode("utf-8")

    return data, attrs


def read_embedding_dataset(
    visit_id: str,
    dataset_name: str,
    embeddings_path: str | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Read a single dataset and its attributes from the clinical embeddings vault.

    Parameters
    ----------
    visit_id : str
        e.g. ``'000005'``
    dataset_name : str
        e.g. ``'1_cxr_42'``
    embeddings_path : str, optional
        Override default embeddings path.

    Returns
    -------
    tuple[data, attributes]
        data: numpy array (PyTorch embeddings)
        attributes: dict of all HDF5 attributes on the dataset
    """
    path = _resolve(embeddings_path or DEFAULT_EMBEDDINGS_PATH)

    with _lock(path):
        with h5py.File(str(path), "r") as f:
            if visit_id not in f:
                raise KeyError(f"Visit group '{visit_id}' not found in embeddings vault")
            grp = f[visit_id]
            if dataset_name not in grp:
                raise KeyError(f"Dataset '{dataset_name}' not found in group '{visit_id}'")

            ds = grp[dataset_name]
            data = ds[()]
            attrs = dict(ds.attrs)

    return data, attrs


def list_datasets_in_group(
    visit_id: str,
    modality_prefix: str | None = None,
    vault_path: str | None = None,
) -> list[str]:
    """
    List all dataset names under a visit group, optionally filtered by modality.

    Parameters
    ----------
    modality_prefix : str, optional
        Filter datasets containing this modality string, e.g. ``'cxr'`` or ``'report'``.
    """
    path = _resolve(vault_path or DEFAULT_RAW_VAULT_PATH)
    if not path.exists():
        return []

    with _lock(path):
        with h5py.File(str(path), "r") as f:
            if visit_id not in f:
                return []
            names = list(f[visit_id].keys())

    if modality_prefix:
        names = [n for n in names if f"_{modality_prefix}_" in n]

    return names


# ── Write Embeddings ────────────────────────────────────────────────

def save_embedding(
    visit_id: str,
    dataset_name: str,
    embedding: np.ndarray,
    attributes: dict[str, Any],
    embeddings_path: str | None = None,
) -> None:
    """
    Persist an embedding vector + copied attributes to the embeddings vault.
    """
    path = _resolve(embeddings_path or DEFAULT_EMBEDDINGS_PATH)

    with _lock(path):
        with h5py.File(str(path), "a") as f:
            if "description" not in f.attrs:
                f.attrs["description"] = "CausalMedFusion Clinical Embeddings"

            grp = f.require_group(visit_id)
            if dataset_name in grp:
                del grp[dataset_name]

            ds = grp.create_dataset(
                dataset_name,
                data=embedding.astype(np.float32),
                compression="gzip",
                compression_opts=4,
            )

            # Copy all attributes from the raw tensor
            for key, value in attributes.items():
                ds.attrs[key] = value


# ── Check Existence ─────────────────────────────────────────────────

def embedding_exists(
    visit_id: str,
    dataset_name: str,
    embeddings_path: str | None = None,
) -> bool:
    """Check if an embedding already exists in the vault."""
    path = _resolve(embeddings_path or DEFAULT_EMBEDDINGS_PATH)
    if not path.exists():
        return False

    with _lock(path):
        with h5py.File(str(path), "r") as f:
            if visit_id not in f:
                return False
            return dataset_name in f[visit_id]
