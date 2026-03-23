import os
import django
import sys
import requests

sys.path.insert(0, r"c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from assessments.models import AssessmentFile

files = AssessmentFile.objects.filter(data_category='labs').order_by('-id')
if not files.exists():
    print("No labs files found!")
else:
    target = files.first()
    print(f"Testing raw request on labs file {target.id}")
    
    payload = {
        "stay_id": str(target.assessment.visit.visit_id),
        "report_id": str(target.assessment.visit.visit_id),
        "report_type": "blood",
        "file_path": target.file.path,
        "icu_intime": target.assessment.visit.admit_timestamp.isoformat(),
    }
    
    print("Payload:", payload)
    try:
        resp = requests.post("http://localhost:8003/process-labs-by-path", json=payload)
        print("Status Code:", resp.status_code)
        print("Response Body:", resp.text)
    except Exception as e:
        print("Request failed:", e)
