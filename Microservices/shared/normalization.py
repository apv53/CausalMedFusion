"""
Normalization Utilities
========================
Z-score helpers and Parquet-based lookup-table loaders for lab and vital
value/count norms.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd


# ── Z-Score ──────────────────────────────────────────────────────────

def z_score(value: float, mean: float, std: float) -> float:
    """
    Standard Z-score: (value − μ) / σ.

    Returns 0.0 when σ is zero or near-zero to avoid division errors.
    """
    if std < 1e-9:
        return 0.0
    return (value - mean) / std


# ── Log-Count Transform ────────────────────────────────────────────

def log_count_transform(count: int) -> float:
    """Apply ln(count + 1) for count density normalisation."""
    return math.log(count + 1)


# ── Parquet Norm Loaders ────────────────────────────────────────────

def load_lookup_from_parquet(parquet_path: str | Path) -> dict[str, dict[str, Any]]:
    """
    Load a categorical lookup table from a Parquet file.

    Expected columns: ``label``, ``abbreviation``, ``transform``, ``z_mean``, ``z_std``, ``label_encoding``.

    Returns a dict mapping BOTH the label and the abbreviation to the standardization dict:
        {
            "Hemoglobin": {"transform": "log", "z_mean": 12.5, "z_std": 1.8, "label_encoding": 5},
            "HGB": {"transform": "log", "z_mean": 12.5, "z_std": 1.8, "label_encoding": 5},
            ...
        }
    """
    df = pd.read_parquet(parquet_path)

    # Validate required columns
    required = {"label", "abbreviation", "transform", "z_mean", "z_std", "label_encoding"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Parquet file {parquet_path} is missing columns: {missing}. "
            f"Expected: {required}"
        )

    lookup: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        # Store for both label and abbreviation
        label = str(row["label"]).strip()
        abbrev = str(row["abbreviation"]).strip()
        
        info = {
            "transform": str(row["transform"]).strip() if pd.notna(row["transform"]) else "none",
            "z_mean": float(row["z_mean"]),
            "z_std": float(row["z_std"]),
            "label_encoding": int(row["label_encoding"]) if pd.notna(row["label_encoding"]) else None
        }

        if label:
            lookup[label] = info
            # Also store lowercase for case-insensitive matching fallback if preferred
            # But the logic expects exact match or fallback. Let's just use exact match for now.
        if abbrev:
            lookup[abbrev] = info

    return lookup

