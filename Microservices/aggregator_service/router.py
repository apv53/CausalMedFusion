"""
Aggregator Service Router
POST /aggregate
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
import traceback

from aggregator_service.schemas import AggregateRequest, AggregateResponse
from aggregator_service.processing import process_pending_files_for_stay

router = APIRouter()

@router.post(
    "/aggregate",
    response_model=AggregateResponse,
    summary="Aggregate pending data for a stay into window_store.h5",
)
async def aggregate_stay(req: AggregateRequest) -> AggregateResponse:
    try:
        processed_count, modified_windows, errors = await process_pending_files_for_stay(req.stay_id)
        
        return AggregateResponse(
            stay_id=req.stay_id,
            aggregated_files=processed_count,
            modified_windows=modified_windows,
            errors=errors
        )
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))
