import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# ── Core Processing Gateway (CPU Bound) URL ──────────
CORE_GATEWAY_URL = getattr(settings, "CORE_GATEWAY_URL", "http://localhost:8001")

IMAGE_SERVICE_URL = CORE_GATEWAY_URL
REPORT_SERVICE_URL = CORE_GATEWAY_URL
LABS_SERVICE_URL = CORE_GATEWAY_URL
VITALS_SERVICE_URL = CORE_GATEWAY_URL


def process_image(assessment_file_id, file_path, view_position, icu_intime, record_time, stay_id=None, patient_id=None, visit_id=None, assessment_id=None, window_id=None, file_id=None):
    """Send file path (shared storage) instead of raw bytes — avoids HTTP file transfer overhead."""
    url = f"{IMAGE_SERVICE_URL}/v1/process-image"

    try:
        payload = {
            "image_name": str(assessment_file_id),
            "file_id": str(file_id) if file_id else str(assessment_file_id),
            "stay_id": str(stay_id) if stay_id else "",
            "patient_id": str(patient_id) if patient_id else "",
            "visit_id": str(visit_id) if visit_id else "",
            "assessment_id": str(assessment_id) if assessment_id else "",
            "window_id": window_id if window_id is not None else 1,
            "view_position": view_position,
            "file_path": file_path,
            "icu_intime": icu_intime if isinstance(icu_intime, str) else icu_intime.isoformat(),
            "record_time": record_time if isinstance(record_time, str) else record_time.isoformat(),
        }
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error processing image {assessment_file_id}: {e}")
        return None


def process_report(report_id, file_path, report_type, icu_intime, time_of_assessment_record, stay_id=None, patient_id=None, visit_id=None, assessment_id=None, window_id=None, file_id=None):
    """Send file path (shared storage) instead of raw bytes."""
    url = f"{REPORT_SERVICE_URL}/v1/process-report-by-path"

    try:
        payload = {
            "report_id": str(report_id),
            "file_id": str(file_id) if file_id else str(report_id),
            "stay_id": str(stay_id) if stay_id else "",
            "patient_id": str(patient_id) if patient_id else "",
            "visit_id": str(visit_id) if visit_id else "",
            "assessment_id": str(assessment_id) if assessment_id else "",
            "window_id": window_id if window_id is not None else 1,
            "report_type": report_type,
            "file_path": file_path,
            "icu_intime": icu_intime if isinstance(icu_intime, str) else icu_intime.isoformat(),
            "time_of_assessment_record": time_of_assessment_record if isinstance(time_of_assessment_record, str) else time_of_assessment_record.isoformat(),
        }
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error processing report {report_id}: {e}")
        return None


def process_labs(stay_id, file_path, report_type, icu_intime):
    """Send file path (shared storage) instead of raw bytes."""
    url = f"{LABS_SERVICE_URL}/process-labs-by-path"

    try:
        payload = {
            "stay_id": str(stay_id),
            "report_id": str(stay_id),
            "report_type": report_type,
            "file_path": file_path,
            "icu_intime": icu_intime if isinstance(icu_intime, str) else icu_intime.isoformat(),
        }
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error processing labs for stay {stay_id}: {e}")
        return None


def trigger_aggregator(stay_id: str) -> bool:
    """Trigger the Window Aggregator service for a specific stay."""
    try:
        url = f"{CORE_GATEWAY_URL}/aggregate"
        resp = requests.post(url, json={"stay_id": stay_id}, timeout=30)
        resp.raise_for_status()
        logger.info(f"Aggregator triggered successfully for stay {stay_id}. Resp: {resp.json()}")
        return True
    except Exception as e:
        logger.error(f"Aggregator call failed for stay {stay_id}: {e}")
        return False


def process_vitals(stay_id, file_paths, icu_intime):
    """Send file paths (shared storage) instead of raw bytes."""
    url = f"{VITALS_SERVICE_URL}/process-vitals-by-path"

    try:
        payload = {
            "stay_id": str(stay_id),
            "file_paths": file_paths if isinstance(file_paths, list) else [file_paths],
            "icu_intime": icu_intime if isinstance(icu_intime, str) else icu_intime.isoformat(),
        }
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error processing vitals for stay {stay_id}: {e}")
        return None


# ── Embedding Service ───────────────────────────────────────────────

EMBEDDING_SERVICE_URL = getattr(settings, "EMBEDDING_SERVICE_URL", "http://localhost:8005")


def embed_single(visit_id, file_id, window_id, modality):
    """
    Trigger embedding extraction for a single file.

    Parameters
    ----------
    modality : str
        'cxr' or 'report'
    """
    endpoint = "embed-cxr" if modality == "cxr" else "embed-report"
    url = f"{EMBEDDING_SERVICE_URL}/v1/{endpoint}"

    try:
        payload = {
            "visit_id": str(visit_id),
            "file_id": str(file_id),
            "window_id": window_id,
        }
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error embedding {modality} file {file_id}: {e}")
        return None


def embed_batch(visit_id, items, modality):
    """
    Trigger batch embedding extraction for multiple files of the same modality.

    Parameters
    ----------
    items : list[dict]
        Each dict has 'file_id' and 'window_id'.
    modality : str
        'cxr' or 'report'
    """
    url = f"{EMBEDDING_SERVICE_URL}/v1/embed-batch"

    try:
        payload = {
            "visit_id": str(visit_id),
            "modality": modality,
            "items": items,
        }
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error batch-embedding {modality} for visit {visit_id}: {e}")
        return None
