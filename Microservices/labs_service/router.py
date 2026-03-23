"""
Labs Service Router
====================
POST /v1/process-labs          — multipart upload
POST /process-labs-by-path     — shared storage path
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

# ── Ensure project root is on sys.path ────────────────────────────────────────
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from labs_service.extraction import extract_lab_tuples
from labs_service.processing import validate_and_normalize
from labs_service.schemas import LabProcessByPathRequest, LabProcessResponse
from shared.db_manager import upsert_lab_measurements

router = APIRouter()


@router.post(
    "/v1/process-labs",
    response_model=LabProcessResponse,
    summary="Process a clinical lab-report PDF",
    description=(
        "Accepts a lab-report PDF, extracts structured (item, value, time) "
        "tuples, validates against the lab item lookup, applies per-item "
        "transform and z-score normalisation, computes t_global and t_window, "
        "groups by 4-hour window, and persists to PostgreSQL via JSONB upsert. "
        "Each persisted event has keys: lab_type, lab_value, t_global, t_window."
    ),
)
async def process_labs_endpoint(
    pdf: UploadFile = File(..., description="Lab-report PDF file"),
    stay_id: str = Form(..., description="Patient stay identifier"),
    report_id: str = Form(..., description="Unique report identifier"),
    report_type: str = Form(..., description="Report type (e.g. AR, RR)"),
    icu_intime: datetime = Form(..., description="ICU admission timestamp (ISO 8601)"),
) -> LabProcessResponse:
    """Full lab PDF → extract → normalise → PostgreSQL pipeline."""

    # Strip timezone for naive subtraction
    if icu_intime.tzinfo:
        icu_intime = icu_intime.replace(tzinfo=None)

    # 1. Read uploaded PDF
    pdf_bytes = await pdf.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")

    # 2. Extract (item, value, time) tuples
    try:
        readings = extract_lab_tuples(pdf_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"PDF extraction failed: {exc}"
        )

    if not readings:
        raise HTTPException(
            status_code=422,
            detail="No lab readings could be extracted from the PDF.",
        )

    # 3. Validate, normalise, and group by window
    try:
        grouped = validate_and_normalize(readings, icu_intime)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Processing failed: {exc}"
        )

    if not grouped:
        raise HTTPException(
            status_code=422,
            detail="No valid lab items found after validation.",
        )

    # 4. Persist to PostgreSQL — one upsert per window_id
    total = 0
    try:
        for window_id, measurements in grouped.items():
            await upsert_lab_measurements(stay_id, window_id, measurements)
            total += len(measurements)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Database write failed: {exc}"
        )

    return LabProcessResponse(
        stay_id=stay_id,
        report_id=report_id,
        windows_processed=sorted(grouped.keys()),
        total_measurements=total,
        measurements_by_window={str(k): v for k, v in grouped.items()},
    )


@router.post(
    "/process-labs-by-path",
    response_model=LabProcessResponse,
    summary="Process a lab-report PDF from shared storage path",
    description=(
        "Accepts a file path pointing to a lab-report PDF on shared storage "
        "instead of a multipart upload, reducing HTTP transfer overhead. "
        "Produces the same lab_type, lab_value, t_global, t_window event "
        "schema as the upload endpoint."
    ),
)
async def process_labs_by_path_endpoint(
    req: LabProcessByPathRequest,
) -> LabProcessResponse:
    """Read lab PDF from shared storage path → extract → normalise → PostgreSQL pipeline."""

    # 1. Read file from shared storage
    file_path = Path(req.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"File not found: {req.file_path}"
        )

    pdf_bytes = file_path.read_bytes()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="PDF file is empty.")

    # 2. Extract (item, value, time) tuples
    try:
        readings = extract_lab_tuples(pdf_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"PDF extraction failed: {exc}"
        )

    if not readings:
        raise HTTPException(
            status_code=422,
            detail="No lab readings could be extracted from the PDF.",
        )

    # 3. Parse icu_intime (strip offset), validate, normalise, and group by window
    icu_intime = datetime.fromisoformat(req.icu_intime).replace(tzinfo=None)
    try:
        grouped = validate_and_normalize(readings, icu_intime)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Processing failed: {exc}"
        )

    if not grouped:
        raise HTTPException(
            status_code=422,
            detail="No valid lab items found after validation.",
        )

    # 4. Persist to PostgreSQL — one upsert per window_id
    total = 0
    try:
        for window_id, measurements in grouped.items():
            await upsert_lab_measurements(req.stay_id, window_id, measurements)
            total += len(measurements)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Database write failed: {exc}"
        )

    return LabProcessResponse(
        stay_id=req.stay_id,
        report_id=req.report_id,
        windows_processed=sorted(grouped.keys()),
        total_measurements=total,
        measurements_by_window={str(k): v for k, v in grouped.items()},
    )