import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from aggregator_service.router import router
from aggregator_service.db_client import init_aggregator_db, close_aggregator_db

app = FastAPI(
    title="CausalMedFusion — Window Aggregator Service",
    description="Aggregates embeddings and measurements into window_store.h5",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_aggregator_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_aggregator_db()

app.include_router(router, tags=["Aggregation"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("aggregator_service.main:app", host="0.0.0.0", port=8006, reload=False)
