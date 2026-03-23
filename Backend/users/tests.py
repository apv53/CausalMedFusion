from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from users.models import SignupRequest

User = get_user_model()

class UsersAppTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create an admin user
        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="testpassword",
            role="Admin",
            is_approved=True
        )
        # Create a doctor user
        self.doctor_user = User.objects.create_user(
            username="doctor_user",
            password="testpassword",
            role="Doctor",
            is_approved=True
        )

    def test_signup_submission(self):
        """Test submitting a signup request via API."""
        url = "/api/auth/signup/"
        data = {
            "username": "new_doctor",
            "email": "new@doctor.com",
            "password": "securepassword",
            "role": "Doctor"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SignupRequest.objects.count(), 1)
        sr = SignupRequest.objects.first()
        self.assertEqual(sr.username, "new_doctor")
        self.assertFalse(sr.is_processed)

    def test_login_success(self):
        """Test login to receive JWT."""
        url = "/api/auth/login/"
        response = self.client.post(url, {"username": "doctor_user", "password": "testpassword"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_failure(self):
        """Test login with wrong password."""
        url = "/api/auth/login/"
        response = self.client.post(url, {"username": "doctor_user", "password": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_pending_requests_admin_only(self):
        """Test that only admins can view pending requests."""
        # Create a pending request
        SignupRequest.objects.create(
            username="pending_dr",
            email="p@test.com",
            password="pwd",
            role="Doctor"
        )
        url = "/api/auth/pending/"
        
        # As Doctor (Forbidden by logic, actually returns empty or 403)
        self.client.force_authenticate(user=self.doctor_user)
        # Assuming the view returns empty queryset for non-admins as per views.py
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # As Admin
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_approve_signup(self):
        """Test admin approving a request creates a User."""
        sr = SignupRequest.objects.create(
            username="approve_me",
            email="a@test.com",
            password="hashed",
            role="Doctor"
        )
        url = f"/api/auth/approve/{sr.id}/"
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        sr.refresh_from_db()
        self.assertTrue(sr.is_processed)
        self.assertTrue(sr.is_approved)
        
        # Check user was created
        new_user = User.objects.get(username="approve_me")
        self.assertTrue(new_user.is_approved)
        self.assertEqual(new_user.role, "Doctor")

    def test_me_endpoint(self):
        """Test me endpoint returns user details."""
        url = "/api/me/"
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "doctor_user")
        self.assertEqual(response.data["role"], "Doctor")
