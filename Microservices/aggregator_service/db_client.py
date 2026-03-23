"""
Async database client for Window Aggregator.
Queries Django tables to fetch pending processing files and clinical measurements.
"""
import os
import json
import asyncpg
from typing import Any

DEFAULT_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:anuroop%401373@localhost:5432/causalmedfusion",
)

_pool: asyncpg.Pool | None = None

async def init_aggregator_db() -> None:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DEFAULT_DATABASE_URL, min_size=1, max_size=5)

async def close_aggregator_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

async def fetch_pending_files(stay_id: str) -> list[dict[str, Any]]:
    """Fetch all pending AssessmentFiles for a given stay_id, grouped structurally later."""
    query = """
    SELECT 
        f.id as file_id,
        a.window_id,
        f.data_category
    FROM assessments_assessmentfile f
    JOIN assessments_assessment a ON f.assessment_id = a.id
    JOIN visits_visit v ON a.visit_id = v.id
    WHERE v.visit_id = $1 AND f.aggregation_status = 'pending'
    ORDER BY a.window_id ASC;
    """
    assert _pool is not None
    async with _pool.acquire() as conn:
        rows = await conn.fetch(query, stay_id)
        return [dict(r) for r in rows]

async def update_aggregation_status(file_ids: list[int], status: str = 'aggregated') -> None:
    """Update aggregation status for the processed files."""
    if not file_ids:
        return
    query = "UPDATE assessments_assessmentfile SET aggregation_status = $1 WHERE id = ANY($2::int[])"
    assert _pool is not None
    async with _pool.acquire() as conn:
        await conn.execute(query, status, file_ids)

async def fetch_vital_measurements(file_id: int) -> list[dict[str, Any]]:
    """Fetch JSONB vital events for a source file."""
    query = "SELECT measurements FROM assessments_vitalmeasurement WHERE source_file_id = $1"
    assert _pool is not None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(query, file_id)
        if row and row['measurements']:
            if isinstance(row['measurements'], str):
                return json.loads(row['measurements'])
            return row['measurements']
        return []

async def fetch_lab_measurements(file_id: int) -> list[dict[str, Any]]:
    """Fetch JSONB lab events for a source file."""
    query = "SELECT measurements FROM assessments_labmeasurement WHERE source_file_id = $1"
    assert _pool is not None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(query, file_id)
        if row and row['measurements']:
            if isinstance(row['measurements'], str):
                return json.loads(row['measurements'])
            return row['measurements']
        return []
