"""
Image Service Router
====================
Receives image file path from shared storage and processes the image.
"""

from pathlib import Path
from datetime import datetime as dt
from fastapi import APIRouter, HTTPException

from image_service.schemas import ImageProcessByPathRequest, ImageProcessResponse
from image_service.processing import process_image, encode_view_position
from image_service.config import ALLOWED_IMAGE_ROOT

from shared.hdf5_manager import save_image_data

router = APIRouter()

# Resolve once at import time for consistent startswith checks
_RESOLVED_ROOT = str(ALLOWED_IMAGE_ROOT.resolve())


def validate_path(file_path: str) -> Path:
    """
    Ensure file path exists and is inside allowed root directory.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise HTTPException(404, f"Image not found: {file_path}")

    if not str(path).startswith(_RESOLVED_ROOT):
        raise HTTPException(403, "Access outside allowed media directory")

    return path


@router.post(
    "/v1/process-image",
    response_model=ImageProcessResponse,
    summary="Process an X-ray image from shared storage",
)
async def process_image_endpoint(req: ImageProcessByPathRequest):

    # Validate path
    path = validate_path(req.file_path)

    # Read image
    raw_bytes = path.read_bytes()

    if not raw_bytes:
        raise HTTPException(400, "Image file is empty")

    # Encode view position
    try:
        view_label = encode_view_position(req.view_position)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    # Parse ISO timestamps to datetime objects
    icu_intime = dt.fromisoformat(req.icu_intime)
    record_time = dt.fromisoformat(req.record_time)

    # Compute temporal features using user-specified formulas:
    #   t_global = (record_time - stay_intime) / 24h
    #   t_window = (record_time - window_start) / 4h
    #     where window_start = stay_intime + (window_id - 1) * 4h
    hours_elapsed = (record_time - icu_intime).total_seconds() / 3600.0
    window_start_hours = (req.window_id - 1) * 4.0
    window_end_hours = req.window_id * 4.0

    t_global = hours_elapsed / 24.0

    # Constrain hours_elapsed to within the window [window_start, window_end)
    # so t_window always produces a meaningful value in [0, 1]
    clamped_hours = max(window_start_hours, min(hours_elapsed, window_end_hours))
    t_window = (clamped_hours - window_start_hours) / 4.0

    # Normalize (clamp to [0, 1])
    t_global = round(max(0.0, min(t_global, 1.0)), 6)
    t_window = round(max(0.0, min(t_window, 1.0)), 6)

    print(f"\n{'='*60}")
    print(f"[IMAGE TEMPORAL] icu_intime   = {icu_intime}")
    print(f"[IMAGE TEMPORAL] record_time  = {record_time}")
    print(f"[IMAGE TEMPORAL] hours_elapsed= {hours_elapsed:.4f}")
    print(f"[IMAGE TEMPORAL] window_id    = {req.window_id}")
    print(f"[IMAGE TEMPORAL] window_range = [{window_start_hours}, {window_end_hours})")
    print(f"[IMAGE TEMPORAL] clamped_hours= {clamped_hours:.4f}")
    print(f"[IMAGE TEMPORAL] t_global     = {t_global}")
    print(f"[IMAGE TEMPORAL] t_window     = {t_window}")
    print(f"{'='*60}\n", flush=True)

    # Process image
    try:
        tensor = process_image(raw_bytes)
    except Exception as exc:
        print(f"[IMAGE ERROR] process_image failed: {exc}", flush=True)
        raise HTTPException(422, f"Image processing failed: {exc}")

    # Save to HDF5
    try:
        save_image_data(
            stay_id=req.stay_id,
            patient_id=req.patient_id,
            visit_id=req.visit_id,
            assessment_id=req.assessment_id,
            file_id=req.file_id,
            window_id=req.window_id,
            tensor=tensor,
            view_label=view_label,
            t_global=t_global,
            t_window=t_window,
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"[IMAGE ERROR] HDF5 write failed: {exc}", flush=True)
        raise HTTPException(500, f"HDF5 write failed: {exc}")

    return ImageProcessResponse(
        image_name=req.image_name,
        view_label=view_label,
        window_id=req.window_id,
        t_global=t_global,
        t_window=t_window,
    )

