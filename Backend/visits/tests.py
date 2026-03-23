from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from patients.models import Patient
from visits.models import Visit

User = get_user_model()

class VisitsAppTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.doctor = User.objects.create_user(
            username="doctor_user",
            password="testpassword",
            role="Doctor",
            is_approved=True
        )
        self.client.force_authenticate(user=self.doctor)
        
        self.patient = Patient.objects.create(
            name="John Smith",
            age=50,
            gender="Male",
            phone="555-0000",
            email="john.smith@example.com"
        )

    def test_visit_model_creation(self):
        """Test Visit model saves and auto-generates visit_id."""
        visit = Visit.objects.create(patient=self.patient)
        self.assertIsNotNone(visit.id)
        self.assertEqual(visit.visit_id, str(visit.id).zfill(6))
        self.assertEqual(str(visit), f"{visit.visit_id} - {self.patient.name}")

    def test_create_visit_api(self):
        """Test POST /api/visits/ linking to patient."""
        url = "/api/visits/"
        data = {
            "patient": self.patient.id
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Visit.objects.count(), 1)
        self.assertEqual(response.data["patient"], self.patient.id)
        self.assertIn("visit_id", response.data)

    def test_list_visits_api(self):
        """Test GET /api/visits/"""
        Visit.objects.create(patient=self.patient)
        url = "/api/visits/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Using DRF, it might return paginated results, so check if list or inside 'results'
        data = response.data
        if isinstance(data, dict) and "results" in data:
            self.assertEqual(len(data["results"]), 1)
        else:
            self.assertEqual(len(data), 1)
