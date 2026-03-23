# users/serializers.py

from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import SignupRequest

User = get_user_model()


# =====================================================
# CUSTOM JWT LOGIN SERIALIZER
# =====================================================
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends JWT serializer to:
    - Block login if user not approved
    - Return user info in response
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

        # Block login if admin has not approved
        if not self.user.is_approved:
            raise serializers.ValidationError(
                "Your account is pending admin approval."
            )

        # Enforce single-device login: blacklist all previous tokens for this user
        outstanding_tokens = OutstandingToken.objects.filter(user=self.user)
        for token in outstanding_tokens:
            BlacklistedToken.objects.get_or_create(token=token)

        # Attach user info to response
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "role": self.user.role,
        }

        return data


# =====================================================
# SIGNUP REQUEST SERIALIZER
# =====================================================
class SignupRequestSerializer(serializers.ModelSerializer):
    """
    Handles signup request submission.
    Stores hashed password.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"}
    )

    class Meta:
        model = SignupRequest
        fields = [
            "id",
            "username",
            "email",
            "password",        # IMPORTANT
            "role",
            "requested_at",
            "is_processed",
            "is_approved",
        ]
        read_only_fields = [
            "id",
            "requested_at",
            "is_processed",
            "is_approved",
        ]

    def create(self, validated_data):
        # Hash password before saving
        validated_data["password"] = make_password(
            validated_data["password"]
        )
        return SignupRequest.objects.create(**validated_data)