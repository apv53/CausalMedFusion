"""
ML Engine Gateway
=================
Unifies all GPU-heavy ML operations (e.g., embeddings, inference) into
a single FastAPI instance on Port 8005. Loads PyTorch models lazily
to speed up local developer boot times.

Included Services:
- Embedding Service
- Inference Service (ONNX)
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Import Routers
from embedding_service.router import router as embedding_router
from inference_service.router import router as inference_router


app = FastAPI(
    title="CausalMedFusion — ML Engine Gateway",
    description="GPU-bound microservices for embeddings and inference.",
    version="2.0.0"
    # No lifespan = No eager PyTorch loading!
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
    return {"status": "healthy", "service": "ml-gateway"}

# Mount Sub-Routers
app.include_router(embedding_router, tags=["Embedding Extraction"])
app.include_router(inference_router, tags=["ONNX Inference"])


if __name__ == "__main__":
    import uvicorn
    # ML gateway runs natively on port 8005
    uvicorn.run("ml_gateway.main:app", host="0.0.0.0", port=8005, reload=False)
