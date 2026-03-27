import os
import sys
import django
import requests

sys.path.append(r'c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from visits.models import Visit

v = Visit.objects.get(visit_id="000009")

print(f"Triggering inference for visit {v.visit_id} on port 8010")

url = "http://localhost:8010/v1/infer"
try:
    res = requests.post(url, json={"visit_id": v.visit_id})
    res.raise_for_status()
    data = res.json()
    print(f"Status Code: {res.status_code}")
    print(f"Result dict: {data}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'response') and e.response:
        print(f"Response: {e.response.text}")
