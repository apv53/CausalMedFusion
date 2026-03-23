"""
Vitals PDF Extraction
=====================
Scans clinical vitals-monitor PDFs for structured (item, value, time) tuples.

Handles two PDF layouts:
  1. Prose / line-based:
       Heart Rate    88    2024-06-15 10:30
       SpO2          97    2024-06-15 10:30

  2. Tabular (multi-column):
       Cells on the same row are reconstructed by grouping text blocks that
       share approximately the same vertical midpoint (within Y_TOLERANCE pts).

Uses regex to match:  <item_name>  <numeric_value>  <timestamp>
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

import os
from pathlib import Path

import fitz  # PyMuPDF

import sys
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.normalization import load_lookup_from_parquet


@dataclass
class VitalReading:
    """A single raw vital reading extracted from a PDF."""
    item_name: str
    value: float
    time: datetime


# ── Regex ──────────────────────────────────────────────────────────────────────

_VITAL_LINE_PATTERN = re.compile(
    r"(?P<item>[A-Za-z][A-Za-z0-9 _/()-]+?)\s*\|?\s+"       # item name
    r"(?P<value>-?\d+(?:\.\d+)?)\s*\|?\s+"                    # numeric value
    r"(?P<time>\d{4}\s*-\s*\d{2}\s*-\s*\d{2}[\sT]\d{2}:\d{2}"  # timestamp
    r"(?::\d{2})?)",                                     # optional seconds
)

_DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
]

# How many PDF points two blocks can differ in vertical midpoint and still be
# considered the same table row.  6 pt ≈ 2 mm — works for most clinical PDFs.
_Y_TOLERANCE = 6.0


def _parse_datetime(s: str) -> datetime:
    """Try multiple datetime formats."""
    s = s.strip()
    # Remove accidental spaces around hyphens in date (e.g., "2026 -03-12" -> "2026-03-12")
    s = re.sub(r'(\d)\s*-\s*(\d)', r'\1-\2', s)
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: '{s}'")


# ── Norms Loading ──────────────────────────────────────────────────────────────

_VALUE_NORMS_PATH = os.environ.get(
    "VITALS_VALUE_NORMS_PATH",
    str(Path(__file__).resolve().parent.parent / "data" / "vital_item_lookup.parquet"),
)

_vital_norms_cache: set[str] | None = None


def _get_valid_vital_items() -> set[str]:
    """Load valid vital item labels and abbreviations from Parquet (cached after first call)."""
    global _vital_norms_cache
    if _vital_norms_cache is None:
        _vital_norms_cache = set(load_lookup_from_parquet(_VALUE_NORMS_PATH).keys())
    return _vital_norms_cache


# ── Layout Helpers ─────────────────────────────────────────────────────────────

def _prose_lines(page: fitz.Page) -> list[str]:
    """
    Extract lines from continuous prose / line-based PDFs.
    Uses the standard text stream — fastest path.
    """
    return page.get_text("text").splitlines()


def _tabular_lines(page: fitz.Page) -> list[str]:
    """
    Reconstruct logical rows from tabular PDFs by grouping text blocks that
    share approximately the same vertical midpoint.

    Each fitz block is a tuple:
        (x0, y0, x1, y1, text, block_no, block_type)
    where block_type == 0 is a text block.

    Strategy:
      1. Collect all text blocks with their vertical midpoint (y0+y1)/2.
      2. Sort blocks by (y_mid, x0) — top-to-bottom, left-to-right.
      3. Group blocks whose y_mid values fall within Y_TOLERANCE of the
         first block in the current group (row anchor).
      4. Join cells in each row left-to-right with two spaces, producing
         a single synthesised line per table row.
    """
    raw_blocks = page.get_text("blocks")

    # Keep only text blocks (type 0), skip images (type 1)
    text_blocks = [b for b in raw_blocks if b[6] == 0]

    if not text_blocks:
        return []

    # Annotate each block with its vertical midpoint
    # block: (x0, y0, x1, y1, text, block_no, block_type)
    annotated = []
    for b in text_blocks:
        x0, y0, x1, y1, text, *_ = b
        y_mid = (y0 + y1) / 2.0
        # Flatten internal newlines — each block is one table cell
        cell_text = " ".join(text.split())
        if cell_text:
            annotated.append((y_mid, x0, cell_text))

    if not annotated:
        return []

    # Sort top-to-bottom then left-to-right
    annotated.sort(key=lambda t: (t[0], t[1]))

    # Group into rows using Y_TOLERANCE bucketing
    rows: list[str] = []
    current_row: list[tuple[float, float, str]] = []
    row_y_anchor: float = annotated[0][0]

    for y_mid, x0, cell_text in annotated:
        if abs(y_mid - row_y_anchor) <= _Y_TOLERANCE:
            current_row.append((y_mid, x0, cell_text))
        else:
            # Flush the completed row
            if current_row:
                rows.append("  ".join(item[2] for item in current_row))
            # Start a new row anchored at this block's y_mid
            current_row = [(y_mid, x0, cell_text)]
            row_y_anchor = y_mid

    # Flush the final row
    if current_row:
        rows.append("  ".join(item[2] for item in current_row))

    return rows


def _extract_lines(page: fitz.Page) -> list[str]:
    """
    Return candidate lines from a page using both prose and tabular strategies,
    deduplicated while preserving order.

    Running both strategies is cheap and ensures readings are never missed
    regardless of whether the PDF is prose-based, table-based, or mixed.
    """
    seen: set[str] = set()
    lines: list[str] = []

    for line in _prose_lines(page) + _tabular_lines(page):
        # Remove zero-width spaces and other invisible characters that break regex
        line = line.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
        normalized = " ".join(line.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            lines.append(normalized)

    return lines


# ── Main Extraction ────────────────────────────────────────────────────────────

def extract_vital_tuples(pdf_bytes: bytes) -> list[VitalReading]:
    """
    Extract (item, value, time) tuples from a vitals PDF.

    Handles both prose and tabular PDF layouts transparently.

    Parameters
    ----------
    pdf_bytes : bytes
        Raw PDF file content.

    Returns
    -------
    list[VitalReading]
        All extracted readings whose item name is present in the vitals lookup.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    readings: list[VitalReading] = []
    valid_items = _get_valid_vital_items()

    for page in doc:
        for line in _extract_lines(page):
            for match in _VITAL_LINE_PATTERN.finditer(line):
                try:
                    item_name = match.group("item").strip()
                    if item_name not in valid_items:
                        continue
                    value = float(match.group("value"))
                    time = _parse_datetime(match.group("time"))
                    readings.append(
                        VitalReading(item_name=item_name, value=value, time=time)
                    )
                except (ValueError, IndexError):
                    continue

    doc.close()
    return readings


def extract_vitals_from_multiple_pdfs(
    pdf_bytes_list: list[bytes],
) -> list[VitalReading]:
    """
    Extract vital readings from multiple PDFs and combine.

    Parameters
    ----------
    pdf_bytes_list : list[bytes]
        Raw PDF file contents.

    Returns
    -------
    list[VitalReading]
        Combined readings from all PDFs.
    """
    all_readings: list[VitalReading] = []
    for pdf_bytes in pdf_bytes_list:
        all_readings.extend(extract_vital_tuples(pdf_bytes))
    return all_readings