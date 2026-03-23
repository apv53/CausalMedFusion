"""
Image Processing Pipeline
=========================
Transforms raw X-ray bytes into an ML-ready (1, 224, 224) tensor.
"""

import io
import numpy as np
from PIL import Image

try:
    import torchxrayvision as xrv
    HAS_XRV = True
except ImportError:
    HAS_XRV = False


VIEW_POSITION_MAP = {
    "LL": 0,
    "AP LLD": 1,
    "PA": 2,
    "LATERAL": 3,
    "AP": 4,
    "AP RLD": 5,
    "NIL": 6,
}


def encode_view_position(view_position: str) -> int:
    key = view_position.strip().upper()

    if key not in VIEW_POSITION_MAP:
        raise ValueError(
            f"Unknown view_position '{view_position}'. "
            f"Expected one of {list(VIEW_POSITION_MAP.keys())}"
        )

    return VIEW_POSITION_MAP[key]


TARGET_SIZE = (224, 224)


def process_image(raw_bytes: bytes) -> np.ndarray:
    """
    Full preprocessing pipeline.
    """

    img = Image.open(io.BytesIO(raw_bytes)).convert("L")
    img_array = np.array(img, dtype=np.float32)

    if HAS_XRV:
        img_array = xrv.datasets.normalize(img_array, maxval=255)
    else:
        img_array = img_array / 255.0

    img_pil = Image.fromarray(img_array, mode="F")
    img_resized = img_pil.resize(TARGET_SIZE, resample=Image.BILINEAR)

    tensor = np.array(img_resized, dtype=np.float32)
    tensor = np.expand_dims(tensor, axis=0)

    return tensor
