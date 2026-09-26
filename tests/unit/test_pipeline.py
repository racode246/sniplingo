import logging

from tests.fakes import FakeCapturer, FakeImageTranslator, FakeOcr, FakeTranslator

from sniplingo.core.pipeline import TranslationPipeline
from sniplingo.domain.errors import (
    CaptureError,
    OcrError,
    OcrLanguageUnavailableError,
    TranslationError,
)
from sniplingo.domain.models import (
    BackendAttempt,
    OcrLine,
    OcrResult,
    Region,
    ResultStatus,
    TranslationResult,
)


def test_happy_path_capture_ocr_translate_single_line():
    image = object()
    capturer = FakeCapturer(image)
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Save your progress?"),)))
    translator = FakeTranslator(name="fake", mapping={"Save your progress?": "進行状況を保存？"})
    pipeline = TranslationPipeline(
        capturer, ocr, translator, source="en", target="ja", capture_padding=0
    )

    region = Region(0, 0, 100, 50)
    result = pipeline.run(region)

    # capture got the region (no padding here); OCR got the captured image + source language
    assert capturer.captured == [region]
    assert ocr.images == [image]
    assert ocr.langs == ["en"]
    assert translator.calls == [("Save your progress?", "en", "ja")]
    assert result.source_text == "Save your progress?"
    assert result.translated_text == "進行状況を保存？"
    assert result.backend == "fake"
    assert result.ok


def test_wrapped_word_across_lines_is_merged_before_translation():
    """A trailing hyphen joins the next OCR line into the same translatable row."""
    ocr = FakeOcr(OcrResult(lines=(OcrLine("beauti-"), OcrLine("ful day"))))
    translator = FakeTranslator(name="fake", mapping={"beautiful day": "美しい日"})
    pipeline = TranslationPipeline(FakeCapturer(), ocr, translator)

    result = pipeline.run(Region(0, 0, 10, 10))

    assert translator.calls == [("beautiful day", "en", "ja")]
    assert result.translated_text == "美しい日"


def test_multiple_lines_are_sent_as_one_call_joined_with_newline():
    """All cleaned rows go in ONE translate call (latency-critical)."""
    ocr = FakeOcr(
        OcrResult(
            lines=(
                OcrLine("QUALITY: +20%"),
                OcrLine("EVASION RATING: 126"),
                OcrLine("Corrupted"),
            )
        )
    )
    joined_source = "QUALITY: +20%\nEVASION RATING: 126\nCorrupted"
    joined_translation = "品質: +20%\n回避値: 126\n汚職"
    translator = FakeTranslator(name="fake", mapping={joined_source: joined_translation})
    pipeline = TranslationPipeline(FakeCapturer(), ocr, translator)

    result = pipeline.run(Region(0, 0, 100, 100))

    # Single round-trip with newline-joined payload.
    assert translator.calls == [(joined_source, "en", "ja")]
    assert result.source_text == joined_source
    assert result.translated_text == joined_translation
    assert result.backend == "fake"
    assert result.ok


def test_underline_decoration_is_stripped_before_translation():
    """Underlines/dividers read as edge punctuation must not reach the translator."""
    ocr = FakeOcr(
        OcrResult(
            lines=(
                OcrLine("_GLOVES_"),
                OcrLine("==="),  # decoration-only row -> dropped
                OcrLine("~Quality: +20%~"),
            )
        )
    )
    translator = FakeTranslator(name="fake")
    pipeline = TranslationPipeline(FakeCapturer(), ocr, translator)

    result = pipeline.run(Region(0, 0, 100, 100))

    assert translator.calls == [("GLOVES\nQuality: +20%", "en", "ja")]
    assert result.source_text == "GLOVES\nQuality: +20%"
    assert result.ok


