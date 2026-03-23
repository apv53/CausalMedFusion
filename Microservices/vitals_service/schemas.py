"""
Pydantic schemas for the Vitals Processing Microservice.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VitalsProcessByPathRequest(BaseModel):
    """Request body for path-based vitals processing (shared storage)."""

    stay_id: str = Field(..., description="Patient stay / assessment identifier")
    file_paths: list[str] = Field(
        ..., min_length=1, description="Absolute paths to vitals PDFs on shared storage"
    )
    icu_intime: str = Field(..., description="ICU admission timestamp (ISO 8601)")


class VitalsProcessResponse(BaseModel):
    """JSON body returned after successful vitals processing."""

    stay_id: str = Field(..., description="Patient stay identifier")
    windows_processed: list[int] = Field(
        ..., description="Sorted list of window IDs that contained vital events"
    )
    total_measurements: int = Field(
        ..., ge=0, description="Total number of normalised vital events persisted"
    )
    measurements_by_window: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description=(
            "Mapping from window_id (str) to list of normalised measurement dicts. "
            "Each dict has keys: vital_type, vital_mean, vital_std, "
            "vital_last, vital_count, t_global, t_window."
        ),
    )
