"""Run every image in the OCR corpus (tests/data/ocr) through the real text path and
compare with its .txt answer. Run with: pytest tests/integration -m windows_ocr

The image goes through exactly what the app does before translating — preprocess,
Windows OCR, line cleaning, newline join — via TranslationPipeline with a capturer
that returns the file and a translator that records what it was asked to translate.
"""

from __future__ import annotations

import pytest
from PIL import Image
from tests.fakes import FakeCapturer, FakeTranslator
from tests.ocr_corpus import (
    OCR_CORPUS_SCORES,
    OcrCase,
    diff,
    discover_cases,
    normalize,
    similarity,
)

from sniplingo.adapters.winrt_ocr import WinRtOcrEngine
from sniplingo.core.config import AppConfig
from sniplingo.core.pipeline import TranslationPipeline
from sniplingo.domain.models import Region, ResultStatus

pytestmark = pytest.mark.windows_ocr


@pytest.fixture(scope="module")
def ocr_engine() -> WinRtOcrEngine:
    engine = WinRtOcrEngine(scale=AppConfig().ocr_scale)
    if not engine.is_language_available("en"):
        pytest.skip("English OCR language pack not installed")
    return engine


def _text_sent_to_translator(image: Image.Image, engine: WinRtOcrEngine) -> str:
    translator = FakeTranslator(name="recorder")
    pipeline = TranslationPipeline(FakeCapturer(image), engine, translator, capture_padding=0)
    result = pipeline.run(Region(0, 0, image.width, image.height))
    if result.status is ResultStatus.NO_TEXT:
        return ""
    assert result.status is ResultStatus.OK, result.error
    ((text, _source, _target),) = translator.calls
    return text


@pytest.mark.parametrize("case", discover_cases(), ids=lambda c: c.name)
def test_ocr_matches_ground_truth(case: OcrCase, ocr_engine, request):
    with Image.open(case.image) as img:
        image = img.convert("RGB")

    actual = normalize(_text_sent_to_translator(image, ocr_engine))
    expected = normalize(case.expected_text())
    score = similarity(actual, expected)
    request.config.stash[OCR_CORPUS_SCORES].append((case.name, score))

    threshold = request.config.getoption("--ocr-min-similarity")
    assert score >= threshold, (
        f"{case.name}: similarity {score:.3f} < {threshold:.2f}\n{diff(actual, expected)}"
    )
