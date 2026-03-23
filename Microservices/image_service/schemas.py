"""
Pydantic schemas for the Image Processing Microservice.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ImageProcessByPathRequest(BaseModel):
    """Request body for path-based image processing (shared storage)."""

    image_name: str = Field(..., description="Unique image identifier")
    file_id: str = Field(..., description="AssessmentFile primary key")
    stay_id: str = Field(..., description="ICU stay / visit identifier")
    patient_id: str = Field(..., description="Patient identifier")
    visit_id: str = Field(..., description="Visit identifier")
    assessment_id: str = Field(..., description="Assessment identifier")
    window_id: int = Field(default=1, description="Temporal window offset")
    view_position: str = Field(..., description="e.g. AP, PA, LATERAL")
    file_path: str = Field(..., description="Absolute path to image on shared storage")
    icu_intime: str = Field(..., description="ICU admission timestamp (ISO)")
    record_time: str = Field(..., description="Image capture timestamp (ISO)")


class ImageProcessResponse(BaseModel):
    """JSON body returned after successful image processing."""

    image_name: str = Field(..., description="Key used to store the image in HDF5")
    view_label: int = Field(..., description="Encoded view-position integer")
    window_id: int = Field(..., ge=1, le=6, description="4-hour temporal bin (1–6)")
    t_global: float = Field(..., ge=0.0, le=1.0, description="Normalised global time")
    t_window: float = Field(..., ge=0.0, le=1.0, description="Normalised window time")
    status: str = Field(default="success")
