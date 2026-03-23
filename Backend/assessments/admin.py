from django.contrib import admin
from .models import Assessment, AssessmentFile, LabMeasurement, VitalMeasurement, AnalysisResult

admin.site.register(Assessment)
admin.site.register(AssessmentFile)
admin.site.register(LabMeasurement)
admin.site.register(VitalMeasurement)
admin.site.register(AnalysisResult)
