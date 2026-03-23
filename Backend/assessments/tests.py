from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch

from patients.models import Patient
from visits.models import Visit
from assessments.models import Assessment, AssessmentFile

User = get_user_model()

class AssessmentsAppTests(TestCase):
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
            name="Alice Walker",
            age=32,
            gender="Female",
            phone="111-2222",
            email="alice@example.com"
        )
        self.visit = Visit.objects.create(patient=self.patient)

    def test_assessment_model_creation(self):
        """Test Assessment model creation and id generation."""
        assessment = Assessment.objects.create(
            visit=self.visit,
            window_id=1,
            time_window_start=timezone.now(),
            time_window_end=timezone.now() + timezone.timedelta(hours=4)
        )
        self.assertIsNotNone(assessment.id)
        self.assertEqual(assessment.assessment_id, str(assessment.id).zfill(6))
        self.assertEqual(str(assessment), f"{assessment.assessment_id} - Visit {self.visit.visit_id} - Window 1")

    @patch("assessments.views.process_assessment_file_task.apply_async")
    def test_upload_assessment_file(self, mock_apply_async):
        """Test uploading a file to an assessment triggers the celery task mock."""
        assessment = Assessment.objects.create(
            visit=self.visit,
            window_id=1,
            time_window_start=timezone.now(),
            time_window_end=timezone.now() + timezone.timedelta(hours=4)
        )
        
        url = "/api/assessmentfiles/"
        # We simulate a file upload using a simple string buffer wrapped in a simple uploaded file.
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile("test_lab.pdf", b"file_content", content_type="application/pdf")
        
        data = {
            "assessment": assessment.id,
            "data_category": "labs",
            "file": test_file
        }
        
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify it was saved to DB
        self.assertEqual(AssessmentFile.objects.count(), 1)
        a_file = AssessmentFile.objects.first()
        self.assertEqual(a_file.processing_status, "processing")
        self.assertEqual(a_file.data_category, "labs")
        
        # Verify the celery task was called exactly once to prevent real microservice calls
        mock_apply_async.assert_called_once()
        args, kwargs = mock_apply_async.call_args
        # args should be [file_id, 'labs', None] since it's labs
        self.assertEqual(kwargs["args"][0], a_file.id)
        self.assertEqual(kwargs["args"][1], "labs")
        self.assertEqual(kwargs["queue"], "labs_queue")
