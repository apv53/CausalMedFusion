from django.db import models
from patients.models import Patient

class Visit(models.Model):
    visit_id = models.CharField(max_length=6, unique=True, blank=True)

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="visits"
    )

    admit_timestamp = models.DateTimeField(auto_now_add=True)
    discharge_timestamp = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Save first to get auto ID
        super().save(*args, **kwargs)

        if not self.visit_id:
            self.visit_id = str(self.id).zfill(6)
            super().save(update_fields=["visit_id"])

    def __str__(self):
        return f"{self.visit_id} - {self.patient.name}"
