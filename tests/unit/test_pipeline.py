from tests.fakes import FakeCapturer, FakeOcr, FakeTranslator

from sniplingo.core.pipeline import TranslationPipeline
from sniplingo.domain.models import OcrLine, OcrResult, Region


def test_happy_path_capture_ocr_postprocess_translate():
    image = object()
    capturer = FakeCapturer(image)
    ocr = FakeOcr(OcrResult(lines=(OcrLine("Save your"), OcrLine("progress?"))))
    translator = FakeTranslator(name="fake", mapping={"Save your progress?": "進行状況を保存？"})
    pipeline = TranslationPipeline(capturer, ocr, translator, source="en", target="ja")

    region = Region(0, 0, 100, 50)
    result = pipeline.run(region)

    # capture got the region; OCR got the captured image + source language
    assert capturer.captured == [region]
    assert ocr.images == [image]
    assert ocr.langs == ["en"]
    # OCR lines were post-processed into one string before translation
    assert translator.calls == [("Save your progress?", "en", "ja")]
    assert result.source_text == "Save your progress?"
    assert result.translated_text == "進行状況を保存？"
    assert result.backend == "fake"
    assert result.ok


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
