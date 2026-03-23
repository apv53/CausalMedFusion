"""
Inference Service Schemas
=========================
Pydantic request/response models for the ONNX inference endpoint.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    visit_id: str = Field(..., description="Zero-padded visit ID, e.g. '000005'")


class InferenceResponse(BaseModel):
    assessment_id: str = Field(..., description="UUID generated for this inference run")
    visit_id: str
    severity_index: int = Field(..., description="n — number of populated windows (1-6)")
    mortality_prob: float
    severity_score: float
    vent_prob: float
    dialysis_prob: float
    mechanical_prob: float
    cardiac_prob: float
    global_sev_prob: float
    assessment_report: str
