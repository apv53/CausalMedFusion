import os
import sys
import django
import requests

sys.path.append(r'c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from visits.models import Visit
from assessments.models import Assessment, AnalysisResult

v = Visit.objects.get(visit_id="000009")

print(f"Testing end-to-end for visit {v.visit_id}")

# 1. Trigger inference on my test port
url = "http://localhost:8010/v1/infer"
res = requests.post(url, json={"visit_id": v.visit_id})
inference_result = res.json()

# 2. Duplicate the logic from run_engine view
assessments_used = list(
    Assessment.objects.filter(visit=v).values_list('id', flat=True)
)

try:
    result = AnalysisResult.objects.create(
        visit=v,
        inference_id=inference_result.get("assessment_id"),
        severity_index=inference_result.get("severity_index", 1),
        assessments_used=assessments_used,
        severity_score=inference_result.get("severity_score") if inference_result.get("severity_score") is not None else 0.0,
        mortality_risk=inference_result.get("mortality_prob") if inference_result.get("mortality_prob") is not None else 0.0,
        vent_prob=inference_result.get("vent_prob") if inference_result.get("vent_prob") is not None else 0.0,
        dialysis_prob=inference_result.get("dialysis_prob") if inference_result.get("dialysis_prob") is not None else 0.0,
        mechanical_prob=inference_result.get("mechanical_prob") if inference_result.get("mechanical_prob") is not None else 0.0,
        cardiac_prob=inference_result.get("cardiac_prob") if inference_result.get("cardiac_prob") is not None else 0.0,
        global_sev_prob=inference_result.get("global_sev_prob") if inference_result.get("global_sev_prob") is not None else 0.0,
        assessment_report=inference_result.get("assessment_report", ""),
        is_stale=False
    )
    print(f"Successfully created AnalysisResult ID: {result.id}")
except Exception as e:
    print(f"Error creating AnalysisResult: {e}")
