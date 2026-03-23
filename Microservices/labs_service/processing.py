"""
Lab Processing Pipeline
========================
Validates extracted lab readings, applies Z-score normalisation using
population norms from a Parquet lookup table, computes temporal coordinates,
and groups results by window_id for database persistence.

Output event schema (one dict per reading):
    {
        lab_type  : int    label_encoding of the lab item
        lab_value : float  normalised (transformed + z-scored) measurement
        t_global  : float  normalised time of event from stay admission
        t_window  : float  normalised time of event from window start
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

from labs_service.extraction import LabReading

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.normalization import load_lookup_from_parquet, z_score
from shared.temporal import compute_temporal_coords


# ── Norms Loading ──────────────────────────────────────────────────────────────

_LAB_NORMS_PATH = os.environ.get(
    "LAB_NORMS_PATH",
    str(Path(__file__).resolve().parent.parent / "data" / "lab_item_lookup.parquet"),
)

_lab_norms_cache: dict[str, dict[str, Any]] | None = None


def _get_lab_norms() -> dict[str, dict[str, Any]]:
    """Load lab norms from Parquet (cached after first call)."""
    global _lab_norms_cache
    if _lab_norms_cache is None:
        _lab_norms_cache = load_lookup_from_parquet(_LAB_NORMS_PATH)
    return _lab_norms_cache


# ── Processing ─────────────────────────────────────────────────────────────────

def validate_and_normalize(
    readings: list[LabReading],
    icu_intime: datetime,
    lab_norms: dict[str, dict[str, Any]] | None = None,
) -> dict[int, list[dict[str, Any]]]:
    """
    Filter, normalise, and group lab readings by window_id.

    For each reading:
      1. Discard if item_name not present in lab_item_lookup.
      2. Compute t_global and t_window from charttime relative to icu_intime.
      3. Apply transform specified in lookup transform field (e.g. log1p).
      4. Z-score normalise using lookup z_mean and z_std.
      5. Emit event with label_encoding as lab_type.

    Parameters
    ----------
    readings : list[LabReading]
        Raw readings extracted from PDF.
    icu_intime : datetime
        ICU admission timestamp.
    lab_norms : dict, optional
        Norms dictionary. If None, loaded from the configured Parquet file.

    Returns
    -------
    dict[int, list[dict]]
        Mapping from window_id to list of normalised measurement dicts.
        Each dict has keys: lab_type, lab_value, t_global, t_window.
    """
    if lab_norms is None:
        lab_norms = _get_lab_norms()

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for reading in readings:

        # ── 1. Discard items not in lookup ────────────────────────────────────
        if reading.item_name not in lab_norms:
            continue

        norms = lab_norms[reading.item_name]

        # ── 2. Temporal coordinates ───────────────────────────────────────────
        temporal = compute_temporal_coords(icu_intime, reading.time)

        # ── 3. Apply transform ────────────────────────────────────────────────
        val = reading.value
        transform = norms.get("transform", "none").lower()
        if "log" in transform:
            val = math.log1p(max(0.0, val))

        # ── 4. Z-score normalise ──────────────────────────────────────────────
        lab_value = z_score(val, norms["z_mean"], norms["z_std"])

        # ── 5. Emit event ─────────────────────────────────────────────────────
        grouped[temporal.window_id].append({
            "lab_type":  int(norms["label_encoding"]),
            "lab_value": round(lab_value, 6),
            "t_global":  temporal.t_global,
            "t_window":  temporal.t_window,
        })

    for wid in grouped:
        grouped[wid].sort(key=lambda e: (e["t_global"], e["lab_type"]))

    return dict(grouped)