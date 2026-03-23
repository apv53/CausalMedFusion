import os
import django
import sys

sys.path.insert(0, r"c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

tables = [
    'assessments_assessment',
    'assessments_assessmentfile',
    'assessments_labmeasurement',
    'assessments_vitalmeasurement'
]

with connection.cursor() as c:
    for table in tables:
        c.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}';")
        cols = [r[0] for r in c.fetchall()]
        print(f"Columns in {table}:")
        for col in cols:
            print(f" - {col}")
        print()
