"""
Report Processing Microservice — Entry Point
=============================================
FastAPI application that exposes the clinical report processing endpoint.

Run:
    uvicorn report_service.main:app --host 0.0.0.0 --port 8002 --reload
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Ensure project root is on sys.path ──────────────────────────────
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from report_service.router import router

app = FastAPI(
    title="CausalMedFusion — Report Processing Service",
    description=(
        "Context-Aware Report Processing Microservice. "
        "Transforms clinical PDFs into section-aware text strings, "
        "computes temporal coordinates, and persists to the HDF5 vault."
    ),
    version="1.0.0",
)

# ── CORS (allow all origins during development) ────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount router ────────────────────────────────────────────────────
app.include_router(router, tags=["Report Processing"])


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness probe."""
    return {"status": "healthy", "service": "report-processing"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("report_service.main:app", host="0.0.0.0", port=8002, reload=True)
