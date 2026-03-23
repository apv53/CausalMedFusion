"""
Pydantic schemas for the Labs Processing Microservice.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LabProcessByPathRequest(BaseModel):
    """Request body for path-based lab processing (shared storage)."""

    stay_id: str = Field(..., description="Patient stay / assessment identifier")
    report_id: str = Field(..., description="Unique report identifier")
    report_type: str = Field(..., description="Report type (e.g. blood)")
    file_path: str = Field(..., description="Absolute path to lab PDF on shared storage")
    icu_intime: str = Field(..., description="ICU admission timestamp (ISO 8601)")


class LabProcessResponse(BaseModel):
    """JSON body returned after successful lab processing."""

    stay_id: str = Field(..., description="Patient stay identifier")
    report_id: str = Field(..., description="Unique report identifier")
    windows_processed: list[int] = Field(
        ..., description="Sorted list of window IDs that contained lab events"
    )
    total_measurements: int = Field(
        ..., ge=0, description="Total number of normalised lab events persisted"
    )
    measurements_by_window: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description=(
            "Mapping from window_id (str) to list of normalised measurement dicts. "
            "Each dict has keys: lab_type, lab_value, t_global, t_window."
        ),
    )
