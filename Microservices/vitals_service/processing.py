"""
Vitals Processing Pipeline
===========================
Bins extracted vital readings into 30-minute sub-windows, computes
synthetic midpoint times, performs statistical aggregation (mean, std,
last Z-scores plus density Z-scores), and groups results by window_id.

Output event schema (one dict per item per sub-window bin):
    {
        vital_type  : int    label_encoding of the vital type
        vital_mean  : float  z-scored mean of transformed values in the bin
        vital_std   : float  population std of z-scored values in the bin
        vital_last  : float  z-scored last transformed value in the bin
        vital_count : float  log(count+1) z-scored against count_lookup
        t_global    : float  normalised time of bin midpoint from admission
        t_window    : float  normalised time of bin midpoint from window start
    }
"""

from __future__ import annotations

import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from vitals_service.extraction import VitalReading

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.normalization import (
    load_lookup_from_parquet,
    z_score,
)
from shared.temporal import (
    compute_midpoint_temporal_coords,
    compute_sub_window_id,
    compute_window_id,
)


# ── Norms Loading ──────────────────────────────────────────────────────────────

_VALUE_NORMS_PATH = os.environ.get(
    "VITALS_VALUE_NORMS_PATH",
    str(Path(__file__).resolve().parent.parent / "data" / "vital_item_lookup.parquet"),
)

_COUNT_NORMS_PATH = os.environ.get(
    "VITALS_COUNT_NORMS_PATH",
    str(Path(__file__).resolve().parent.parent / "data" / "vital_count_lookup.parquet"),
)

_value_norms_cache: dict[str, dict[str, Any]] | None = None
_count_norms_cache: dict[tuple[int, int], dict[str, float]] | None = None


def _get_value_norms() -> dict[str, dict[str, Any]]:
    """Load value norms from vital_item_lookup (cached)."""
    global _value_norms_cache
    if _value_norms_cache is None:
        _value_norms_cache = load_lookup_from_parquet(_VALUE_NORMS_PATH)
    return _value_norms_cache


def _get_count_norms() -> dict[tuple[int, int], dict[str, float]]:
    """
    Load count-density norms from vital_count_lookup (cached).
    Keyed by (window_id, item_id) where item_id is the label_encoding integer.
    """
    global _count_norms_cache
    if _count_norms_cache is None:
        import pandas as pd
        df = pd.read_parquet(_COUNT_NORMS_PATH)
        norms: dict[tuple[int, int], dict[str, float]] = {}
        for _, row in df.iterrows():
            if pd.isna(row.get("itemid")) or pd.isna(row.get("window_id")):
                continue
            key = (int(row["window_id"]), int(row["itemid"]))
            norms[key] = {
                "mean": float(row["mean"])   if pd.notna(row.get("mean"))   else 0.0,
                "std":  float(row["stddev"]) if pd.notna(row.get("stddev")) else 1.0,
            }
        _count_norms_cache = norms
    return _count_norms_cache


# ── Transform Helper ───────────────────────────────────────────────────────────

def _apply_transform(value: float, transform: str) -> float:
    """
    Apply the transform specified in the item lookup to a single raw value.
    Currently supports log (log1p) transforms. Extend as needed.
    """
    t = transform.lower().strip()
    if "log" in t:
        return math.log1p(max(0.0, value))
    return value


# ── Sub-Window Binning ─────────────────────────────────────────────────────────

BinnedKey = tuple[int, int]  # (window_id, sub_window_id)


def bin_into_sub_windows(
    readings: list[VitalReading],
    icu_intime: datetime,
) -> dict[BinnedKey, dict[str, list[float]]]:
    """
    Assign each reading to a (window_id, sub_window_id) bin and
    group raw values by item_name.

    Returns
    -------
    dict[(window_id, sub_window_id), dict[item_name, list[raw_values]]]
    """
    bins: dict[BinnedKey, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for reading in readings:
        wid  = compute_window_id(icu_intime, reading.time)
        swid = compute_sub_window_id(icu_intime, reading.time, wid)
        bins[(wid, swid)][reading.item_name].append(reading.value)

    return dict(bins)


# ── Statistical Aggregation ────────────────────────────────────────────────────

def _safe_std(values: list[float]) -> float:
    """Population standard deviation (0.0 for single-element lists)."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def aggregate_sub_windows(
    binned: dict[BinnedKey, dict[str, list[float]]],
    icu_intime: datetime,
    value_norms: dict[str, dict[str, Any]] | None = None,
    count_norms: dict[tuple[int, int], dict[str, float]] | None = None,
) -> dict[int, list[dict[str, Any]]]:
    """
    For each (window_id, sub_window_id) bin and each vital item:

      1. Apply per-item transform to every raw value individually.
      2. Z-score each transformed value using item lookup z_mean / z_std.
      3. Compute vital_mean, vital_std, vital_last from the z-scored values.
      4. Normalise count: log(count+1) z-scored via vital_count_lookup.
      5. Attach t_global and t_window from the bin's midpoint time.

    Output event schema:
        vital_type  : int   (label_encoding)
        vital_mean  : float
        vital_std   : float
        vital_last  : float
        vital_count : float
        t_global    : float
        t_window    : float

    Returns results grouped by window_id.
    """
    if value_norms is None:
        value_norms = _get_value_norms()
    if count_norms is None:
        count_norms = _get_count_norms()

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for (wid, swid), items in sorted(binned.items()):

        # Midpoint temporal coordinates for this 30-minute bin
        midpoint = compute_midpoint_temporal_coords(icu_intime, wid, swid)

        for item_name, raw_values in items.items():

            # ── 1. Lookup item norms ──────────────────────────────────────────
            if item_name not in value_norms:
                continue

            norms      = value_norms[item_name]
            transform  = norms.get("transform", "none")
            z_mean     = norms["z_mean"]
            z_std      = norms["z_std"]
            vital_type = int(norms["label_encoding"])

            # ── 2. Transform each raw value individually ──────────────────────
            transformed = [_apply_transform(v, transform) for v in raw_values]

            # ── 3. Z-score each transformed value ────────────────────────────
            zscored = [z_score(v, z_mean, z_std) for v in transformed]

            # ── 4. Aggregate z-scored values ──────────────────────────────────
            vital_mean = sum(zscored) / len(zscored)
            vital_last = zscored[-1]
            vital_std  = _safe_std(zscored)

            # ── 5. Normalise count ────────────────────────────────────────────
            log_count = math.log1p(len(raw_values))
            cnorms    = count_norms.get(
                (wid, vital_type),
                {"mean": 0.0, "std": 1.0},
            )
            vital_count = z_score(log_count, cnorms["mean"], cnorms["std"])

            # ── 6. Emit event ─────────────────────────────────────────────────
            grouped[wid].append({
                "vital_type":  vital_type,
                "vital_mean":  round(vital_mean,  6),
                "vital_std":   round(vital_std,   6),
                "vital_last":  round(vital_last,  6),
                "vital_count": round(vital_count, 6),
                "t_global":    midpoint.t_global,
                "t_window":    midpoint.t_window,
            })

    for wid in grouped:
        grouped[wid].sort(key=lambda e: (e["t_global"], e["vital_type"]))

    return dict(grouped)