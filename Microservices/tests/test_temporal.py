"""
Tests for shared.temporal module
================================
Covers window_id computation, t_global, t_window, sub-window, midpoint.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.temporal import (
    compute_midpoint_temporal_coords,
    compute_midpoint_time,
    compute_sub_window_id,
    compute_t_global,
    compute_t_window,
    compute_temporal_coords,
    compute_window_id,
)


# ── Fixtures ─────────────────────────────────────────────────────────

ICU_INTIME = datetime(2024, 6, 15, 8, 0, 0)  # 08:00


# ── Window ID Tests (now max 6) ──────────────────────────────────────

class TestWindowId:
    def test_at_admission(self):
        """t=0 → window 1."""
        assert compute_window_id(ICU_INTIME, ICU_INTIME) == 1

    def test_first_window(self):
        """t=2h → window 1."""
        rt = ICU_INTIME + timedelta(hours=2)
        assert compute_window_id(ICU_INTIME, rt) == 1

    def test_second_window(self):
        """t=4h → window 2."""
        rt = ICU_INTIME + timedelta(hours=4)
        assert compute_window_id(ICU_INTIME, rt) == 2

    def test_mid_trajectory(self):
        """t=10h → window 3."""
        rt = ICU_INTIME + timedelta(hours=10)
        assert compute_window_id(ICU_INTIME, rt) == 3

    def test_last_regular_window(self):
        """t=20h → window 6."""
        rt = ICU_INTIME + timedelta(hours=20)
        assert compute_window_id(ICU_INTIME, rt) == 6

    def test_at_24h(self):
        """t=24h → clamped to window 6."""
        rt = ICU_INTIME + timedelta(hours=24)
        assert compute_window_id(ICU_INTIME, rt) == 6

    def test_beyond_24h_clamp(self):
        """t=30h → clamped to window 6."""
        rt = ICU_INTIME + timedelta(hours=30)
        assert compute_window_id(ICU_INTIME, rt) == 6

    def test_before_admission_clamp(self):
        """t<0 → clamped to window 1."""
        rt = ICU_INTIME - timedelta(hours=1)
        assert compute_window_id(ICU_INTIME, rt) == 1


# ── t_global Tests ───────────────────────────────────────────────────

class TestTGlobal:
    def test_at_zero(self):
        assert compute_t_global(ICU_INTIME, ICU_INTIME) == 0.0

    def test_at_12h(self):
        rt = ICU_INTIME + timedelta(hours=12)
        assert compute_t_global(ICU_INTIME, rt) == pytest.approx(0.5)

    def test_at_24h(self):
        rt = ICU_INTIME + timedelta(hours=24)
        assert compute_t_global(ICU_INTIME, rt) == pytest.approx(1.0)

    def test_clamp_above(self):
        rt = ICU_INTIME + timedelta(hours=30)
        assert compute_t_global(ICU_INTIME, rt) == 1.0

    def test_clamp_below(self):
        rt = ICU_INTIME - timedelta(hours=2)
        assert compute_t_global(ICU_INTIME, rt) == 0.0


# ── t_window Tests ───────────────────────────────────────────────────

class TestTWindow:
    def test_start_of_window(self):
        """Window 2 starts at 4h; t=4h → t_window = 0."""
        rt = ICU_INTIME + timedelta(hours=4)
        assert compute_t_window(ICU_INTIME, rt, window_id=2) == pytest.approx(0.0)

    def test_mid_window(self):
        """t=6h, window 2 → 2h into 4h bin → 0.5."""
        rt = ICU_INTIME + timedelta(hours=6)
        assert compute_t_window(ICU_INTIME, rt, window_id=2) == pytest.approx(0.5)

    def test_end_of_window(self):
        """t=8h, window 2 → full 4h → 1.0."""
        rt = ICU_INTIME + timedelta(hours=8)
        assert compute_t_window(ICU_INTIME, rt, window_id=2) == pytest.approx(1.0)


# ── Convenience Wrapper Tests ────────────────────────────────────────

class TestTemporalCoords:
    def test_returns_all_fields(self):
        rt = ICU_INTIME + timedelta(hours=6)
        result = compute_temporal_coords(ICU_INTIME, rt)
        assert result.window_id == 2
        assert result.t_global == pytest.approx(0.25)
        assert result.t_window == pytest.approx(0.5)

    def test_result_immutable(self):
        result = compute_temporal_coords(ICU_INTIME, ICU_INTIME)
        with pytest.raises(AttributeError):
            result.window_id = 99  # type: ignore[misc]


# ── Sub-Window Tests ─────────────────────────────────────────────────

class TestSubWindow:
    def test_start_of_window(self):
        """At window start → sub-window 1."""
        rt = ICU_INTIME + timedelta(hours=4)  # start of window 2
        assert compute_sub_window_id(ICU_INTIME, rt, window_id=2) == 1

    def test_mid_window(self):
        """2h into a 4h window = 120 min / 30 min = sub-window 5."""
        rt = ICU_INTIME + timedelta(hours=6)  # 2h into window 2
        assert compute_sub_window_id(ICU_INTIME, rt, window_id=2) == 5

    def test_last_sub_window(self):
        """3.75h into window → sub-window 8."""
        rt = ICU_INTIME + timedelta(hours=7, minutes=45)  # 3h45m into window 2
        assert compute_sub_window_id(ICU_INTIME, rt, window_id=2) == 8


# ── Midpoint Tests ───────────────────────────────────────────────────

class TestMidpoint:
    def test_midpoint_window1_sub1(self):
        """T_mid = icu_intime + 0 + 15min."""
        mid = compute_midpoint_time(ICU_INTIME, window_id=1, sub_window_id=1)
        expected = ICU_INTIME + timedelta(minutes=15)
        assert mid == expected

    def test_midpoint_window2_sub3(self):
        """T_mid = icu_intime + 4h + (2*3-1)*15min = icu + 4h + 75min."""
        mid = compute_midpoint_time(ICU_INTIME, window_id=2, sub_window_id=3)
        expected = ICU_INTIME + timedelta(hours=4, minutes=75)
        assert mid == expected

    def test_midpoint_temporal_coords(self):
        """Verify t_global and t_window are consistent."""
        result = compute_midpoint_temporal_coords(ICU_INTIME, window_id=1, sub_window_id=1)
        assert result.window_id == 1
        assert result.sub_window_id == 1
        # T_mid = 15 min = 0.25 h → t_global = 0.25/24
        assert result.t_global == pytest.approx(0.25 / 24, abs=1e-5)
        # t_window = 0.25h / 4h
        assert result.t_window == pytest.approx(0.25 / 4, abs=1e-5)
