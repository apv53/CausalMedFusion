"""
Model Registry — Singleton Model Loader
========================================
Loads DenseNet121 (CXR) and RadBERT-RoBERTa (reports) once at import
time and keeps them warm in memory for the lifetime of the process.
"""

from __future__ import annotations

import torch

# ── Device ──────────────────────────────────────────────────────────

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Lazy-loaded singletons ──────────────────────────────────────────

_cxr_model = None
_report_model = None
_report_tokenizer = None


def load_cxr_model():
    """Load DenseNet121 from torchxrayvision (called once at startup)."""
    global _cxr_model
    if _cxr_model is not None:
        return

    import torchxrayvision as xrv

    print("[MODEL REGISTRY] Loading DenseNet121 (CXR) ...", flush=True)
    _cxr_model = xrv.models.DenseNet(weights="densenet121-res224-all")
    _cxr_model = _cxr_model.to(DEVICE)
    _cxr_model.eval()
    print(f"[MODEL REGISTRY] DenseNet121 loaded on {DEVICE}", flush=True)


def load_report_model():
    """Load RadBERT-RoBERTa from HuggingFace (called once at startup)."""
    global _report_model, _report_tokenizer
    if _report_model is not None:
        return

    from transformers import AutoTokenizer, AutoModel

    MODEL_NAME = "zzxslp/RadBERT-RoBERTa-4m"
    print(f"[MODEL REGISTRY] Loading {MODEL_NAME} ...", flush=True)

    _report_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _report_model = AutoModel.from_pretrained(MODEL_NAME)
    _report_model = _report_model.to(DEVICE)
    _report_model.eval()
    print(f"[MODEL REGISTRY] {MODEL_NAME} loaded on {DEVICE}", flush=True)


def get_cxr_model():
    """Return the CXR model (lazily loads if not present)."""
    if _cxr_model is None:
        load_cxr_model()
    return _cxr_model


def get_report_model():
    """Return the report model (lazily loads if not present)."""
    if _report_model is None:
        load_report_model()
    return _report_model


def get_report_tokenizer():
    """Return the report tokenizer (lazily loads if not present)."""
    if _report_tokenizer is None:
        load_report_model()
    return _report_tokenizer
