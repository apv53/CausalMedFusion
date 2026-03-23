import os
import django
import sys

sys.path.insert(0, r"c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

with connection.cursor() as c:
    c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='assessments_analysisresult';")
    cols = [r[0] for r in c.fetchall()]
    print("Columns in assessments_analysisresult:")
    for col in cols:
        print(f" - {col}")
