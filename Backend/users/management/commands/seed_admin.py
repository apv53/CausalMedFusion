"""
seed_admin – Create the first Admin user from environment variables.

Runs idempotently: only creates an Admin if zero Admin users exist.
Designed to run on every container startup (safe to call repeatedly).

Required env vars:
    ADMIN_USERNAME  (default: admin)
    ADMIN_EMAIL     (default: admin@causalmedfusion.com)
    ADMIN_PASSWORD  (REQUIRED – skips seed if missing)
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the first Admin user from environment variables (idempotent)."

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME", "admin")
        email = os.environ.get("ADMIN_EMAIL", "admin@causalmedfusion.com")
        password = os.environ.get("ADMIN_PASSWORD")

        if not password:
            self.stderr.write(self.style.ERROR(
                "❌ ADMIN_PASSWORD env var not set – cannot seed/update admin."
            ))
            return

        # Check if an Admin already exists
        admin_user = User.objects.filter(role="Admin").first()

        if admin_user:
            # Self-healing: ensure credentials match the .env file
            admin_user.set_password(password)
            admin_user.username = username
            admin_user.email = email
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(
                f"✅ Admin '{username}' already exists. Credentials synchronized with .env.docker."
            ))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role="Admin",
            is_approved=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f"✅ Admin user '{username}' created successfully."
        ))
