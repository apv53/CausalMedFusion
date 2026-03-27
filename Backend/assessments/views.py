from rest_framework import viewsets
from .models import Assessment, AssessmentFile, LabMeasurement, VitalMeasurement, AnalysisResult
from .serializers import (
    AssessmentSerializer,
    AssessmentFileSerializer,
    LabMeasurementSerializer,
    VitalMeasurementSerializer,
    AnalysisResultSerializer,
)

import json
import os
import mimetypes

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from visits.models import Visit
from .tasks import process_assessment_file_task
from .microservices_client import trigger_aggregator, trigger_inference_service
import uuid


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_file(request, file_id):

    file_obj = get_object_or_404(AssessmentFile, id=file_id)

    file_path = file_obj.file.path
    file_name = os.path.basename(file_path)

    content_type, _ = mimetypes.guess_type(file_path)

    if not content_type:
        content_type = "application/octet-stream"

    with open(file_path, "rb") as f:

        response = HttpResponse(
            f.read(),
            content_type=content_type
        )

        response["Content-Disposition"] = f'attachment; filename="{file_name}"'

        return response


class AssessmentViewSet(viewsets.ModelViewSet):

    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer

    def get_queryset(self):

        queryset = super().get_queryset()

        visit_id = self.request.query_params.get("visit")

        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)

        return queryset


class AssessmentFileViewSet(viewsets.ModelViewSet):

    queryset = AssessmentFile.objects.all()
    serializer_class = AssessmentFileSerializer

    def perform_destroy(self, instance):

        assessment = instance.assessment

        instance.delete()

        if not assessment.files.exists():
            assessment.delete()

    def perform_create(self, serializer):

        instance = serializer.save()

        # mark file as processing
        instance.processing_status = "processing"
        instance.save(update_fields=["processing_status"])

        category_map = {
            "radiography_image": "image",
            "clinical_notes": "report",
            "labs": "labs",
            "vitals": "vitals",
        }

        ms_name = category_map.get(instance.data_category)

        if ms_name:

            meta = instance.metadata or {}

            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}

            # Pass correct view/type label for images and reports
            view_pos = instance.file_type_label
            if not view_pos:
                view_pos = "PA" if ms_name == "image" else "AR" if ms_name == "report" else None

            queue_map = {
                "image": "image_queue",
                "report": "report_queue",
                "labs": "labs_queue",
                "vitals": "vitals_queue",
            }

            process_assessment_file_task.apply_async(
                args=[instance.id, ms_name, view_pos],
                queue=queue_map.get(ms_name, "celery"),
            )

    @action(detail=True, methods=["post"])
    def reprocess(self, request, pk=None):

        instance = self.get_object()

        instance.processing_status = "processing"
        instance.save(update_fields=["processing_status"])

        category_map = {
            "radiography_image": "image",
            "clinical_notes": "report",
            "labs": "labs",
            "vitals": "vitals",
        }

        ms_name = category_map.get(instance.data_category)

        if ms_name:

            meta = instance.metadata or {}

            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}

            # Pass correct view/type label for images and reports
            view_pos = instance.file_type_label
            if not view_pos:
                view_pos = "PA" if ms_name == "image" else "AR" if ms_name == "report" else None

            queue_map = {
                "image": "image_queue",
                "report": "report_queue",
                "labs": "labs_queue",
                "vitals": "vitals_queue",
            }

            process_assessment_file_task.apply_async(
                args=[instance.id, ms_name, view_pos],
                queue=queue_map.get(ms_name, "celery"),
            )

        return Response({"status": "Reprocessing started", "file_id": instance.id})


class LabMeasurementViewSet(viewsets.ModelViewSet):

    queryset = LabMeasurement.objects.all()
    serializer_class = LabMeasurementSerializer

    def get_queryset(self):

        queryset = super().get_queryset()

        visit_id = self.request.query_params.get("visit")

        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)

        return queryset


class VitalMeasurementViewSet(viewsets.ModelViewSet):

    queryset = VitalMeasurement.objects.all()
    serializer_class = VitalMeasurementSerializer

    def get_queryset(self):

        queryset = super().get_queryset()

        visit_id = self.request.query_params.get("visit")

        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)

        return queryset


class AnalysisResultViewSet(viewsets.ModelViewSet):

    queryset = AnalysisResult.objects.all()
    serializer_class = AnalysisResultSerializer

    def get_queryset(self):

        queryset = super().get_queryset()

        visit_id = self.request.query_params.get("visit")

        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)

        return queryset.order_by("-created_at")

    @action(detail=False, methods=["post"])
    def run_engine(self, request):
        visit_id = request.data.get("visit")
        if not visit_id:
            return Response({"detail": "visit is required."}, status=status.HTTP_400_BAD_REQUEST)

        from django.shortcuts import get_object_or_404
        visit = get_object_or_404(Visit, id=visit_id)

        # Step 1: Check for pending aggregation files
        has_pending = AssessmentFile.objects.filter(
            assessment__visit=visit,
            aggregation_status="pending"
        ).exists()

        if has_pending:
            success = trigger_aggregator(visit.visit_id)
            if not success:
                return Response(
                    {"detail": "Failed to aggregate files into HDF5. Check ML Gateway logs."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Step 2: Call ONNX inference service
        inference_result = trigger_inference_service(visit.visit_id)
        if inference_result is None:
            return Response(
                {"detail": "Inference service failed. Check ML Gateway logs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Step 3: Persist result to AnalysisResult
        assessments_used = list(
            Assessment.objects.filter(visit=visit).values_list('id', flat=True)
        )

        result = AnalysisResult.objects.create(
            visit=visit,
            inference_id=inference_result.get("assessment_id"),
            severity_index=inference_result.get("severity_index", 1),
            assessments_used=assessments_used,
            severity_score=inference_result.get("severity_score") if inference_result.get("severity_score") is not None else 0.0,
            mortality_risk=inference_result.get("mortality_prob") if inference_result.get("mortality_prob") is not None else 0.0,
            vent_prob=inference_result.get("vent_prob") if inference_result.get("vent_prob") is not None else 0.0,
            dialysis_prob=inference_result.get("dialysis_prob") if inference_result.get("dialysis_prob") is not None else 0.0,
            mechanical_prob=inference_result.get("mechanical_prob") if inference_result.get("mechanical_prob") is not None else 0.0,
            cardiac_prob=inference_result.get("cardiac_prob") if inference_result.get("cardiac_prob") is not None else 0.0,
            global_sev_prob=inference_result.get("global_sev_prob") if inference_result.get("global_sev_prob") is not None else 0.0,
            assessment_report=inference_result.get("assessment_report", ""),
            is_stale=False
        )

        serializer = self.get_serializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

