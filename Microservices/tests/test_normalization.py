"""
Tests for shared.normalization module
======================================
Covers Z-score, log-count transform, and Parquet norm loading.
"""

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.normalization import (
    load_lookup_from_parquet,
    log_count_transform,
    z_score,
)


# ── Z-Score ──────────────────────────────────────────────────────────

class TestZScore:
    def test_basic(self):
        assert z_score(10.0, 8.0, 2.0) == pytest.approx(1.0)

    def test_negative_z(self):
        assert z_score(6.0, 8.0, 2.0) == pytest.approx(-1.0)

    def test_zero_std_returns_zero(self):
        """When σ=0, function should return 0 to avoid division error."""
        assert z_score(5.0, 3.0, 0.0) == 0.0

    def test_near_zero_std(self):
        assert z_score(5.0, 3.0, 1e-10) == 0.0


# ── Log-Count Transform ────────────────────────────────────────────

class TestLogCountTransform:
    def test_zero_count(self):
        """ln(0 + 1) = 0."""
        assert log_count_transform(0) == pytest.approx(0.0)

    def test_one_count(self):
        """ln(1 + 1) = ln(2) ≈ 0.693."""
        import math
        assert log_count_transform(1) == pytest.approx(math.log(2))

    def test_large_count(self):
        import math
        assert log_count_transform(100) == pytest.approx(math.log(101))


# ── Parquet Norm Loading ────────────────────────────────────────────

class TestLoadLookupFromParquet:
    def test_loads_correctly(self, tmp_path):
        """Create a temporary Parquet file and verify loading."""
        df = pd.DataFrame({
            "label": ["Hemoglobin", "Creatinine"],
            "abbreviation": ["Hgb", "Cr"],
            "transform": ["none", "none"],
            "z_mean": [12.5, 1.0],
            "z_std": [1.8, 0.3],
            "label_encoding": [1, 2]
        })
        p = tmp_path / "test_norms.parquet"
        df.to_parquet(p)

        norms = load_lookup_from_parquet(p)
        assert "Hemoglobin" in norms
        assert "Hgb" in norms
        assert norms["Hemoglobin"]["z_mean"] == pytest.approx(12.5)
        assert norms["Hemoglobin"]["z_std"] == pytest.approx(1.8)
        assert norms["Creatinine"]["z_mean"] == pytest.approx(1.0)

    def test_missing_columns_raises(self, tmp_path):
        """Parquet without required columns should raise ValueError."""
        df = pd.DataFrame({"name": ["x"], "average": [1.0]})
        p = tmp_path / "bad_norms.parquet"
        df.to_parquet(p)

        with pytest.raises(ValueError, match="missing columns"):
            load_lookup_from_parquet(p)
