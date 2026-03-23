"""
Temporal Windowing & Normalization Utilities
=============================================
Shared logic for aligning clinical events to a 24-hour ICU trajectory.

Window scheme:
  - 4-hour bins → window_id 1..6
  - t_global  ∈ [0, 1] : (record_time − icu_intime) / 24 h
  - t_window  ∈ [0, 1] : offset within the 4-hour bin

Sub-window scheme (vitals only):
  - 30-minute bins within each 4-hour window → sub_window_id 1..8
  - Synthetic midpoint at centre of each sub-window
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta


# ── Constants ────────────────────────────────────────────────────────
WINDOW_HOURS = 4.0           # Each temporal bin spans 4 hours
TRAJECTORY_HOURS = 24.0      # Full ICU trajectory length
NUM_WINDOWS = 6              # 24 / 4 = 6 bins
SUB_WINDOW_MINUTES = 30.0    # Each sub-window spans 30 minutes
SUB_WINDOWS_PER_WINDOW = 8   # 4 hours / 30 min = 8 sub-windows


@dataclass(frozen=True)
class TemporalResult:
    """Immutable container for computed temporal coordinates."""
    window_id: int      # 1 – 6
    t_global: float     # [0, 1]
    t_window: float     # [0, 1]


@dataclass(frozen=True)
class MidpointTemporalResult:
    """Immutable container for midpoint-based temporal coordinates."""
    window_id: int          # 1 – 6
    sub_window_id: int      # 1 – 8
    midpoint_time: datetime
    t_global: float         # [0, 1]
    t_window: float         # [0, 1]


# ── Core Helpers ─────────────────────────────────────────────────────

def _hours_elapsed(icu_intime: datetime, record_time: datetime) -> float:
    """Return the number of hours between ICU admission and the event."""
    delta = record_time - icu_intime
    return delta.total_seconds() / 3600.0


def compute_window_id(icu_intime: datetime, record_time: datetime) -> int:
    """
    Assign a 4-hour bin index (1–6).

    Bin 1: [0 h, 4 h)
    Bin 2: [4 h, 8 h)
    ...
    Bin 6: [20 h, 24 h]

    Events before admission are clamped to window 1.
    Events at or after 24 h are clamped to window 6.
    """
    hours = _hours_elapsed(icu_intime, record_time)

    if hours <= 0:
        return 1
    if hours >= TRAJECTORY_HOURS:
        return NUM_WINDOWS

    window_id = int(math.floor(hours / WINDOW_HOURS)) + 1
    return min(window_id, NUM_WINDOWS)


def compute_t_global(icu_intime: datetime, record_time: datetime) -> float:
    """Normalise elapsed time to [0, 1] over the 24-hour trajectory."""
    hours = _hours_elapsed(icu_intime, record_time)
    t = hours / TRAJECTORY_HOURS
    return max(0.0, min(t, 1.0))


def compute_t_window(
    icu_intime: datetime,
    record_time: datetime,
    window_id: int,
) -> float:
    """
    Normalise time within the assigned 4-hour bin to [0, 1].

    window_start = (window_id − 1) × 4 h
    t_window     = (hours_elapsed − window_start) / 4 h
    """
    hours = _hours_elapsed(icu_intime, record_time)
    window_start = (window_id - 1) * WINDOW_HOURS
    offset = hours - window_start
    t = offset / WINDOW_HOURS
    return max(0.0, min(t, 1.0))


# ── Convenience Wrapper ─────────────────────────────────────────────

def compute_temporal_coords(
    icu_intime: datetime,
    record_time: datetime,
) -> TemporalResult:
    """Compute all temporal coordinates in one call."""
    window_id = compute_window_id(icu_intime, record_time)
    t_global = compute_t_global(icu_intime, record_time)
    t_window = compute_t_window(icu_intime, record_time, window_id)
    return TemporalResult(
        window_id=window_id,
        t_global=round(t_global, 6),
        t_window=round(t_window, 6),
    )


# ── Sub-Window Helpers (Vitals) ──────────────────────────────────────

def compute_sub_window_id(
    icu_intime: datetime,
    record_time: datetime,
    window_id: int,
) -> int:
    """
    Assign a 30-minute sub-window index (1–8) within a 4-hour bin.

    Sub-window 1: [0 min, 30 min)
    Sub-window 2: [30 min, 60 min)
    ...
    Sub-window 8: [210 min, 240 min]
    """
    hours = _hours_elapsed(icu_intime, record_time)
    window_start_hours = (window_id - 1) * WINDOW_HOURS
    offset_minutes = (hours - window_start_hours) * 60.0

    if offset_minutes <= 0:
        return 1
    if offset_minutes >= WINDOW_HOURS * 60:
        return SUB_WINDOWS_PER_WINDOW

    sub_id = int(math.floor(offset_minutes / SUB_WINDOW_MINUTES)) + 1
    return min(sub_id, SUB_WINDOWS_PER_WINDOW)


def compute_midpoint_time(
    icu_intime: datetime,
    window_id: int,
    sub_window_id: int,
) -> datetime:
    """
    Calculate the synthetic midpoint event time for a sub-window.

    T_mid = icu_intime + ((window_id - 1) × 4h) + ((2 × sub_window_id - 1) × 15m)
    """
    window_offset = timedelta(hours=(window_id - 1) * WINDOW_HOURS)
    sub_offset = timedelta(minutes=(2 * sub_window_id - 1) * 15)
    return icu_intime + window_offset + sub_offset


def compute_midpoint_temporal_coords(
    icu_intime: datetime,
    window_id: int,
    sub_window_id: int,
) -> MidpointTemporalResult:
    """
    Compute t_global and t_window for a synthetic midpoint.
    """
    midpoint = compute_midpoint_time(icu_intime, window_id, sub_window_id)
    t_global = compute_t_global(icu_intime, midpoint)
    t_window = compute_t_window(icu_intime, midpoint, window_id)
    return MidpointTemporalResult(
        window_id=window_id,
        sub_window_id=sub_window_id,
        midpoint_time=midpoint,
        t_global=round(t_global, 6),
        t_window=round(t_window, 6),
    )
