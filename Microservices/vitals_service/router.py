"""
Vitals Service Router
======================
POST /v1/process-vitals          — multipart upload
POST /process-vitals-by-path     — shared storage path
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

from vitals_service.extraction import extract_vital_tuples, extract_vitals_from_multiple_pdfs
from vitals_service.processing import bin_into_sub_windows, aggregate_sub_windows
from vitals_service.schemas import VitalsProcessByPathRequest, VitalsProcessResponse
from shared.db_manager import upsert_vital_measurements

router = APIRouter()


@router.post(
    "/v1/process-vitals",
    response_model=VitalsProcessResponse,
    summary="Process a clinical vitals-monitor PDF",
    description=(
        "Accepts a vitals PDF, extracts structured (item, value, time) tuples, "
        "bins into 30-minute sub-windows, computes statistical aggregates and "
        "density Z-scores, and persists to PostgreSQL via JSONB upsert. "
        "Each event has keys: vital_type, vital_mean, vital_std, vital_last, "
        "vital_count, t_global, t_window."
    ),
)
async def process_vitals_endpoint(
    pdf: UploadFile = File(..., description="Vitals-monitor PDF file"),
    stay_id: str = Form(..., description="Patient stay identifier"),
    icu_intime: datetime = Form(..., description="ICU admission timestamp (ISO 8601)"),
) -> VitalsProcessResponse:
    """Full vitals PDF → extract → aggregate → PostgreSQL pipeline."""

    if icu_intime.tzinfo:
        icu_intime = icu_intime.replace(tzinfo=None)

    # 1. Read uploaded PDF
    pdf_bytes = await pdf.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")

    # 2. Extract (item, value, time) tuples
    try:
        readings = extract_vital_tuples(pdf_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"PDF extraction failed: {exc}"
        )

    if not readings:
        raise HTTPException(
            status_code=422,
            detail="No vital readings could be extracted from the PDF.",
        )

    # 3. Bin into sub-windows and aggregate
    try:
        binned = bin_into_sub_windows(readings, icu_intime)
        grouped = aggregate_sub_windows(binned, icu_intime)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Processing failed: {exc}"
        )

    if not grouped:
        raise HTTPException(
            status_code=422,
            detail="No valid vital items found after aggregation.",
        )

    # 4. Persist to PostgreSQL — one upsert per window_id
    total = 0
    try:
        for window_id, measurements in grouped.items():
            await upsert_vital_measurements(stay_id, window_id, measurements)
            total += len(measurements)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Database write failed: {exc}"
        )

    return VitalsProcessResponse(
        stay_id=stay_id,
        windows_processed=sorted(grouped.keys()),
        total_measurements=total,
        measurements_by_window={str(k): v for k, v in grouped.items()},
    )


@router.post(
    "/process-vitals-by-path",
    response_model=VitalsProcessResponse,
    summary="Process vitals PDFs from shared storage paths",
    description=(
        "Accepts file paths pointing to vitals PDFs on shared storage "
        "instead of a multipart upload, reducing HTTP transfer overhead. "
        "Produces the same vital_type, vital_mean, vital_std, vital_last, "
        "vital_count, t_global, t_window event schema as the upload endpoint."
    ),
)
async def process_vitals_by_path_endpoint(
    req: VitalsProcessByPathRequest,
) -> VitalsProcessResponse:
    """Read vitals PDFs from shared storage → extract → aggregate → PostgreSQL pipeline."""

    # 1. Read files from shared storage
    pdf_bytes_list: list[bytes] = []
    for fp in req.file_paths:
        file_path = Path(fp)
        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail=f"File not found: {fp}"
            )
        content = file_path.read_bytes()
        if not content:
            raise HTTPException(status_code=400, detail=f"PDF file is empty: {fp}")
        pdf_bytes_list.append(content)

    # 2. Extract (item, value, time) tuples from all PDFs
    try:
        readings = extract_vitals_from_multiple_pdfs(pdf_bytes_list)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"PDF extraction failed: {exc}"
        )

    if not readings:
        raise HTTPException(
            status_code=422,
            detail="No vital readings could be extracted from the PDF(s).",
        )

    # 3. Parse icu_intime, bin into sub-windows, and aggregate
    icu_intime = datetime.fromisoformat(req.icu_intime)
    if icu_intime.tzinfo:
        icu_intime = icu_intime.replace(tzinfo=None)
    try:
        binned = bin_into_sub_windows(readings, icu_intime)
        grouped = aggregate_sub_windows(binned, icu_intime)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Processing failed: {exc}"
        )

    if not grouped:
        raise HTTPException(
            status_code=422,
            detail="No valid vital items found after aggregation.",
        )

    # 4. Persist to PostgreSQL — one upsert per window_id
    total = 0
    try:
        for window_id, measurements in grouped.items():
            await upsert_vital_measurements(req.stay_id, window_id, measurements)
            total += len(measurements)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Database write failed: {exc}"
        )

    return VitalsProcessResponse(
        stay_id=req.stay_id,
        windows_processed=sorted(grouped.keys()),
        total_measurements=total,
        measurements_by_window={str(k): v for k, v in grouped.items()},
    )