def test_translator_error_is_surfaced_directly():
    """A failing chain returns its errored TranslationResult to the caller as-is."""

    class ErrorTranslator:
        name = "fake"

        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str]] = []

        def translate(self, text, source, target):
            self.calls.append((text, source, target))
            return TranslationResult.failed(
                text, source, target, error="all translation backends failed"
            )

    translator = ErrorTranslator()
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Hello"), OcrLine("World"))))
    pipeline = TranslationPipeline(FakeCapturer(), ocr, translator)

    result = pipeline.run(Region(0, 0, 10, 10))

    # Still only one call — failure is reported by the chain, not by retrying rows.
    assert len(translator.calls) == 1
    assert result.ok is False
    assert result.error == "all translation backends failed"


def test_capture_region_is_padded_so_edge_text_keeps_a_quiet_zone():
    # A selection dragged flush to the text would clip its edge glyphs; the pipeline
    # captures a padded rectangle so Windows OCR still sees a margin around the words.
    capturer = FakeCapturer()
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Hi"),)))
    pipeline = TranslationPipeline(capturer, ocr, FakeTranslator(), capture_padding=4)

    pipeline.run(Region(10, 10, 20, 20))

    assert capturer.captured == [Region(6, 6, 28, 28)]


def test_capture_padding_defaults_to_a_nonzero_margin():
    capturer = FakeCapturer()
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Hi"),)))
    pipeline = TranslationPipeline(capturer, ocr, FakeTranslator())

    pipeline.run(Region(100, 100, 50, 20))

    captured = capturer.captured[0]
    assert captured.left < 100 and captured.top < 100
    assert captured.width > 50 and captured.height > 20


def test_empty_ocr_short_circuits_without_translating():
    capturer = FakeCapturer()
    ocr = FakeOcr(OcrResult(lines=()))  # nothing recognized
    translator = FakeTranslator()
    pipeline = TranslationPipeline(capturer, ocr, translator)

    result = pipeline.run(Region(0, 0, 10, 10))

    assert translator.calls == []  # translator must not be invoked
    assert result.source_text == ""
    assert result.translated_text == ""
    assert result.status is ResultStatus.NO_TEXT  # nothing to show, but not an error
    assert result.error is None


def test_whitespace_only_ocr_also_short_circuits():
    ocr = FakeOcr(OcrResult(lines=(OcrLine("   "), OcrLine(""))))
    translator = FakeTranslator()
    pipeline = TranslationPipeline(FakeCapturer(), ocr, translator)

    result = pipeline.run(Region(0, 0, 10, 10))

    assert translator.calls == []
    assert result.translated_text == ""


# --- Vision (image_translator) path ------------------------------------------------


def test_image_translator_short_circuits_ocr_and_text_translator():
    """When an image_translator is configured, OCR and the text path are skipped."""
    image = object()
    capturer = FakeCapturer(image)
    ocr = FakeOcr(OcrResult(lines=()))  # not used
    text = FakeTranslator()  # not used
    vision = FakeImageTranslator(name="gemini", translated_text="やあ世界")
    pipeline = TranslationPipeline(capturer, ocr, text, image_translator=vision, capture_padding=0)

    region = Region(0, 0, 100, 100)
    result = pipeline.run(region)

    # Capture happened once; OCR and text translator were never touched.
    assert capturer.captured == [region]
    assert ocr.images == []
    assert text.calls == []
    # Vision backend got the captured image directly.
    assert vision.calls == [(image, "en", "ja")]
    assert result.translated_text == "やあ世界"
    assert result.backend == "gemini"
    assert result.ok


