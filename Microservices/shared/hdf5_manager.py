"""
HDF5 Vault Manager
==================
Thread-safe and Process-safe helpers for persisting medical data
into a single HDF5 file using OS-level file locking.

Storage layout
--------------
Groups  : ``/<visit_id>/``
Datasets: ``<window_id>_<modality>_<file_id>``
          e.g.  ``1_cxr_42``, ``2_report_55``
"""

from __future__ import annotations

import os
from pathlib import Path

import h5py
import numpy as np
from filelock import FileLock, Timeout

# ── Configuration ────────────────────────────────────────────────────
_project_root = Path(__file__).resolve().parent.parent.parent
DEFAULT_VAULT_PATH = os.environ.get(
    "HDF5_VAULT_PATH",
    str(_project_root / "storage" / "clinical_tensors_raw" / "clinical_vault.h5"),
)

def get_hdf5_path() -> Path:
    """Resolve and return the vault file path, creating parent dirs as needed."""
    path = Path(DEFAULT_VAULT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def _get_lock(path: Path) -> FileLock:
    """Return a FileLock for the given file path."""
    return FileLock(f"{path}.lock", timeout=10)


# ── Image Persistence ───────────────────────────────────────────────

def save_image_data(
    stay_id: str,
    patient_id: str,
    visit_id: str,
    assessment_id: str,
    file_id: str,
    window_id: int,
    tensor: np.ndarray,
    view_label: int,
    t_global: float,
    t_window: float,
) -> None:
    """
    Write a processed image tensor + metadata into the HDF5 vault.
    Storage path: ``/<visit_id>/<window_id>_cxr_<file_id>``
    """
    path = get_hdf5_path()
    dataset_name = f"{window_id}_cxr_{file_id}"

    with _get_lock(path):
        with h5py.File(str(path), "a") as f:
            if "description" not in f.attrs:
                f.attrs["description"] = "CausalMedFusion Clinical Data Vault"

            visit_grp = f.require_group(visit_id)
            if dataset_name in visit_grp:
                del visit_grp[dataset_name]

            ds = visit_grp.create_dataset(
                dataset_name,
                data=tensor.astype(np.float32),
                compression="gzip",
                compression_opts=4,
            )
            ds.attrs["view_label"] = view_label
            ds.attrs["window_id"] = window_id
            ds.attrs["t_global"] = t_global
            ds.attrs["t_window"] = t_window


# ── Report Persistence ──────────────────────────────────────────────

def save_report_data(
    stay_id: str,
    patient_id: str,
    visit_id: str,
    assessment_id: str,
    file_id: str,
    window_id: int,
    text: str,
    type_label: int,
    t_global: float,
    t_window: float,
) -> None:
    """
    Write cleaned report text + metadata into the HDF5 vault.
    Storage path: ``/<visit_id>/<window_id>_report_<file_id>``
    """
    path = get_hdf5_path()
    dataset_name = f"{window_id}_report_{file_id}"

    with _get_lock(path):
        with h5py.File(str(path), "a") as f:
            if "description" not in f.attrs:
                f.attrs["description"] = "CausalMedFusion Clinical Data Vault"

            visit_grp = f.require_group(visit_id)
            if dataset_name in visit_grp:
                del visit_grp[dataset_name]

            dt = h5py.string_dtype(encoding="utf-8")
            ds = visit_grp.create_dataset(dataset_name, data=text, dtype=dt)
            ds.attrs["type_label"] = type_label
            ds.attrs["window_id"] = window_id
            ds.attrs["t_global"] = t_global
            ds.attrs["t_window"] = t_window


# ── Deletion ────────────────────────────────────────────────────────

def delete_dataset(
    visit_id: str,
    dataset_name: str,
    vault_path: str | None = None,
) -> bool:
    """
    Delete a single dataset from the HDF5 vault.

    Parameters
    ----------
    visit_id : str
        Visit group that contains the dataset.
    dataset_name : str
        Name of the dataset, e.g. ``1_cxr_42``.
    vault_path : str, optional
        HDF5 file to operate on.  Defaults to the raw clinical vault.

    Returns
    -------
    bool
        True if the dataset existed and was deleted, False otherwise.
    """
    path = Path(vault_path) if vault_path else get_hdf5_path()
    if not path.exists():
        return False

    with _get_lock(path):
        with h5py.File(str(path), "a") as f:
            if visit_id not in f:
                return False
            grp = f[visit_id]
            if dataset_name not in grp:
                return False
            del grp[dataset_name]
            # Remove the group itself if it is now empty
            if len(grp) == 0:
                del f[visit_id]
            return True


def delete_visit_group(
    visit_id: str,
    vault_path: str | None = None,
) -> bool:
    """
    Delete an entire visit group and all its datasets from the vault.

    Parameters
    ----------
    visit_id : str
        Visit group to remove.
    vault_path : str, optional
        HDF5 file to operate on.  Defaults to the raw clinical vault.

    Returns
    -------
    bool
        True if the group existed and was deleted, False otherwise.
    """
    path = Path(vault_path) if vault_path else get_hdf5_path()
    if not path.exists():
        return False

    with _get_lock(path):
        with h5py.File(str(path), "a") as f:
            if visit_id not in f:
                return False
            del f[visit_id]
            return True
