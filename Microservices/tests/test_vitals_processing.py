"""
Tests for vitals_service.processing module
============================================
Covers sub-window binning, midpoint calculation, and statistical
aggregation with Z-scores.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vitals_service.extraction import VitalReading
from vitals_service.processing import (
    _safe_std,
    aggregate_sub_windows,
    bin_into_sub_windows,
)


# ── Fixtures ─────────────────────────────────────────────────────────

ICU_INTIME = datetime(2024, 6, 15, 8, 0, 0)

VALUE_NORMS = {
    "Heart Rate": {"transform": "none", "z_mean": 80.0, "z_std": 10.0, "label_encoding": 1},
    "SpO2": {"transform": "none", "z_mean": 96.0, "z_std": 2.0, "label_encoding": 2},
}

COUNT_NORMS = {
    (1, 1): {"mean": 1.5, "std": 0.5},
    (1, 2): {"mean": 1.2, "std": 0.4},
    (2, 2): {"mean": 1.2, "std": 0.4},
}


# ── Sub-Window Binning ──────────────────────────────────────────────

class TestBinIntoSubWindows:
    def test_single_reading(self):
        readings = [
            VitalReading("Heart Rate", 88.0, ICU_INTIME + timedelta(hours=1)),
        ]
        binned = bin_into_sub_windows(readings, ICU_INTIME)
        # 1h into window 1: 60 min / 30 = sub-window 3
        assert (1, 3) in binned
        assert "Heart Rate" in binned[(1, 3)]

    def test_multiple_items_same_bin(self):
        t = ICU_INTIME + timedelta(hours=1)
        readings = [
            VitalReading("Heart Rate", 88.0, t),
            VitalReading("SpO2", 97.0, t),
        ]
        binned = bin_into_sub_windows(readings, ICU_INTIME)
        key = (1, 3)
        assert "Heart Rate" in binned[key]
        assert "SpO2" in binned[key]

    def test_values_accumulated(self):
        """Multiple readings of same item in same sub-window are grouped."""
        t1 = ICU_INTIME + timedelta(minutes=5)
        t2 = ICU_INTIME + timedelta(minutes=20)
        readings = [
            VitalReading("Heart Rate", 80.0, t1),
            VitalReading("Heart Rate", 90.0, t2),
        ]
        binned = bin_into_sub_windows(readings, ICU_INTIME)
        key = (1, 1)  # both within first 30 min
        assert len(binned[key]["Heart Rate"]) == 2


# ── Safe Std ─────────────────────────────────────────────────────────

class TestSafeStd:
    def test_single_value(self):
        assert _safe_std([5.0]) == 0.0

    def test_two_values(self):
        # [10, 20] → mean=15, var=25, std=5
        assert _safe_std([10.0, 20.0]) == pytest.approx(5.0)

    def test_identical_values(self):
        assert _safe_std([7.0, 7.0, 7.0]) == pytest.approx(0.0)


# ── Aggregation ──────────────────────────────────────────────────────

class TestAggregateSubWindows:
    def test_basic_aggregation(self):
        readings = [
            VitalReading("Heart Rate", 80.0, ICU_INTIME + timedelta(minutes=5)),
            VitalReading("Heart Rate", 90.0, ICU_INTIME + timedelta(minutes=20)),
        ]
        binned = bin_into_sub_windows(readings, ICU_INTIME)
        grouped = aggregate_sub_windows(
            binned, ICU_INTIME,
            value_norms=VALUE_NORMS,
            count_norms=COUNT_NORMS,
        )

        assert 1 in grouped  # window 1
        snapshot = grouped[1][0]
        assert snapshot["vital_type"] == 1

        # mean = 85.0, Z = (85-80)/10 = 0.5
        assert snapshot["vital_mean"] == pytest.approx(0.5)
        # last = 90.0, Z = (90-80)/10 = 1.0
        assert snapshot["vital_last"] == pytest.approx(1.0)
        assert "t_global" in snapshot
        assert "t_window" in snapshot
        assert "vital_count" in snapshot

    def test_multiple_windows(self):
        readings = [
            VitalReading("SpO2", 97.0, ICU_INTIME + timedelta(hours=1)),
            VitalReading("SpO2", 95.0, ICU_INTIME + timedelta(hours=5)),
        ]
        binned = bin_into_sub_windows(readings, ICU_INTIME)
        grouped = aggregate_sub_windows(
            binned, ICU_INTIME,
            value_norms=VALUE_NORMS,
            count_norms=COUNT_NORMS,
        )
        assert 1 in grouped  # window 1
        assert 2 in grouped  # window 2

    def test_norm_count_field(self):
        """Verify norm_count uses log-count Z-score."""
        import math
        readings = [
            VitalReading("Heart Rate", 80.0, ICU_INTIME + timedelta(minutes=5)),
            VitalReading("Heart Rate", 85.0, ICU_INTIME + timedelta(minutes=10)),
            VitalReading("Heart Rate", 90.0, ICU_INTIME + timedelta(minutes=15)),
        ]
        binned = bin_into_sub_windows(readings, ICU_INTIME)
        grouped = aggregate_sub_windows(
            binned, ICU_INTIME,
            value_norms=VALUE_NORMS,
            count_norms=COUNT_NORMS,
        )
        snapshot = grouped[1][0]
        # count=3, log_count = ln(4) ≈ 1.386
        # Z = (1.386 - 1.5) / 0.5 = -0.228
        expected_log = math.log1p(3)
        expected_z = (expected_log - 1.5) / 0.5
        assert snapshot["vital_count"] == pytest.approx(expected_z, abs=0.01)
