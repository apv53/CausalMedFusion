"""
Inference Service Router
========================
POST /v1/infer — Accepts visit_id, builds tensors, runs ONNX inference.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from inference_service.schemas import InferenceRequest, InferenceResponse
from inference_service.tensor_builder import build_onnx_inputs
from inference_service.engine import run_inference

router = APIRouter()


@router.post(
    "/v1/infer",
    response_model=InferenceResponse,
    summary="Run ONNX severity inference for a patient visit",
)
async def infer(req: InferenceRequest):
    # Step 1-2: Build ONNX input tensors
    try:
        inputs, severity_index = build_onnx_inputs(req.visit_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Steps 3-5: ONNX forward pass, calibration, narrative
    try:
        result = run_inference(inputs, severity_index, req.visit_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")

    return InferenceResponse(**result)
