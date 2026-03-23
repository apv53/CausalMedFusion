"""
Labs Processing Microservice — Entry Point
============================================
FastAPI application that exposes the lab report processing endpoint.

Run:
    uvicorn labs_service.main:app --host 0.0.0.0 --port 8003 --reload
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# ── Ensure project root is on sys.path ──────────────────────────────
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from labs_service.router import router
from shared.db_manager import close_pool, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB tables on startup, close pool on shutdown."""
    await init_db()
    yield
    await close_pool()


app = FastAPI(
    title="CausalMedFusion — Labs Processing Service",
    description=(
        "Lab Processing Microservice. Extracts structured lab measurements "
        "from PDFs, applies Z-score normalisation, computes temporal "
        "coordinates, and persists to PostgreSQL JSONB."
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
app.include_router(router, tags=["Lab Processing"])


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness probe."""
    return {"status": "healthy", "service": "labs-processing"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("labs_service.main:app", host="0.0.0.0", port=8003, reload=True)
