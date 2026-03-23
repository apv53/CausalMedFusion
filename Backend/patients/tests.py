from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from patients.models import Patient

User = get_user_model()

class PatientsAppTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.doctor = User.objects.create_user(
            username="doctor_user",
            password="testpassword",
            role="Doctor",
            is_approved=True
        )
        self.client.force_authenticate(user=self.doctor)
        
        self.patient_data = {
            "name": "Jane Doe",
            "age": 45,
            "gender": "Female",
            "phone": "555-1234",
            "email": "jane.doe@example.com"
        }

    def test_patient_model_creation(self):
        """Test Patient model saves and auto-generates patient_id."""
        patient = Patient.objects.create(**self.patient_data)
        self.assertIsNotNone(patient.id)
        self.assertEqual(patient.patient_id, str(patient.id).zfill(6))
        self.assertEqual(str(patient), f"{patient.patient_id} - {patient.name}")

    def test_create_patient_api(self):
        """Test POST /api/patients/"""
        url = "/api/patients/"
        response = self.client.post(url, self.patient_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(response.data["name"], "Jane Doe")
        self.assertIn("patient_id", response.data)

    def test_list_patients_api(self):
        """Test GET /api/patients/"""
        Patient.objects.create(**self.patient_data)
        url = "/api/patients/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Using DRF, it might return paginated results, so check if list or inside 'results'
        data = response.data
        if isinstance(data, dict) and "results" in data:
            self.assertEqual(len(data["results"]), 1)
        else:
            self.assertEqual(len(data), 1)
