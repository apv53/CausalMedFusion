"""
Embedding Microservice — Entry Point
=====================================
FastAPI application that serves CXR and report embedding extraction.
Models are loaded once at startup and kept warm in memory.

Run:
    uvicorn embedding_service.main:app --host 0.0.0.0 --port 8005
"""

from __future__ import annotations

import sys
from pathlib import Path
from contextlib import asynccontextmanager

# ── Ensure project root is on sys.path ──────────────────────────────
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from embedding_service.router import router
from embedding_service.model_registry import load_cxr_model, load_report_model


# ── Lifespan: load models at startup ────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models into memory once before the service starts."""
    print("[STARTUP] Loading embedding models ...", flush=True)
    load_cxr_model()
    load_report_model()
    print("[STARTUP] All models loaded. Service ready.", flush=True)
    yield
    print("[SHUTDOWN] Embedding service shutting down.", flush=True)


app = FastAPI(
    title="CausalMedFusion — Embedding Service",
    description=(
        "Extracts dense vector embeddings from raw clinical data stored "
        "in the shared HDF5 vault. Supports CXR images (DenseNet121, "
        "1024-dim) and clinical reports (RadBERT-RoBERTa, 768-dim)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount router ────────────────────────────────────────────────────
app.include_router(router, tags=["Embedding Extraction"])


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness probe."""
    return {"status": "healthy", "service": "embedding"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("embedding_service.main:app", host="0.0.0.0", port=8005, reload=False)
