"""
Pydantic schemas for the Report Processing Microservice.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReportProcessByPathRequest(BaseModel):
    """Request body for path-based report processing (shared storage)."""

    report_id: str = Field(..., description="Unique report identifier")
    file_id: str = Field(..., description="AssessmentFile primary key")
    stay_id: str = Field(..., description="ICU stay / visit identifier")
    patient_id: str = Field(..., description="Patient identifier")
    visit_id: str = Field(..., description="Visit identifier")
    assessment_id: str = Field(..., description="Assessment identifier")
    window_id: int = Field(default=1, description="Temporal window offset")
    report_type: str = Field(..., description="Report category: AR or RR")
    file_path: str = Field(..., description="Absolute path to PDF on shared storage")
    icu_intime: str = Field(..., description="ICU admission timestamp (ISO)")
    time_of_assessment_record: str = Field(..., description="Assessment timestamp (ISO)")


class ReportProcessResponse(BaseModel):
    """JSON body returned after successful report processing."""

    report_id: str = Field(..., description="Key used to store the report in HDF5")
    type_label: int = Field(..., description="Encoded report-type integer")
    window_id: int = Field(..., ge=1, le=6, description="4-hour temporal bin (1–6)")
    t_global: float = Field(..., ge=0.0, le=1.0, description="Normalised global time")
    t_window: float = Field(..., ge=0.0, le=1.0, description="Normalised window time")
    sections_extracted: str = Field(
        ..., description="Preview of extracted text (first 200 chars)"
    )
    status: str = Field(default="success")
