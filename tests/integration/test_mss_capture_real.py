"""Real screen capture. Run with: pytest tests/integration -m display"""

import pytest
from PIL.Image import Image as PILImage

from sniplingo.adapters.mss_capturer import MssCapturer
from sniplingo.domain.models import Region

pytestmark = pytest.mark.display


def test_capture_returns_rgb_image_of_expected_size():
    capturer = MssCapturer()
    try:
        image = capturer.capture(Region(0, 0, 10, 8))
    finally:
        capturer.close()
    assert isinstance(image, PILImage)
    assert image.size == (10, 8)
    assert image.mode == "RGB"