def test_image_translator_failure_falls_back_to_ocr_path():
    """If Vision raises, the pipeline still produces a result via OCR + text translator."""
    image = object()
    capturer = FakeCapturer(image)
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Hello"),)))
    text = FakeTranslator(name="google", mapping={"Hello": "こんにちは"})
    vision = FakeImageTranslator(error=TranslationError("vision down"))
    pipeline = TranslationPipeline(capturer, ocr, text, image_translator=vision, capture_padding=0)

    result = pipeline.run(Region(0, 0, 10, 10))

    assert vision.calls  # was attempted
    assert ocr.images == [image]  # fell back to OCR
    assert text.calls == [("Hello", "en", "ja")]
    assert result.translated_text == "こんにちは"
    assert result.backend == "google"
    assert result.ok
    # The swallowed Vision failure is still visible in the result.
    assert result.attempts[0] == BackendAttempt("fake-vision:vision", "vision down")


def test_vision_path_also_captures_a_padded_region():
    """Edge glyphs clipped by a flush selection hurt Vision too — pad before capture."""
    capturer = FakeCapturer()
    ocr = FakeOcr(OcrResult(lines=()))
    vision = FakeImageTranslator(name="gemini", translated_text="やあ")
    pipeline = TranslationPipeline(
        capturer, ocr, FakeTranslator(), image_translator=vision, capture_padding=4
    )

    pipeline.run(Region(10, 10, 20, 20))

    assert capturer.captured == [Region(6, 6, 28, 28)]


def test_successful_vision_attempt_is_recorded():
    vision = FakeImageTranslator(name="gemini", translated_text="やあ")
    pipeline = TranslationPipeline(
        FakeCapturer(), FakeOcr(OcrResult()), FakeTranslator(), image_translator=vision
    )

    result = pipeline.run(Region(0, 0, 10, 10))

    assert result.attempts == (BackendAttempt("gemini:vision"),)


def test_vision_failure_is_logged(caplog):
    vision = FakeImageTranslator(name="gemini", error=TranslationError("HTTP 429"))
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Hello"),)))
    pipeline = TranslationPipeline(FakeCapturer(), ocr, FakeTranslator(), image_translator=vision)

    with caplog.at_level(logging.WARNING, logger="sniplingo"):
        pipeline.run(Region(0, 0, 10, 10))

    assert any("HTTP 429" in r.getMessage() for r in caplog.records)


def test_vision_failure_then_no_text_keeps_the_vision_attempt():
    vision = FakeImageTranslator(name="gemini", error=TranslationError("HTTP 429"))
    pipeline = TranslationPipeline(
        FakeCapturer(), FakeOcr(OcrResult()), FakeTranslator(), image_translator=vision
    )

    result = pipeline.run(Region(0, 0, 10, 10))

    assert result.status is ResultStatus.NO_TEXT
    assert result.attempts == (BackendAttempt("gemini:vision", "HTTP 429"),)


# --- capture / OCR failures become FAILED results (not crashes) --------------------


def test_capture_error_becomes_failed_result():
    capturer = FakeCapturer(error=CaptureError("screen capture failed"))
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Hi"),)))
    translator = FakeTranslator()
    pipeline = TranslationPipeline(capturer, ocr, translator)

    result = pipeline.run(Region(0, 0, 10, 10))

    assert result.status is ResultStatus.FAILED
    assert "screen capture failed" in result.error
    assert ocr.images == [] and translator.calls == []


def test_ocr_error_becomes_failed_result():
    ocr = FakeOcr(OcrResult(), error=OcrError("OCR recognition failed"))
    translator = FakeTranslator()
    pipeline = TranslationPipeline(FakeCapturer(), ocr, translator)

    result = pipeline.run(Region(0, 0, 10, 10))

    assert result.status is ResultStatus.FAILED
    assert "OCR recognition failed" in result.error
    assert translator.calls == []


def test_missing_ocr_language_pack_message_reaches_the_result():
    ocr = FakeOcr(OcrResult(), error=OcrLanguageUnavailableError("install the en pack"))
    pipeline = TranslationPipeline(FakeCapturer(), ocr, FakeTranslator())

    result = pipeline.run(Region(0, 0, 10, 10))

    assert result.status is ResultStatus.FAILED
    assert "install the en pack" in result.error
