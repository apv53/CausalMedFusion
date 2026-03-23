"""
Storage manager for the Window Aggregator service.
Handles appending arrays to the final `window_store.h5` tensor vault.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from filelock import FileLock

_project_root = Path(__file__).resolve().parent.parent.parent

DEFAULT_WINDOW_STORE_PATH = os.environ.get(
    "HDF5_WINDOW_STORE_PATH",
    str(_project_root / "Microservices" / "shared" / "model_inputs" / "window_store.h5"),
)


def _resolve(path_str: str) -> Path:
    """Resolve path and ensure parent directories exist."""
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _lock(path: Path) -> FileLock:
    return FileLock(f"{path}.lock", timeout=10)

def append_to_window_store(
    stay_id: str,
    window_id: int,
    modality: str,
    data: np.ndarray,
    metadata: np.ndarray | None = None,
    store_path: str | None = None,
) -> None:
    """
    Append new rows to an existing dataset or create it if not exists.
    For CXR/Report, `data` is [n, dim] and `metadata` is [n, 3].
    For Vitals/Labs, `data` is [n, dim] and `metadata` is None.
    modality string determines the dataset name in the group.
    Group path: /<stay_id>/w<window_id>/ 
    """
    if data.size == 0:
        return

    path = _resolve(store_path or DEFAULT_WINDOW_STORE_PATH)
    
    with _lock(path):
        with h5py.File(str(path), "a") as f:
            group_name = f"{stay_id}/w{window_id}"
            grp = f.require_group(group_name)

            _append_dataset(grp, modality, data)
            if metadata is not None:
                _append_dataset(grp, f"{modality}_meta", metadata)


def _append_dataset(grp: h5py.Group, name: str, new_data: np.ndarray):
    """Internal helper to either create or append to an resizable HDF5 dataset."""
    if name not in grp:
        # Create dataset with maxshape=(None, ...) to allow resizing along dim 0
        max_shape = (None,) + new_data.shape[1:]
        grp.create_dataset(
            name,
            data=new_data,
            maxshape=max_shape,
            compression="gzip",
            compression_opts=4,
            chunks=True
        )
    else:
        # Dataset exists, extend it
        ds = grp[name]
        current_len = ds.shape[0]
        new_len = current_len + new_data.shape[0]
        ds.resize(new_len, axis=0)
        ds[current_len:] = new_data
