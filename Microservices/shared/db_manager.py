"""
PostgreSQL Database Manager
============================
Async helpers for persisting lab and vital measurements using JSONB
append-on-conflict strategy.

Tables:
  - lab_measurements   (stay_id, window_id, measurements JSONB)
  - vital_measurements (stay_id, window_id, measurements JSONB)

Requires a running PostgreSQL instance. Set ``DATABASE_URL`` env var.
"""

from __future__ import annotations

import json
import os
from typing import Any

import asyncpg

# ── Configuration ────────────────────────────────────────────────────

DEFAULT_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:anuroop%401373@localhost:5432/causalmedfusion",
)

_pool: asyncpg.Pool | None = None


# ── Connection Pool ─────────────────────────────────────────────────

async def get_pool() -> asyncpg.Pool:
    """Return (and lazily create) a shared connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DEFAULT_DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    """Shut down the connection pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ── Table Initialisation ────────────────────────────────────────────

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS lab_measurements (
    stay_id     TEXT    NOT NULL,
    window_id   INTEGER NOT NULL,
    measurements JSONB  NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (stay_id, window_id)
);

CREATE TABLE IF NOT EXISTS vital_measurements (
    stay_id     TEXT    NOT NULL,
    window_id   INTEGER NOT NULL,
    measurements JSONB  NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (stay_id, window_id)
);
"""


async def init_db() -> None:
    """Create tables if they don't exist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(_INIT_SQL)


# ── JSONB Upsert Helpers ────────────────────────────────────────────

async def upsert_lab_measurements(
    stay_id: str,
    window_id: int,
    measurements: list[dict[str, Any]],
) -> None:
    """
    Insert or append lab measurements for a (stay_id, window_id) pair.

    Uses ``ON CONFLICT ... ||`` to append the new JSONB array elements
    to any existing ones.
    """
    pool = await get_pool()
    payload = json.dumps(measurements)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO lab_measurements (stay_id, window_id, measurements)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT (stay_id, window_id)
            DO UPDATE SET measurements =
                lab_measurements.measurements || EXCLUDED.measurements;
            """,
            stay_id,
            window_id,
            payload,
        )


async def upsert_vital_measurements(
    stay_id: str,
    window_id: int,
    measurements: list[dict[str, Any]],
) -> None:
    """
    Insert or append vital measurements for a (stay_id, window_id) pair.

    Uses ``ON CONFLICT ... ||`` to append the new JSONB array elements
    to any existing ones.
    """
    pool = await get_pool()
    payload = json.dumps(measurements)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO vital_measurements (stay_id, window_id, measurements)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT (stay_id, window_id)
            DO UPDATE SET measurements =
                vital_measurements.measurements || EXCLUDED.measurements;
            """,
            stay_id,
            window_id,
            payload,
        )
