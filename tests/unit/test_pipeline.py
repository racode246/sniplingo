from tests.fakes import FakeCapturer, FakeImageTranslator, FakeOcr, FakeTranslator

from sniplingo.core.pipeline import TranslationPipeline
from sniplingo.domain.errors import TranslationError
from sniplingo.domain.models import OcrLine, OcrResult, Region


def test_happy_path_capture_ocr_translate_single_line():
    image = object()
    capturer = FakeCapturer(image)
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Save your progress?"),)))
    translator = FakeTranslator(name="fake", mapping={"Save your progress?": "進行状況を保存？"})
    pipeline = TranslationPipeline(capturer, ocr, translator, source="en", target="ja")

    region = Region(0, 0, 100, 50)
    result = pipeline.run(region)

    # capture got the region; OCR got the captured image + source language
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
            from sniplingo.domain.models import TranslationResult

            return TranslationResult(
                source_text=text,
                translated_text="",
                source_lang=source,
                target_lang=target,
                backend="",
                error="all translation backends failed",
            )

    translator = ErrorTranslator()
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Hello"), OcrLine("World"))))
    pipeline = TranslationPipeline(FakeCapturer(), ocr, translator)

    result = pipeline.run(Region(0, 0, 10, 10))

    # Still only one call — failure is reported by the chain, not by retrying rows.
    assert len(translator.calls) == 1
    assert result.ok is False
    assert result.error == "all translation backends failed"


def test_empty_ocr_short_circuits_without_translating():
    capturer = FakeCapturer()
    ocr = FakeOcr(OcrResult(lines=()))  # nothing recognized
    translator = FakeTranslator()
    pipeline = TranslationPipeline(capturer, ocr, translator)

    result = pipeline.run(Region(0, 0, 10, 10))

    assert translator.calls == []  # translator must not be invoked
    assert result.source_text == ""
    assert result.translated_text == ""
    assert result.ok is False  # nothing to show


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
    pipeline = TranslationPipeline(capturer, ocr, text, image_translator=vision)

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
    pipeline = TranslationPipeline(capturer, ocr, text, image_translator=vision)

    result = pipeline.run(Region(0, 0, 10, 10))

    assert vision.calls  # was attempted
    assert ocr.images == [image]  # fell back to OCR
    assert text.calls == [("Hello", "en", "ja")]
    assert result.translated_text == "こんにちは"
    assert result.backend == "google"
    assert result.ok
