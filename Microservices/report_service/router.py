"""
Report Service Router
=====================
POST /v1/process-report — accepts multipart PDF upload + metadata fields,
runs the text extraction pipeline, persists to HDF5, and returns temporal
coordinates.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

# ── Ensure project root is on sys.path for shared imports ───────────
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from report_service.extraction import encode_report_type, extract_sections
from report_service.schemas import ReportProcessByPathRequest, ReportProcessResponse
from shared.hdf5_manager import save_report_data
from shared.temporal import compute_temporal_coords

router = APIRouter()


@router.post(
    "/v1/process-report",
    response_model=ReportProcessResponse,
    summary="Process a clinical PDF report",
    description=(
        "Accepts a clinical PDF report together with metadata, extracts "
        "section-aware text (FINDINGS / IMPRESSION), computes temporal "
        "coordinates, and persists everything to the HDF5 vault."
    ),
)
async def process_report_endpoint(
    report_pdf: UploadFile = File(..., description="Clinical PDF report file"),
    report_id: str = Form(..., description="Unique report identifier"),
    stay_id: str = Form(..., description="ICU stay / visit identifier"),
    report_type: str = Form(..., description="Report category: AR or RR"),
    icu_intime: datetime = Form(..., description="ICU admission timestamp"),
    time_of_assessment_record: datetime = Form(
        ..., description="Assessment record timestamp"
    ),
) -> ReportProcessResponse:
    """Full PDF → text → HDF5 pipeline."""

    # 1. Read uploaded PDF
    pdf_bytes = await report_pdf.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")

    # 2. Encode categorical report type
    try:
        type_label = encode_report_type(report_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # 3. Compute temporal coordinates
    temporal = compute_temporal_coords(icu_intime, time_of_assessment_record)

    # 4. Extract section-aware text from PDF
    try:
        extracted_text = extract_sections(pdf_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"PDF extraction failed: {exc}",
        )

    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from the uploaded PDF.",
        )

    # 5. Persist to HDF5 vault
    try:
        save_report_data(
            stay_id=stay_id,
            report_id=report_id,
            text=extracted_text,
            type_label=type_label,
            window_id=temporal.window_id,
            t_global=temporal.t_global,
            t_window=temporal.t_window,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"HDF5 write failed: {exc}",
        )

    # 6. Return computed coordinates
    return ReportProcessResponse(
        report_id=report_id,
        type_label=type_label,
        window_id=temporal.window_id,
        t_global=temporal.t_global,
        t_window=temporal.t_window,
        sections_extracted=extracted_text[:200],
    )


@router.post(
    "/v1/process-report-by-path",
    response_model=ReportProcessResponse,
    summary="Process a clinical PDF report from shared storage path",
    description=(
        "Accepts a file path pointing to a clinical PDF on shared storage "
        "instead of a multipart upload, reducing HTTP transfer overhead."
    ),
)
async def process_report_by_path_endpoint(
    req: ReportProcessByPathRequest,
) -> ReportProcessResponse:
    """Read PDF from shared storage path → text → HDF5 pipeline."""

    from datetime import datetime as dt

    # 1. Read file from shared storage
    file_path = Path(req.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")

    pdf_bytes = file_path.read_bytes()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="PDF file is empty.")

    # 2. Encode categorical report type
    try:
        type_label = encode_report_type(req.report_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # 3. Compute temporal coordinates using user-specified formulas:
    #   t_global = (record_time - stay_intime) / 24h
    #   t_window = (record_time - window_start) / 4h
    icu_intime = dt.fromisoformat(req.icu_intime)
    time_of_assessment_record = dt.fromisoformat(req.time_of_assessment_record)

    hours_elapsed = (time_of_assessment_record - icu_intime).total_seconds() / 3600.0
    window_start_hours = (req.window_id - 1) * 4.0
    window_end_hours = req.window_id * 4.0

    t_global = hours_elapsed / 24.0

    # Constrain hours_elapsed to within the window [window_start, window_end)
    clamped_hours = max(window_start_hours, min(hours_elapsed, window_end_hours))
    t_window = (clamped_hours - window_start_hours) / 4.0

    # Normalize (clamp to [0, 1])
    t_global = round(max(0.0, min(t_global, 1.0)), 6)
    t_window = round(max(0.0, min(t_window, 1.0)), 6)

    print(f"\n{'='*60}")
    print(f"[REPORT TEMPORAL] icu_intime   = {icu_intime}")
    print(f"[REPORT TEMPORAL] record_time  = {time_of_assessment_record}")
    print(f"[REPORT TEMPORAL] hours_elapsed= {hours_elapsed:.4f}")
    print(f"[REPORT TEMPORAL] window_id    = {req.window_id}")
    print(f"[REPORT TEMPORAL] window_range = [{window_start_hours}, {window_end_hours})")
    print(f"[REPORT TEMPORAL] clamped_hours= {clamped_hours:.4f}")
    print(f"[REPORT TEMPORAL] t_global     = {t_global}")
    print(f"[REPORT TEMPORAL] t_window     = {t_window}")
    print(f"{'='*60}\n", flush=True)

    # 4. Extract section-aware text from PDF
    try:
        extracted_text = extract_sections(pdf_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"PDF extraction failed: {exc}",
        )

    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from the PDF.",
        )

    # 5. Persist to HDF5 vault
    try:
        save_report_data(
            stay_id=req.stay_id,
            patient_id=req.patient_id,
            visit_id=req.visit_id,
            assessment_id=req.assessment_id,
            file_id=req.file_id,
            window_id=req.window_id,
            text=extracted_text,
            type_label=type_label,
            t_global=t_global,
            t_window=t_window,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"HDF5 write failed: {exc}",
        )

    # 6. Return computed coordinates
    return ReportProcessResponse(
        report_id=req.report_id,
        type_label=type_label,
        window_id=req.window_id,
        t_global=t_global,
        t_window=t_window,
        sections_extracted=extracted_text[:200],
    )

