from django.db import models

class Patient(models.Model):
    GENDER_CHOICES = (
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    )

    patient_id = models.CharField(max_length=6, unique=True, blank=True)

    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=20)
    email = models.EmailField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Save first to get auto ID
        super().save(*args, **kwargs)

        # Generate 6-digit patient_id if not set
        if not self.patient_id:
            self.patient_id = str(self.id).zfill(6)
            super().save(update_fields=["patient_id"])

    def __str__(self):
        return f"{self.patient_id} - {self.name}"
