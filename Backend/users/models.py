# users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ("Doctor", "Doctor"),
        ("Admin", "Admin"),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="Doctor"
    )

    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"

# users/models.py (add below User)

class SignupRequest(models.Model):
    ROLE_CHOICES = (
        ("Doctor", "Doctor"),
        ("Admin", "Admin"),
    )

    username = models.CharField(max_length=150)
    email = models.EmailField()
    password = models.CharField(max_length=255)  # will store hashed
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    requested_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"
