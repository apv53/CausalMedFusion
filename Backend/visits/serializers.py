from rest_framework import serializers
from .models import Visit
from patients.serializers import PatientSerializer

class VisitSerializer(serializers.ModelSerializer):
    patient_details = PatientSerializer(source="patient", read_only=True)

    class Meta:
        model = Visit
        fields = "__all__"
        read_only_fields = ["visit_id"]
