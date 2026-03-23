import os
import sys
import asyncio
from fastapi.testclient import TestClient

sys.path.insert(0, r"c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Microservices")

from labs_service.main import app

client = TestClient(app)

payload = {
    'stay_id': '000005', 
    'report_id': '000005', 
    'report_type': 'blood', 
    'file_path': 'C:\\Users\\anuro\\OneDrive\\Desktop\\Causal Multimodal Medical Modelling System\\storage\\uploads\\assessment\\TEST_LAB_dyOg3bN.pdf', 
    'icu_intime': '2026-03-12T10:50:41.257701+00:00'
}

print("Running labs test client...")
try:
    # We want to see the error raise directly, so tell TestClient to raise server exceptions
    client = TestClient(app, raise_server_exceptions=True)
    resp = client.post("/process-labs-by-path", json=payload)
    print("Success:", resp.json())
except Exception as e:
    import traceback
    traceback.print_exc()
