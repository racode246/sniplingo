"""Real Windows OCR. Run with: pytest tests/integration -m windows_ocr"""

import pytest
from PIL import Image, ImageDraw, ImageFont

from sniplingo.adapters.winrt_ocr import WinRtOcrEngine
from sniplingo.domain.errors import OcrLanguageUnavailableError
from sniplingo.domain.text_postprocess import clean_ocr_text

pytestmark = pytest.mark.windows_ocr


def _render(lines: list[str]) -> Image.Image:
    img = Image.new("RGB", (560, 70 * len(lines) + 40), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 52)
    except OSError:
        font = ImageFont.load_default()
    for i, line in enumerate(lines):
        draw.text((12, 20 + i * 66), line, fill="black", font=font)
    return img


def test_recognizes_english_text():
    engine = WinRtOcrEngine()
    if not engine.is_language_available("en"):
        pytest.skip("English OCR language pack not installed")
    result = engine.recognize(_render(["Save your", "progress?"]), "en")
    assert "progress" in clean_ocr_text(result).lower()


def test_unavailable_language_raises():
    engine = WinRtOcrEngine()
    with pytest.raises(OcrLanguageUnavailableError):
        engine.recognize(_render(["hello"]), "zz")
