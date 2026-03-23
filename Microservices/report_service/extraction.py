"""
Report Extraction Pipeline
==========================
Transforms clinical PDF reports into clean, section-aware text strings.

Steps:
  1. Open PDF with PyMuPDF (fitz)
  2. Extract full text across all pages
  3. Identify FINDINGS: and IMPRESSION: headers
  4. Clean whitespace while preserving medical terms & negations
"""

from __future__ import annotations

import re

import fitz  # PyMuPDF

# ── Report-Type Encoding ────────────────────────────────────────────

REPORT_TYPE_MAP: dict[str, int] = {
    "AR": 0,
    "RR": 1,
}


def encode_report_type(report_type: str) -> int:
    """
    Convert a report-type string to its integer label.

    Raises ``ValueError`` for unknown types.
    """
    key = report_type.strip().upper()
    if key not in REPORT_TYPE_MAP:
        raise ValueError(
            f"Unknown report_type '{report_type}'. "
            f"Expected one of {list(REPORT_TYPE_MAP.keys())}"
        )
    return REPORT_TYPE_MAP[key]


# ── Section Headers ─────────────────────────────────────────────────

# Regex patterns for clinical report headers (case-insensitive)
_SECTION_PATTERN = re.compile(
    r"(FINDINGS\s*:|IMPRESSION\s*:)", re.IGNORECASE
)


def _clean_text(text: str) -> str:
    """
    Normalise whitespace:
      - Replace newlines with spaces
      - Collapse multiple spaces into one
      - Strip leading / trailing whitespace
    Medical terms and negations (no, not, etc.) are preserved.
    """
    text = text.replace("\n", " ")
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


# ── Main Extraction ─────────────────────────────────────────────────

def extract_sections(pdf_bytes: bytes) -> str:
    """
    Extract and clean section-aware text from a clinical PDF.

    Looks for ``FINDINGS:`` and ``IMPRESSION:`` headers.  If found, only
    the text following those headers is returned.  If neither header is
    found, the full cleaned text is returned as a fallback.

    Parameters
    ----------
    pdf_bytes : bytes
        Raw PDF file content.

    Returns
    -------
    str
        Cleaned, section-aware text string.
    """
    # 1. Open PDF and extract text from all pages
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text("text")
    doc.close()

    if not full_text.strip():
        return ""

    # 2. Try to extract named sections
    sections = _SECTION_PATTERN.split(full_text)

    extracted_parts: list[str] = []

    if len(sections) > 1:
        # sections list looks like:
        #   [preamble, 'FINDINGS:', findings_text, 'IMPRESSION:', impression_text, ...]
        i = 1  # skip preamble
        while i < len(sections):
            header = sections[i].strip().upper()
            if i + 1 < len(sections):
                body = _clean_text(sections[i + 1])
                if body:
                    extracted_parts.append(f"{header} {body}")
            i += 2
    else:
        # No recognised headers — return entire cleaned text
        extracted_parts.append(_clean_text(full_text))

    return " ".join(extracted_parts)
