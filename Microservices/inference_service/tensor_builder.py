"""
Tensor Builder — Steps 1 & 2
=============================
Reads window_store.h5 and constructs padded ONNX-ready input tensors.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import h5py
import numpy as np
from filelock import FileLock

logger = logging.getLogger(__name__)

_project_root = Path(__file__).resolve().parent.parent.parent

DEFAULT_WINDOW_STORE_PATH = os.environ.get(
    "HDF5_WINDOW_STORE_PATH",
    str(_project_root / "Microservices" / "shared" / "model_inputs" / "window_store.h5"),
)

# ── Padding specifications (from instructions.txt) ──────────────────
PAD_SPECS = {
    "cxr":         {"max_rows": 4,  "dim": 1024, "has_meta": True,  "meta_dim": 3},
    "report":      {"max_rows": 4,  "dim": 768,  "has_meta": True,  "meta_dim": 3},
    "labs":        {"max_rows": 24, "dim": 4,    "has_meta": False, "meta_dim": 0},
    "vitals":      {"max_rows": 64, "dim": 7,    "has_meta": False, "meta_dim": 0},
}


def _lock(path: Path) -> FileLock:
    return FileLock(f"{path}.lock", timeout=10)


def _pad_with_mask(data: np.ndarray, max_rows: int, dim: int) -> np.ndarray:
    """
    Pad data to [max_rows, dim], then prepend a mask column.
    Result shape: [max_rows, dim+1] where col 0 is the mask.
    Real rows get mask=1.0, padded rows get mask=0.0.
    """
    n = min(data.shape[0], max_rows) if data.size > 0 else 0
    padded = np.zeros((max_rows, dim), dtype=np.float32)
    mask = np.zeros((max_rows, 1), dtype=np.float32)

    if n > 0:
        padded[:n] = data[:n, :dim]
        mask[:n] = 1.0

    return np.concatenate([mask, padded], axis=1)  # [max_rows, dim+1]


def _pad_no_mask(data: np.ndarray, max_rows: int, dim: int) -> np.ndarray:
    """
    Pad data to [max_rows, dim] without a mask column.
    Used for the main embedding arrays (cxr, report).
    """
    n = min(data.shape[0], max_rows) if data.size > 0 else 0
    padded = np.zeros((max_rows, dim), dtype=np.float32)

    if n > 0:
        padded[:n] = data[:n, :dim]

    return padded  # [max_rows, dim]


def build_onnx_inputs(
    visit_id: str,
    store_path: str | None = None,
) -> tuple[dict[str, np.ndarray], int]:
    """
    Build all 7 ONNX input tensors from window_store.h5.

    Returns
    -------
    inputs : dict[str, ndarray]
        Keys: cxr, cxr_meta, report, report_meta, lab, vital, window_mask
    severity_index : int
        Number of populated window groups (n).
    """
    path = Path(store_path or DEFAULT_WINDOW_STORE_PATH)

    if not path.exists():
        raise FileNotFoundError(f"Window store not found: {path}")

    with _lock(path):
        with h5py.File(str(path), "r") as f:
            if visit_id not in f:
                raise KeyError(f"Visit group '{visit_id}' not found in window_store.h5")

            visit_grp = f[visit_id]
            # Step 1: List existing window groups → determine severity index n
            existing_windows = sorted(
                [int(k[1:]) for k in visit_grp.keys() if k.startswith("w")]
            )
            n = len(existing_windows)

            if n == 0:
                raise ValueError(f"No window groups found for visit '{visit_id}'")

            # Step 2: For each window slot k=1..6, build padded tensors
            all_cxr = []
            all_cxr_meta = []
            all_report = []
            all_report_meta = []
            all_lab = []
            all_vital = []
            window_mask_list = []

            for k in range(1, 7):
                grp_name = f"w{k}"

                if grp_name in visit_grp:
                    wgrp = visit_grp[grp_name]
                    window_mask_list.append(1.0)

                    # CXR embedding
                    cxr_data = np.array(wgrp["cxr"], dtype=np.float32) if "cxr" in wgrp else np.array([], dtype=np.float32)
                    all_cxr.append(_pad_no_mask(cxr_data.reshape(-1, 1024) if cxr_data.size > 0 else cxr_data, 4, 1024))

                    # CXR meta (with mask column)
                    cxr_meta_data = np.array(wgrp["cxr_meta"], dtype=np.float32) if "cxr_meta" in wgrp else np.array([], dtype=np.float32)
                    all_cxr_meta.append(_pad_with_mask(cxr_meta_data.reshape(-1, 3) if cxr_meta_data.size > 0 else cxr_meta_data, 4, 3))

                    # Report embedding
                    rep_data = np.array(wgrp["report"], dtype=np.float32) if "report" in wgrp else np.array([], dtype=np.float32)
                    all_report.append(_pad_no_mask(rep_data.reshape(-1, 768) if rep_data.size > 0 else rep_data, 4, 768))

                    # Report meta (with mask column)
                    rep_meta_data = np.array(wgrp["report_meta"], dtype=np.float32) if "report_meta" in wgrp else np.array([], dtype=np.float32)
                    all_report_meta.append(_pad_with_mask(rep_meta_data.reshape(-1, 3) if rep_meta_data.size > 0 else rep_meta_data, 4, 3))

                    # Labs (with mask column)
                    lab_data = np.array(wgrp["labs"], dtype=np.float32) if "labs" in wgrp else np.array([], dtype=np.float32)
                    all_lab.append(_pad_with_mask(lab_data.reshape(-1, 4) if lab_data.size > 0 else lab_data, 24, 4))

                    # Vitals (with mask column)
                    vit_data = np.array(wgrp["vitals"], dtype=np.float32) if "vitals" in wgrp else np.array([], dtype=np.float32)
                    all_vital.append(_pad_with_mask(vit_data.reshape(-1, 7) if vit_data.size > 0 else vit_data, 64, 7))

                else:
                    # Missing window — all-zero tensors
                    window_mask_list.append(0.0)
                    all_cxr.append(np.zeros((4, 1024), dtype=np.float32))
                    all_cxr_meta.append(np.zeros((4, 4), dtype=np.float32))
                    all_report.append(np.zeros((4, 768), dtype=np.float32))
                    all_report_meta.append(np.zeros((4, 4), dtype=np.float32))
                    all_lab.append(np.zeros((24, 5), dtype=np.float32))
                    all_vital.append(np.zeros((64, 8), dtype=np.float32))

    # Stack into final ONNX shapes with batch dim [1, 6, ...]
    inputs = {
        "cxr":         np.stack(all_cxr)[np.newaxis],          # [1, 6, 4, 1024]
        "cxr_meta":    np.stack(all_cxr_meta)[np.newaxis],     # [1, 6, 4, 4]
        "report":      np.stack(all_report)[np.newaxis],       # [1, 6, 4, 768]
        "report_meta": np.stack(all_report_meta)[np.newaxis],  # [1, 6, 4, 4]
        "lab":         np.stack(all_lab)[np.newaxis],           # [1, 6, 24, 5]
        "vital":       np.stack(all_vital)[np.newaxis],        # [1, 6, 64, 8]
        "window_mask": np.array([window_mask_list], dtype=np.float32),  # [1, 6]
    }

    logger.info(
        f"[TENSOR BUILDER] visit={visit_id} severity_index={n} "
        f"shapes: {', '.join(f'{k}={v.shape}' for k, v in inputs.items())}"
    )

    return inputs, n
