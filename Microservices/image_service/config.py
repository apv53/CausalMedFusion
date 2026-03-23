"""
Configuration for the image microservice.
"""

import os
from pathlib import Path

# Only allow reading images from this directory
# Default: project-level storage/uploads (matches Django MEDIA_ROOT)
_project_root = Path(__file__).resolve().parent.parent.parent
ALLOWED_IMAGE_ROOT = Path(
    os.environ.get(
        "ALLOWED_IMAGE_ROOT",
        str(_project_root / "storage" / "uploads"),
    )
)
