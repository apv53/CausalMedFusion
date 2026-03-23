"""
Tests for image_service.processing module
==========================================
Covers view-position encoding and the image processing pipeline.
"""

import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from image_service.processing import (
    TARGET_SIZE,
    VIEW_POSITION_MAP,
    encode_view_position,
    process_image,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _make_test_image(width: int = 512, height: int = 512) -> bytes:
    """Create a synthetic grayscale PNG in memory."""
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, size=(height, width), dtype=np.uint8)
    img = Image.fromarray(arr, mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── View-Position Encoding ──────────────────────────────────────────

class TestViewPositionEncoding:
    @pytest.mark.parametrize("vp,expected", list(VIEW_POSITION_MAP.items()))
    def test_all_known_positions(self, vp: str, expected: int):
        assert encode_view_position(vp) == expected

    def test_case_insensitive(self):
        assert encode_view_position("ap") == VIEW_POSITION_MAP["AP"]
        assert encode_view_position("Pa") == VIEW_POSITION_MAP["PA"]

    def test_strips_whitespace(self):
        assert encode_view_position("  AP  ") == VIEW_POSITION_MAP["AP"]

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown view_position"):
            encode_view_position("UNKNOWN_VIEW")


# ── Image Processing Pipeline ───────────────────────────────────────

class TestProcessImage:
    def test_output_shape(self):
        raw = _make_test_image()
        tensor = process_image(raw)
        assert tensor.shape == (1, TARGET_SIZE[0], TARGET_SIZE[1])

    def test_output_dtype(self):
        raw = _make_test_image()
        tensor = process_image(raw)
        assert tensor.dtype == np.float32

    def test_different_input_sizes(self):
        """Pipeline should handle non-square images."""
        for w, h in [(640, 480), (100, 300), (1024, 1024)]:
            raw = _make_test_image(width=w, height=h)
            tensor = process_image(raw)
            assert tensor.shape == (1, 224, 224)

    def test_rgb_input_handled(self):
        """RGB images should be converted to grayscale automatically."""
        rng = np.random.default_rng(7)
        arr = rng.integers(0, 256, size=(256, 256, 3), dtype=np.uint8)
        img = Image.fromarray(arr, mode="RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        tensor = process_image(buf.getvalue())
        assert tensor.shape == (1, 224, 224)
