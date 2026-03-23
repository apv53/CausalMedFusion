from rest_framework import serializers
from .models import Assessment, AssessmentFile, LabMeasurement, VitalMeasurement, AnalysisResult
import json


class LabMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabMeasurement
        fields = "__all__"


class VitalMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalMeasurement
        fields = "__all__"


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = "__all__"
        read_only_fields = ["analysis_id", "is_stale", "created_at"]






class AssessmentFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssessmentFile
        fields = "__all__"
        read_only_fields = ["processing_status", "embedding_status", "aggregation_status"]

    def create(self, validated_data):
        """
        Handle multipart metadata and extract file_type_label and charttime.
        """
        from django.utils.dateparse import parse_datetime

        metadata = validated_data.get("metadata")

        # Convert metadata string → dict
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        if metadata:
            validated_data["metadata"] = metadata

            # Extract file_type_label from metadata
            file_type_label = metadata.get("view_label") or metadata.get("type_label") or ""
            validated_data["file_type_label"] = file_type_label

            # Extract charttime from metadata if not already set
            if not validated_data.get("charttime") and metadata.get("charttime"):
                parsed = parse_datetime(metadata["charttime"])
                if parsed:
                    validated_data["charttime"] = parsed

        return AssessmentFile.objects.create(**validated_data)


class AssessmentSerializer(serializers.ModelSerializer):
    files = AssessmentFileSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Assessment
        fields = "__all__"
        read_only_fields = ["assessment_id", "created_at", "time_window_start", "time_window_end"]

    def validate(self, data):
        visit = data["visit"]
        window_id = data.get("window_id")

        if visit.discharge_timestamp is not None:
            raise serializers.ValidationError(
                "Cannot add assessment to a discharged visit."
            )

        if window_id is None:
            raise serializers.ValidationError(
                {"window_id": "window_id is required."}
            )

        if window_id < 1 or window_id > 6:
            raise serializers.ValidationError(
                {"window_id": "window_id must be between 1 and 6."}
            )

        return data

    def create(self, validated_data):
        from datetime import timedelta

        visit = validated_data["visit"]
        window_id = validated_data["window_id"]

        admit = visit.admit_timestamp
        offset_hours = (window_id - 1) * 4

        validated_data["time_window_start"] = admit + timedelta(hours=offset_hours)
        validated_data["time_window_end"] = admit + timedelta(hours=offset_hours + 4)

        return super().create(validated_data)
