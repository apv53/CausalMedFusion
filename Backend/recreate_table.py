import os
import django
import sys

sys.path.insert(0, r"c:\Users\anuro\OneDrive\Desktop\Causal Multimodal Medical Modelling System\Backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection
from assessments.models import AnalysisResult

with connection.cursor() as cursor:
    # Drop the table and any constraints
    cursor.execute('DROP TABLE IF EXISTS assessments_analysisresult CASCADE;')
    print("Dropped old assessments_analysisresult table.")

# Use Django's schema editor to create the table based on CURRENT models.py
with connection.schema_editor() as schema_editor:
    schema_editor.create_model(AnalysisResult)
    print("Re-created assessments_analysisresult table using latest model schema.")
