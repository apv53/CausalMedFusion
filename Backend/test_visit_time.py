import os
import sys
import django
from datetime import datetime, timezone, timedelta

sys.path.append(r'c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from visits.models import Visit
from patients.models import Patient

# Get a patient
p = Patient.objects.first()
if not p:
    print("No patients found. Create one first.")
    sys.exit(1)

# Create a visit with a specific time (1 hour ago)
past_time = datetime.now(timezone.utc) - timedelta(hours=1)
print(f"Creating visit for patient {p.patient_id} with time {past_time}")

v = Visit.objects.create(
    patient=p,
    admit_timestamp=past_time
)

# Fetch back
v_check = Visit.objects.get(id=v.id)
print(f"Created Visit ID: {v_check.visit_id}")
print(f"Saved Timestamp: {v_check.admit_timestamp}")

if abs((v_check.admit_timestamp - past_time).total_seconds()) < 1:
    print("SUCCESS: Manual timestamp preserved!")
else:
    print("FAILURE: Timestamp was overwritten!")

# Cleanup
v_check.delete()
