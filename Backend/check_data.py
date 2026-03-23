import os
import django
import sys

sys.path.insert(0, r"c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

with connection.cursor() as c:
    c.execute("SELECT count(*) FROM assessments_analysisresult;")
    count = c.fetchone()[0]
    print(f"Row count in assessments_analysisresult: {count}")
