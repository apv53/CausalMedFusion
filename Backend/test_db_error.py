import os
import sys
import django
import requests

sys.path.append(r'c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assessments.models import AssessmentFile

f = AssessmentFile.objects.get(id=101)

# Raw requests call to see exactly what fails
payload = {
    "image_name": str(f.id),
    "file_id": str(f.id),
    "stay_id": str(f.assessment.id),
    "patient_id": str(f.assessment.visit.patient.patient_id),
    "visit_id": str(f.assessment.visit.visit_id),
    "assessment_id": str(f.assessment.assessment_id),
    "window_id": f.assessment.window_id,
    "view_position": getattr(f.assessment.visit, 'view_position', "AP"),
    "file_path": f.file.path,
    "icu_intime": f.assessment.visit.admit_timestamp.isoformat(),
    "record_time": f.assessment.visit.admit_timestamp.isoformat(),
}
print(f"Payload: {payload}")
url = "http://localhost:8009/v1/process-image"
print(f"URL: {url}")
res = requests.post(url, json=payload)
print(f"Status Code: {res.status_code}")
print(f"Response: {res.text}")
