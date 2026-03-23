"""
Image Processing Microservice — Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from image_service.router import router

app = FastAPI(
    title="CausalMedFusion Image Processing Service",
    description="Processes X-ray images from shared storage and stores tensors in HDF5.",
    version="1.0.0",
)

# Allow frontend / backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register router
app.include_router(router, tags=["Image Processing"])


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "image-processing"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("image_service.main:app", host="0.0.0.0", port=8001, reload=True)
