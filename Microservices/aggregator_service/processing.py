"""
Core processing logic for the Window Aggregator Service.
Fetches embeddings and DB measurements, structures them as tensors,
and sends them to storage.
"""
from __future__ import annotations

import logging
from typing import Any
from collections import defaultdict

import numpy as np

from aggregator_service.db_client import (
    fetch_pending_files,
    update_aggregation_status,
    fetch_vital_measurements,
    fetch_lab_measurements
)
from aggregator_service.storage import append_to_window_store
from shared.hdf5_embeddings_manager import read_raw_dataset, read_embedding_dataset

logger = logging.getLogger(__name__)

async def process_pending_files_for_stay(stay_id: str) -> tuple[int, list[int], list[str]]:
    """
    Main pipeline:
    1. Fetch all pending AssessmentFiles for stay_id.
    2. Group by window_id.
    3. For each window, extract modalities into properly shaped numpy arrays.
    4. Sort arrays by t_global.
    5. Append to window_store.h5.
    6. Mark as 'aggregated'.
    """
    pending_files = await fetch_pending_files(stay_id)
    if not pending_files:
        return 0, [], []

    # Group by window_id
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in pending_files:
        grouped[row['window_id']].append(row)

    processed_file_ids = []
    errors = []
    modified_windows = []

    for window_id, files in grouped.items():
        # Holds the new rows for this window
        collected = {
            "cxr": [], "cxr_meta": [],
            "report": [], "report_meta": [],
            "vitals": [], "labs": []
        }

        window_file_ids = []

        for f in files:
            file_id = f['file_id']
            cat = f['data_category']

            try:
                if cat == 'radiography_image':
                    dataset_name = f"{window_id}_cxr_{file_id}"
                    emb, attrs = read_embedding_dataset(stay_id, dataset_name)
                    if isinstance(emb, np.ndarray):
                        collected["cxr"].append(emb)
                        meta_row = [
                            attrs.get("view_label", 0),
                            attrs.get("t_global", 0.0),
                            attrs.get("t_window", 0.0)
                        ]
                        collected["cxr_meta"].append(meta_row)
                        window_file_ids.append(file_id)

                elif cat == 'clinical_notes':
                    dataset_name = f"{window_id}_report_{file_id}"
                    emb, attrs = read_embedding_dataset(stay_id, dataset_name)
                    if isinstance(emb, np.ndarray):
                        collected["report"].append(emb)
                        meta_row = [
                            attrs.get("type_label", 0),
                            attrs.get("t_global", 0.0),
                            attrs.get("t_window", 0.0)
                        ]
                        collected["report_meta"].append(meta_row)
                        window_file_ids.append(file_id)

                elif cat == 'vitals':
                    events = await fetch_vital_measurements(file_id)
                    for ev in events:
                        collected["vitals"].append([
                            ev["vital_type"], ev["vital_mean"], ev["vital_std"],
                            ev["vital_last"], ev["vital_count"],
                            ev["t_global"], ev["t_window"]
                        ])
                    window_file_ids.append(file_id)

                elif cat == 'labs':
                    events = await fetch_lab_measurements(file_id)
                    for ev in events:
                        collected["labs"].append([
                            ev["lab_type"], ev["lab_value"],
                            ev["t_global"], ev["t_window"]
                        ])
                    window_file_ids.append(file_id)

            except Exception as e:
                errors.append(f"window={window_id} file_id={file_id} error: {str(e)}")
        
        # Now convert collections to numpy, sort by t_global, and append
        has_new_data = False
        
        # Helper to sort arrays based on a t_global column index
        def _to_sorted_arrays(data_list, meta_list, t_global_col=1):
            if not data_list:
                return np.array([]), np.array([])
            
            arr_data = np.array(data_list, dtype=np.float32)
            if meta_list is not None:
                arr_meta = np.array(meta_list, dtype=np.float32)
                # Sort indices by t_global in meta
                sort_idx = np.argsort(arr_meta[:, t_global_col])
                return arr_data[sort_idx], arr_meta[sort_idx]
            else:
                # Sort directly (vitals t_global is col 5; labs t_global is col 2)
                sort_idx = np.argsort(arr_data[:, t_global_col])
                return arr_data[sort_idx], None

        try:
            # CXR
            cxr_arr, cxr_meta_arr = _to_sorted_arrays(collected["cxr"], collected["cxr_meta"], t_global_col=1)
            if cxr_arr.size > 0:
                append_to_window_store(stay_id, window_id, "cxr", cxr_arr, cxr_meta_arr)
                has_new_data = True

            # Report
            rep_arr, rep_meta_arr = _to_sorted_arrays(collected["report"], collected["report_meta"], t_global_col=1)
            if rep_arr.size > 0:
                append_to_window_store(stay_id, window_id, "report", rep_arr, rep_meta_arr)
                has_new_data = True

            # Vitals
            vit_arr, _ = _to_sorted_arrays(collected["vitals"], None, t_global_col=5)
            if vit_arr.size > 0:
                append_to_window_store(stay_id, window_id, "vitals", vit_arr, None)
                has_new_data = True

            # Labs
            lab_arr, _ = _to_sorted_arrays(collected["labs"], None, t_global_col=2)
            if lab_arr.size > 0:
                append_to_window_store(stay_id, window_id, "labs", lab_arr, None)
                has_new_data = True

            if has_new_data:
                modified_windows.append(window_id)
                processed_file_ids.extend(window_file_ids)

        except Exception as e:
            errors.append(f"Failed to append datasets for window {window_id}: {str(e)}")

    if processed_file_ids:
        await update_aggregation_status(processed_file_ids, 'aggregated')

    return len(processed_file_ids), modified_windows, errors
