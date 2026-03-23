# users/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework_simplejwt.views import TokenObtainPairView

from django.contrib.auth import get_user_model

from .models import SignupRequest
from .serializers import (
    SignupRequestSerializer,
    CustomTokenObtainPairSerializer,
)

User = get_user_model()


# ===============================
# LIST PENDING SIGNUP REQUESTS
# ===============================
class PendingSignupRequestsView(ListAPIView):
    serializer_class = SignupRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only Admins can see pending requests
        if self.request.user.role != "Admin":
            return SignupRequest.objects.none()

        return SignupRequest.objects.filter(is_processed=False)


# ===============================
# CUSTOM LOGIN (JWT)
# ===============================
class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ===============================
# SIGNUP REQUEST (PUBLIC)
# ===============================
class SignupView(APIView):
    permission_classes = []  # Public access

    def post(self, request):
        serializer = SignupRequestSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Signup request submitted for approval."},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ===============================
# APPROVE SIGNUP REQUEST
# ===============================
class ApproveSignupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):

        if request.user.role != "Admin":
            return Response(
                {"error": "Only admin can approve requests."},
                status=403,
            )

        try:
            signup_request = SignupRequest.objects.get(id=request_id)
        except SignupRequest.DoesNotExist:
            return Response({"error": "Request not found"}, status=404)

        if signup_request.is_processed:
            return Response({"error": "Already processed"}, status=400)

        # Create actual user
        User.objects.create(
            username=signup_request.username,
            email=signup_request.email,
            password=signup_request.password,  # Already hashed
            role=signup_request.role,
            is_approved=True,
        )

        signup_request.is_processed = True
        signup_request.is_approved = True
        signup_request.save()

        return Response({"message": "User approved successfully"})


# ===============================
# REJECT SIGNUP REQUEST
# ===============================
class RejectSignupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):

        if request.user.role != "Admin":
            return Response(
                {"error": "Only admin can reject requests."},
                status=403,
            )

        try:
            signup_request = SignupRequest.objects.get(id=request_id)
        except SignupRequest.DoesNotExist:
            return Response({"error": "Request not found"}, status=404)

        signup_request.is_processed = True
        signup_request.is_approved = False
        signup_request.save()

        return Response({"message": "Signup request rejected"})

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response({
            "username": user.username,
            "email": user.email,
            "role": user.role,
        })