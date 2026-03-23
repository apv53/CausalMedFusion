from celery import shared_task
from .models import AssessmentFile
from .microservices_client import process_image, process_report, process_labs, process_vitals
import logging
import traceback
import time

logger = logging.getLogger(__name__)

@shared_task
def process_assessment_file_task(file_id, microservice_name, view_position=None):
    """
    Celery task to handle asynchronous microservice processing for Assessment Files.
    Includes timing instrumentation for latency monitoring.
    """
    task_start = time.time()

    try:
        file_instance = AssessmentFile.objects.get(id=file_id)
    except AssessmentFile.DoesNotExist:
        logger.error(f"AssessmentFile with id {file_id} not found.")
        return

    stay_id = str(file_instance.assessment.id)
    assessment_id = file_instance.assessment.assessment_id
    visit_id = file_instance.assessment.visit.visit_id
    patient_id = file_instance.assessment.visit.patient.patient_id
    window_id = file_instance.assessment.window_id

    # stay_intime = ICU admission time (NOT window start)
    admit_ts = file_instance.assessment.visit.admit_timestamp
    icu_intime = admit_ts.isoformat()

    # record_time = charttime (clinical event time)
    # Fallback: if charttime is null, use the window midpoint so
    # t_window produces a meaningful value (~0.5) instead of 1.0
    if file_instance.charttime:
        record_time = file_instance.charttime.isoformat()
    else:
        # Window midpoint = admit + (window_id - 1)*4h + 2h
        from datetime import timedelta
        midpoint = admit_ts + timedelta(hours=(window_id - 1) * 4 + 2)
        record_time = midpoint.isoformat()

    file_path = file_instance.file.path

    print(f"\n[CELERY TEMPORAL DEBUG] file_id={file_id}, window_id={window_id}, "
          f"admit_ts={admit_ts.isoformat()}, charttime={file_instance.charttime}, "
          f"record_time={record_time}, microservice={microservice_name}", flush=True)

    if microservice_name not in ['image', 'report', 'labs', 'vitals']:
        file_instance.processing_status = 'Failed'
        file_instance.metadata = {"error_msg": f"Unknown microservice: {microservice_name}"}
        file_instance.save(update_fields=["processing_status", "metadata"])
        return

    # Status and metadata will be set and saved once at the end (batch DB write)
    final_status = None
    final_metadata = None

    try:
        response_data = None
        ms_start = time.time()

        if microservice_name == 'image':
            response_data = process_image(
                assessment_file_id=file_id,
                file_path=file_path, 
                stay_id=stay_id,
                patient_id=patient_id,
                visit_id=visit_id,
                assessment_id=assessment_id,
                window_id=window_id,
                view_position=view_position, 
                icu_intime=icu_intime, 
                record_time=record_time,
                file_id=str(file_instance.id)
            )
        elif microservice_name == 'report':
            response_data = process_report(
                report_id=file_id,
                file_path=file_path,
                stay_id=stay_id,
                patient_id=patient_id,
                visit_id=visit_id,
                assessment_id=assessment_id,
                window_id=window_id,
                report_type=view_position or "AR",
                icu_intime=icu_intime,
                time_of_assessment_record=record_time,
                file_id=str(file_instance.id)
            )
        elif microservice_name == 'labs':
            response_data = process_labs(
                stay_id=stay_id,
                file_path=file_path,
                report_type="blood",
                icu_intime=icu_intime
            )
        elif microservice_name == 'vitals':
            response_data = process_vitals(
                stay_id=stay_id,
                file_paths=[file_path],
                icu_intime=icu_intime
            )

        ms_elapsed = time.time() - ms_start
        logger.info(
            f"[TIMING] Microservice '{microservice_name}' call for file {file_id} "
            f"took {ms_elapsed:.3f}s"
        )

        if response_data is not None:
            final_status = 'completed'
            final_metadata = response_data

            # ── Persist lab/vital measurements to new tables ──────────
            _persist_measurements(file_instance, microservice_name, response_data)
        else:
            final_status = 'failed'
            final_metadata = {"error_msg": "Microservice returned an empty response."}

    except Exception as e:
        logger.error(f"Microservice error for file {file_id}: {str(e)}")
        traceback.print_exc()
        final_status = 'failed'
        final_metadata = {"error_msg": str(e)}

    finally:
        # Single batched DB write: update processing_status + metadata in one save
        file_instance.processing_status = final_status
        file_instance.metadata = final_metadata
        file_instance.save(update_fields=["processing_status", "metadata"])

        total_elapsed = time.time() - task_start
        logger.info(
            f"[TIMING] Total task for file {file_id} ({microservice_name}) "
            f"completed in {total_elapsed:.3f}s | status={final_status}"
        )

        # ── After-completion: trigger embeddings if ALL files are done ──
        # Any file completion should trigger the check, in case it was the final 
        # file holding up a pending image/report embedding.
        _trigger_embeddings_if_all_done(file_instance.assessment)


def _persist_measurements(file_instance, microservice_name, response_data):
    """
    Create LabMeasurement / VitalMeasurement Django ORM rows from the
    microservice response.  Uses update_or_create so reprocessing is
    idempotent.
    """
    from .models import LabMeasurement, VitalMeasurement

    measurements_by_window = response_data.get("measurements_by_window", {})
    if not measurements_by_window:
        return

    visit = file_instance.assessment.visit

    if microservice_name == "labs":
        for window_id_str, measurements in measurements_by_window.items():
            window_id = int(window_id_str)
            LabMeasurement.objects.update_or_create(
                source_file=file_instance,
                visit=visit,
                window_id=window_id,
                defaults={"measurements": measurements},
            )
    elif microservice_name == "vitals":
        for window_id_str, measurements in measurements_by_window.items():
            window_id = int(window_id_str)
            VitalMeasurement.objects.update_or_create(
                source_file=file_instance,
                visit=visit,
                window_id=window_id,
                defaults={"measurements": measurements},
            )


def _trigger_embeddings_if_all_done(assessment):
    """
    Check if every file in the assessment has reached a terminal state
    (completed / failed). If so, generate embeddings for the completed
    CXR and report files.
    """
    from .models import AssessmentFile

    all_files = AssessmentFile.objects.filter(assessment=assessment)
    terminal_states = {"completed", "failed"}

    # Only proceed if every sibling file is done processing
    if all_files.exclude(processing_status__in=terminal_states).exists():
        logger.info(
            f"[EMBEDDING] Assessment {assessment.assessment_id}: "
            f"some files still processing — deferring embeddings"
        )
        return

    logger.info(
        f"[EMBEDDING] Assessment {assessment.assessment_id}: "
        f"all files done — triggering embedding generation"
    )

    try:
        from .embedding_helpers import trigger_embeddings_for_assessment
        trigger_embeddings_for_assessment(assessment)
    except Exception as e:
        logger.error(f"[EMBEDDING] Failed to generate embeddings: {e}")
        traceback.print_exc()

    # Trigger Aggregator after embeddings are requested
    trigger_aggregator_task.delay(str(assessment.id))


@shared_task
def trigger_aggregator_task(stay_id: str):
    from .microservices_client import trigger_aggregator
    trigger_aggregator(stay_id)

