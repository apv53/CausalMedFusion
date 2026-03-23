from rest_framework import serializers
from .models import Patient
import re

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = "__all__"

    def validate_phone(self, value):
        """Strip non-digit characters (except leading +) and validate length."""
        cleaned = re.sub(r"[^\d+]", "", value.strip())
        digits_only = cleaned.lstrip("+")
        if not digits_only.isdigit() or not (7 <= len(digits_only) <= 15):
            raise serializers.ValidationError(
                "Enter a valid phone number (7-15 digits, optional leading +)."
            )
        return cleaned

