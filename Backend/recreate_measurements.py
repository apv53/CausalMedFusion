import os
import django
import sys

sys.path.insert(0, r"c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection
from assessments.models import LabMeasurement, VitalMeasurement

with connection.cursor() as cursor:
    cursor.execute('DROP TABLE IF EXISTS assessments_labmeasurement CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS assessments_vitalmeasurement CASCADE;')
    print("Dropped old measurement tables.")

with connection.schema_editor() as schema_editor:
    schema_editor.create_model(LabMeasurement)
    schema_editor.create_model(VitalMeasurement)
    print("Re-created measurement tables using latest model schema.")
