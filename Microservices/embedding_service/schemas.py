"""
Pydantic schemas for the Embedding Microservice.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Single embedding requests ───────────────────────────────────────

class CXREmbeddingRequest(BaseModel):
    """Request body for a single CXR embedding extraction."""
    visit_id: str = Field(..., description="Visit group in HDF5")
    file_id: str = Field(..., description="AssessmentFile primary key")
    window_id: int = Field(..., ge=1, le=6, description="Temporal window (1-6)")


class ReportEmbeddingRequest(BaseModel):
    """Request body for a single report embedding extraction."""
    visit_id: str = Field(..., description="Visit group in HDF5")
    file_id: str = Field(..., description="AssessmentFile primary key")
    window_id: int = Field(..., ge=1, le=6, description="Temporal window (1-6)")


class EmbeddingResponse(BaseModel):
    """Standard response for a single embedding extraction."""
    visit_id: str
    file_id: str
    embedding_shape: list[int] = Field(..., description="Shape of the stored embedding")
    status: str = Field(default="success")


# ── Batch embedding requests ────────────────────────────────────────

class BatchItem(BaseModel):
    """A single item inside a batch request."""
    file_id: str
    window_id: int = Field(..., ge=1, le=6)


class BatchEmbeddingRequest(BaseModel):
    """Request body for batch embedding extraction."""
    visit_id: str = Field(..., description="Visit group in HDF5")
    modality: str = Field(..., description="'cxr' or 'report'")
    items: list[BatchItem] = Field(..., min_length=1, description="Files to embed")


class BatchEmbeddingResponse(BaseModel):
    """Response for batch embedding extraction."""
    processed: int = Field(..., description="Number of successfully embedded items")
    failed: int = Field(..., description="Number of items that failed")
    results: list[EmbeddingResponse] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    status: str = Field(default="success")
