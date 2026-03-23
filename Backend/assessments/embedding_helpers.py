"""
Embedding Routing Helper
=========================
Shared logic for determining which files need embeddings and routing
to the appropriate endpoint (single vs batch per modality).

Called from:
  - tasks.py      — after all raw processing in an assessment finishes
  - views.py      — as a safety net before running the severity engine
"""

import sys
import logging
from pathlib import Path as _Path

logger = logging.getLogger(__name__)

# ── Modality mapping ────────────────────────────────────────────────

_MODALITY_MAP = {
    "radiography_image": "cxr",
    "clinical_notes": "report",
}


def _get_embedding_exists_fn():
    """Import embedding_exists from the Microservices shared package."""
    try:
        _project_root = _Path(__file__).resolve().parent.parent.parent
        ms_root = str(_project_root / "Microservices")
        if ms_root not in sys.path:
            sys.path.insert(0, ms_root)
        from shared.hdf5_embeddings_manager import embedding_exists
        return embedding_exists
    except ImportError:
        logger.warning("[EMBEDDING] Could not import embedding_exists — skipping existence check")
        return None


def trigger_embeddings_for_assessment(assessment):
    """
    Check all completed CXR/report files in the given assessment and
    generate embeddings for any that are missing.

    Routing per modality:
      - ≥2 files  → batch endpoint
      - 1 file    → single endpoint
    """
    from .models import AssessmentFile
    from .microservices_client import embed_single, embed_batch

    visit_id = assessment.visit.visit_id

    # Find completed CXR/report files
    completed_files = AssessmentFile.objects.filter(
        assessment=assessment,
        processing_status="completed",
        data_category__in=["radiography_image", "clinical_notes"],
    )

    if not completed_files.exists():
        return

    embedding_exists = _get_embedding_exists_fn()

    # Group pending files by modality
    pending_by_modality = {}  # modality -> list of {file_id, window_id}

    for f in completed_files:
        modality = _MODALITY_MAP.get(f.data_category)
        if not modality:
            continue

        dataset_name = f"{f.assessment.window_id}_{modality}_{f.id}"

        # Skip if embedding already exists
        if embedding_exists and embedding_exists(visit_id, dataset_name):
            if f.embedding_status != "completed":
                f.embedding_status = "completed"
                f.save(update_fields=["embedding_status"])
            continue

        pending_by_modality.setdefault(modality, []).append({
            "file_id": str(f.id),
            "window_id": f.assessment.window_id,
            "obj": f,
        })

    if not pending_by_modality:
        logger.info(f"[EMBEDDING] All embeddings up-to-date for assessment {assessment.assessment_id}")
        return

    # Route to batch or single endpoint per modality
    for modality, items in pending_by_modality.items():
        # Set all to processing before network call
        for item in items:
            item["obj"].embedding_status = "processing"
            item["obj"].save(update_fields=["embedding_status"])

        if len(items) >= 2:
            logger.info(
                f"[EMBEDDING] Batch embedding {len(items)} {modality} files "
                f"for visit {visit_id}"
            )
            batch_payload = [{"file_id": i["file_id"], "window_id": i["window_id"]} for i in items]
            res = embed_batch(visit_id, batch_payload, modality)
            
            new_status = "completed" if res else "failed"
            for item in items:
                item["obj"].embedding_status = new_status
                item["obj"].save(update_fields=["embedding_status"])
        else:
            for item in items:
                logger.info(
                    f"[EMBEDDING] Single embedding {modality} file "
                    f"{item['file_id']} for visit {visit_id}"
                )
                res = embed_single(
                    visit_id,
                    item["file_id"],
                    item["window_id"],
                    modality,
                )
                item["obj"].embedding_status = "completed" if res else "failed"
                item["obj"].save(update_fields=["embedding_status"])
