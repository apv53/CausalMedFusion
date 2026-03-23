from django.db import models
from visits.models import Visit
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import os


class Assessment(models.Model):
    """
    Represents a single 4-hour temporal window within a visit.
    One Assessment per window_id (1-6) per visit.
    """

    assessment_id = models.CharField(max_length=6, unique=True, blank=True)

    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name="assessments",
    )

    window_id = models.IntegerField(
        help_text="1-6, representing the 4-hour window index from admission",
    )

    time_window_start = models.DateTimeField()
    time_window_end = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)
            self.assessment_id = str(self.pk).zfill(6)
            super().save(update_fields=["assessment_id"])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.assessment_id} - Visit {self.visit.visit_id} - Window {self.window_id}"


class AssessmentFile(models.Model):
    """
    Represents a single file uploaded for an assessment window.

    For radiography_image and clinical_notes, the embedding is written to
    clinical_embeddings.h5 keyed as <window_id>_<modality>_<id>.

    For vitals and labs, extracted measurements are written to the
    VitalMeasurement / LabMeasurement tables with this file as source_file.

    aggregation_status tracks whether this file's data has been incorporated
    into window_store.h5 by the Window Aggregator service.
    """

    CATEGORY_CHOICES = [
        ("radiography_image", "Radiography Image"),
        ("clinical_notes", "Clinical Notes"),
        ("vitals", "Vitals"),
        ("labs", "Labs"),
    ]

    PROCESSING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    EMBEDDING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("not_applicable", "N/A"),
    ]

    AGGREGATION_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("aggregated", "Aggregated"),
        ("failed", "Failed"),
    ]

    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="files",
    )

    file = models.FileField(upload_to="assessment/")

    file_type_label = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="e.g., PA, AP, LL for CXR; AR, RR for reports",
    )

    data_category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
    )

    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default="pending",
    )

    embedding_status = models.CharField(
        max_length=20,
        choices=EMBEDDING_STATUS_CHOICES,
        default="not_applicable",
    )

    aggregation_status = models.CharField(
        max_length=20,
        choices=AGGREGATION_STATUS_CHOICES,
        default="pending",
        help_text=(
            "Tracks whether this file's data has been incorporated into "
            "window_store.h5. Reset to 'pending' when the file is part of "
            "a window that needs re-aggregation."
        ),
    )

    # Only used for CXR images and reports
    charttime = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Actual time the measurement or image was taken.",
    )

    # Arbitrary metadata returned by microservices
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["charttime", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.pk and self.embedding_status == "not_applicable":
            if self.data_category in ["radiography_image", "clinical_notes"]:
                self.embedding_status = "pending"
        super().save(*args, **kwargs)

    def clean(self):
        if self.data_category in ["radiography_image", "clinical_notes"]:
            if not self.charttime:
                raise ValidationError(
                    "charttime is required for radiography images and clinical reports."
                )

    def __str__(self):
        return (
            f"File {self.id} ({self.data_category}) "
            f"- Assessment {self.assessment.assessment_id}"
        )


class LabMeasurement(models.Model):
    """
    Stores normalised lab measurements extracted from a single lab PDF.

    One row per (source_file, visit, window_id).
    Cascade-deleted when the source AssessmentFile is deleted,
    which triggers re-aggregation of the affected window.
    """

    source_file = models.ForeignKey(
        AssessmentFile,
        on_delete=models.CASCADE,
        related_name="lab_measurements",
        help_text="The assessment file (Labs PDF/CSV) that provided this measurement.",
        null=True, blank=True
    )

    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name="lab_measurements",
    )

    window_id = models.IntegerField(
        help_text="1-6, the 4-hour window these measurements belong to.",
    )

    measurements = models.JSONField(
        default=list,
        help_text=(
            "Array of normalised lab events. "
            "Each event: {lab_type, lab_value, t_global, t_window}."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["window_id"]
        unique_together = [("source_file", "visit", "window_id")]

    def __str__(self):
        return (
            f"Labs - Visit {self.visit.visit_id} "
            f"- Window {self.window_id} "
            f"- File {self.source_file_id}"
        )


class VitalMeasurement(models.Model):
    """
    Stores normalised vital measurements extracted from a single vitals PDF.

    One row per (source_file, visit, window_id).
    Cascade-deleted when the source AssessmentFile is deleted,
    which triggers re-aggregation of the affected window.
    """

    source_file = models.ForeignKey(
        AssessmentFile,
        on_delete=models.CASCADE,
        related_name="vital_measurements",
        help_text="The assessment file (Vitals PDF/CSV) that provided this measurement.",
        null=True, blank=True
    )

    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name="vital_measurements",
    )

    window_id = models.IntegerField(
        help_text="1-6, the 4-hour window these measurements belong to.",
    )

    measurements = models.JSONField(
        default=list,
        help_text=(
            "Array of normalised vital snapshots. "
            "Each event: {vital_type, vital_mean, vital_std, "
            "vital_last, vital_count, t_global, t_window}."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["window_id"]
        unique_together = [("source_file", "visit", "window_id")]

    def __str__(self):
        return (
            f"Vitals - Visit {self.visit.visit_id} "
            f"- Window {self.window_id} "
            f"- File {self.source_file_id}"
        )


class AnalysisResult(models.Model):
    """
    Stores the output of a single incremental inference run for a visit.

    Each row represents severity S_n — derived from all windows 1..n
    available at the time of inference. assessments_used records the
    Assessment PKs of the windows that contributed to this result.

    is_stale is set True when a source file is deleted and the window
    data changes, invalidating this result. A fresh inference run
    produces a new non-stale row; stale rows are retained as audit history.
    """

    analysis_id = models.CharField(max_length=6, unique=True, blank=True)

    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name="analysis_results",
        help_text="The patient visit this inference result belongs to.",
        null=True, blank=True
    )

    # JSON array of Assessment PKs that contributed windows to this result.
    # e.g. [1, 2, 3] means S_3 was computed from windows belonging to
    # Assessment PKs 1, 2, and 3.
    assessments_used = models.JSONField(
        default=list,
        help_text="List of Assessment PKs whose windows were used to compute this result.",
    )

    # The severity index n — how many windows were used (1-6)
    severity_index = models.IntegerField(
        default=1,
        help_text="n in S_n — number of 4-hour windows used for this inference run.",
    )

    # UUID generated by the inference microservice for this inference run
    inference_id = models.UUIDField(
        unique=True,
        default=None,
        null=True,
        blank=True,
        help_text="UUID generated by the inference service for this result row.",
    )

    # Calibrated inference output probabilities (all in [0, 1])
    severity_score  = models.FloatField(default=0.0)
    mortality_risk  = models.FloatField(default=0.0)
    vent_prob       = models.FloatField(default=0.0)
    dialysis_prob   = models.FloatField(default=0.0)
    mechanical_prob = models.FloatField(default=0.0)
    cardiac_prob    = models.FloatField(default=0.0)
    global_sev_prob = models.FloatField(default=0.0)

    # Natural language narrative generated by the inference service
    assessment_report = models.TextField(default="")

    # Staleness flag — set True when a contributing file is deleted
    # and the window data no longer matches this result.
    # The row is kept as audit history; fresh inference produces a new row.
    is_stale = models.BooleanField(
        default=False,
        help_text=(
            "True when a source file deletion has invalidated this result. "
            "A new inference run will produce a fresh non-stale row."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)
            self.analysis_id = str(self.pk).zfill(6)
            super().save(update_fields=["analysis_id"])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        stale_tag = " [STALE]" if self.is_stale else ""
        return (
            f"Analysis {self.analysis_id} "
            f"(Visit {self.visit.visit_id}, S{self.severity_index})"
            f"{stale_tag}"
        )


# ── Deletion Signal ────────────────────────────────────────────────────────────

@receiver(pre_delete, sender=AssessmentFile)
def delete_assessment_file_on_delete(sender, instance, **kwargs):
    """
    Triggered right before an AssessmentFile is deleted. Performs five steps:

    1. Delete physical file from disk.
    2. Delete embedding dataset from clinical_embeddings.h5 (CXR/report only).
    3. Delete the window group from window_store.h5 for (visit_id, window_id).
    4. Reset aggregation_status to 'pending' on all remaining AssessmentFile
       rows for the same (visit, window_id), so the next inference request
       triggers a clean re-aggregation of that window.
    5. Mark all AnalysisResult rows for the visit as stale, since the window
       data has changed and existing results no longer reflect current inputs.
    """

    # ── Step 1: Delete physical file from disk ────────────────────────────────
    if instance.file and hasattr(instance.file, "path"):
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)

    # ── Step 2: Delete embedding from clinical_embeddings.h5 ─────────────────
    _MODALITY_MAP = {
        "radiography_image": "cxr",
        "clinical_notes": "report",
    }
    modality = _MODALITY_MAP.get(instance.data_category)
    if modality:
        visit_id   = instance.assessment.visit.visit_id
        window_id  = instance.assessment.window_id
        file_id    = str(instance.id)
        dataset_name = f"{window_id}_{modality}_{file_id}"

        from pathlib import Path as _Path
        _project_root = _Path(__file__).resolve().parent.parent.parent
        emb_vault = str(
            _project_root / "storage" / "clinical_embeddings" / "clinical_embeddings.h5"
        )

        try:
            from shared.hdf5_manager import delete_dataset
        except ImportError:
            import sys
            ms_root = str(_project_root / "Microservices")
            if ms_root not in sys.path:
                sys.path.insert(0, ms_root)
            from shared.hdf5_manager import delete_dataset

        try:
            delete_dataset(visit_id, dataset_name, vault_path=emb_vault)
        except Exception:
            pass  # Best effort

    # ── Step 3 & 4: Aggregator HDF5 cleanup and sibling status reset ─────────────
    if instance.aggregation_status == "aggregated":
        affected_window_id = instance.assessment.window_id
        visit_id = instance.assessment.visit.visit_id
        
        # Reset remaining files of the SAME category to pending
        (
            AssessmentFile.objects
            .filter(
                assessment__visit=instance.assessment.visit,
                assessment__window_id=affected_window_id,
                data_category=instance.data_category
            )
            .exclude(pk=instance.pk)
            .update(aggregation_status="pending")
        )
        
        from pathlib import Path as _Path
        _project_root = _Path(__file__).resolve().parent.parent.parent
        window_store_path = str(
            _project_root / "Microservices" / "shared" / "model_inputs" / "window_store.h5"
        )
        
        try:
            import h5py
            from filelock import FileLock
            
            group_key = f"{visit_id}/w{affected_window_id}"
            
            category_mapping = {
                "radiography_image": ["cxr", "cxr_meta"],
                "clinical_notes": ["report", "report_meta"],
                "vitals": ["vitals"],
                "labs": ["labs"]
            }
            datasets_to_delete = category_mapping.get(instance.data_category, [])
            
            if os.path.isfile(window_store_path):
                # Safely delete the specific arrays with file lock to prevent corruption
                lock = FileLock(f"{window_store_path}.lock", timeout=10)
                with lock:
                    with h5py.File(window_store_path, "a") as f:
                        if group_key in f:
                            grp = f[group_key]
                            for ds_name in datasets_to_delete:
                                if ds_name in grp:
                                    del grp[ds_name]
                            
                            # If group is now entirely empty, we could delete the group, 
                            # but keeping it is harmless and allows seamless appending later.
        except Exception as e:
            # Do not raise — deletion of the HDF5 tensor is best-effort on Django side
            import logging
            logging.getLogger(__name__).error(f"Failed to delete aggregator tensor: {e}")

    # ── Step 5: Mark all AnalysisResults for the visit as stale ──────────────
    AnalysisResult.objects.filter(
        visit=instance.assessment.visit
    ).update(is_stale=True)