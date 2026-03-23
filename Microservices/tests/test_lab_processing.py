"""
Tests for labs_service.processing module
=========================================
Covers lab extraction, validation, and Z-score normalisation.
"""

import io
import sys
from datetime import datetime, timedelta
from pathlib import Path

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from labs_service.extraction import LabReading, extract_lab_tuples
from labs_service.processing import validate_and_normalize


# ── Helpers ──────────────────────────────────────────────────────────

ICU_INTIME = datetime(2024, 6, 15, 8, 0, 0)

SAMPLE_NORMS = {
    "Hemoglobin": {"transform": "none", "z_mean": 12.0, "z_std": 2.0, "label_encoding": 1},
    "Creatinine": {"transform": "none", "z_mean": 1.0, "z_std": 0.3, "label_encoding": 2},
    "Glucose": {"transform": "none", "z_mean": 100.0, "z_std": 20.0, "label_encoding": 3},
}


def _make_lab_pdf(lines: list[str]) -> bytes:
    """Create a PDF from lines of text."""
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=10)
        y += 16
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ── Extraction Tests ─────────────────────────────────────────────────

class TestLabExtraction:
    def test_extracts_valid_lines(self):
        pdf = _make_lab_pdf([
            "Hemoglobin    14.2    2024-06-15 10:30",
            "Creatinine    1.5     2024-06-15 11:00",
        ])
        readings = extract_lab_tuples(pdf)
        assert len(readings) == 2
        assert readings[0].item_name == "Hemoglobin"
        assert readings[0].value == pytest.approx(14.2)
        assert readings[1].item_name == "Creatinine"

    def test_ignores_malformed_lines(self):
        pdf = _make_lab_pdf([
            "This is a header line",
            "Hemoglobin    14.2    2024-06-15 10:30",
            "Random text without values",
        ])
        readings = extract_lab_tuples(pdf)
        assert len(readings) == 1

    def test_empty_pdf(self):
        doc = fitz.open()
        doc.new_page()
        pdf_bytes = doc.tobytes()
        doc.close()
        assert extract_lab_tuples(pdf_bytes) == []


# ── Processing Tests ─────────────────────────────────────────────────

class TestLabProcessing:
    def test_filters_invalid_items(self):
        """Items not in lab_norms should be discarded."""
        readings = [
            LabReading("Hemoglobin", 14.0, ICU_INTIME + timedelta(hours=2)),
            LabReading("FakeItem", 99.0, ICU_INTIME + timedelta(hours=2)),
        ]
        grouped = validate_and_normalize(readings, ICU_INTIME, lab_norms=SAMPLE_NORMS)
        total = sum(len(v) for v in grouped.values())
        assert total == 1  # only Hemoglobin

    def test_z_score_applied(self):
        """Check that value is Z-scored correctly."""
        readings = [
            LabReading("Hemoglobin", 14.0, ICU_INTIME + timedelta(hours=2)),
        ]
        grouped = validate_and_normalize(readings, ICU_INTIME, lab_norms=SAMPLE_NORMS)
        # Z = (14 - 12) / 2 = 1.0
        measurement = grouped[1][0]  # window 1
        assert measurement["lab_value"] == pytest.approx(1.0)
        assert measurement["lab_type"] == 1

    def test_groups_by_window(self):
        """Readings at different times should end up in different windows."""
        readings = [
            LabReading("Glucose", 120.0, ICU_INTIME + timedelta(hours=1)),   # window 1
            LabReading("Glucose", 110.0, ICU_INTIME + timedelta(hours=5)),   # window 2
            LabReading("Glucose", 90.0, ICU_INTIME + timedelta(hours=10)),   # window 3
        ]
        grouped = validate_and_normalize(readings, ICU_INTIME, lab_norms=SAMPLE_NORMS)
        assert 1 in grouped
        assert 2 in grouped
        assert 3 in grouped

    def test_temporal_coords_present(self):
        readings = [
            LabReading("Hemoglobin", 12.0, ICU_INTIME + timedelta(hours=6)),
        ]
        grouped = validate_and_normalize(readings, ICU_INTIME, lab_norms=SAMPLE_NORMS)
        m = grouped[2][0]  # window 2 (4-8h)
        assert "t_global" in m
        assert "t_window" in m
        assert "lab_type" in m
        assert 0.0 <= m["t_global"] <= 1.0
        assert 0.0 <= m["t_window"] <= 1.0
