"""
Core Processing Gateway
======================
Unifies all CPU-bound processing algorithms into a single FastAPI instance
on Port 8001. Reduces OS memory overhead and simplifies connection pools.

Included Services:
- Image Service
- Report Service
- Labs Service
- Vitals Service
- Aggregator Service
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Import Routers
from image_service.router import router as image_router
from report_service.router import router as report_router
from labs_service.router import router as labs_router
from vitals_service.router import router as vitals_router
from aggregator_service.router import router as aggregator_router

# Import DB Initialization Functions
from shared.db_manager import init_db as init_shared_db, close_pool as close_shared_db
from aggregator_service.db_client import init_aggregator_db, close_aggregator_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Events
    await init_shared_db()
    await init_aggregator_db()
    yield
    # Shutdown Events
    await close_shared_db()
    await close_aggregator_db()


app = FastAPI(
    title="CausalMedFusion — Core Processing Gateway",
    description="Unified CPU-bound microservices for fast extraction and aggregation.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "core-gateway"}

# Mount Sub-Routers
app.include_router(image_router, tags=["Image Processing"])
app.include_router(report_router, tags=["Report Processing"])
app.include_router(labs_router, tags=["Labs Processing"])
app.include_router(vitals_router, tags=["Vitals Processing"])
app.include_router(aggregator_router, tags=["Aggregation"])


if __name__ == "__main__":
    import uvicorn
    # Core gateway runs on port 8001 replacing the fragmented 8001-8004, 8006 sequence
    uvicorn.run("core_gateway.main:app", host="0.0.0.0", port=8001, reload=False)
