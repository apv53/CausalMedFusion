"""
Tests for report_service.extraction module
===========================================
Covers report-type encoding and PDF section extraction.
"""

import io
import sys
from pathlib import Path

import fitz  # PyMuPDF
import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from report_service.extraction import (
    REPORT_TYPE_MAP,
    _clean_text,
    encode_report_type,
    extract_sections,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _make_pdf(text: str) -> bytes:
    """Create a single-page PDF containing the given text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ── Report-Type Encoding ────────────────────────────────────────────

class TestReportTypeEncoding:
    @pytest.mark.parametrize("rt,expected", list(REPORT_TYPE_MAP.items()))
    def test_known_types(self, rt: str, expected: int):
        assert encode_report_type(rt) == expected

    def test_case_insensitive(self):
        assert encode_report_type("ar") == 0
        assert encode_report_type("Rr") == 1

    def test_strips_whitespace(self):
        assert encode_report_type("  AR  ") == 0

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown report_type"):
            encode_report_type("XX")


# ── Text Cleaning ───────────────────────────────────────────────────

class TestCleanText:
    def test_collapses_whitespace(self):
        assert _clean_text("hello   world") == "hello world"

    def test_replaces_newlines(self):
        assert _clean_text("line1\nline2\nline3") == "line1 line2 line3"

    def test_strips_edges(self):
        assert _clean_text("  spaced  ") == "spaced"

    def test_preserves_negations(self):
        text = "no evidence of   not  significant"
        cleaned = _clean_text(text)
        assert "no evidence" in cleaned
        assert "not significant" in cleaned


# ── Section Extraction ──────────────────────────────────────────────

class TestExtractSections:
    def test_finds_both_sections(self):
        text = (
            "PATIENT INFO\n\n"
            "FINDINGS: There is a small opacity in the right lung.\n\n"
            "IMPRESSION: Possible pneumonia. Follow up recommended."
        )
        pdf = _make_pdf(text)
        result = extract_sections(pdf)
        assert "FINDINGS:" in result
        assert "IMPRESSION:" in result
        assert "opacity" in result
        assert "pneumonia" in result

    def test_findings_only(self):
        text = "FINDINGS: Normal cardiac silhouette."
        pdf = _make_pdf(text)
        result = extract_sections(pdf)
        assert "FINDINGS:" in result
        assert "Normal cardiac" in result

    def test_no_headers_fallback(self):
        """When no recognised headers exist, return full cleaned text."""
        text = "This report has no standard headers but contains useful info."
        pdf = _make_pdf(text)
        result = extract_sections(pdf)
        assert "useful info" in result

    def test_empty_pdf(self):
        """An empty PDF should return empty string."""
        doc = fitz.open()
        doc.new_page()  # blank page
        pdf_bytes = doc.tobytes()
        doc.close()
        result = extract_sections(pdf_bytes)
        assert result == ""
