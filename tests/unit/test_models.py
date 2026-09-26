import dataclasses

import pytest

from sniplingo.domain.errors import PermanentTranslationError, TranslationError
from sniplingo.domain.models import (
    BackendAttempt,
    BackendName,
    OcrLine,
    OcrResult,
    Region,
    ResultStatus,
    TranslationResult,
)


def test_region_right_bottom_area():
    r = Region(left=10, top=20, width=30, height=40)
    assert r.right == 40
    assert r.bottom == 60
    assert r.area == 1200
    assert not r.is_empty


def test_region_negative_origin_allowed():
    r = Region(left=-100, top=-50, width=10, height=10)
    assert r.right == -90
    assert r.bottom == -40
    assert not r.is_empty


@pytest.mark.parametrize("w,h", [(0, 10), (10, 0), (0, 0), (-1, 5)])
def test_region_is_empty(w, h):
    assert Region(0, 0, w, h).is_empty


def test_region_is_frozen():
    r = Region(0, 0, 1, 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.left = 5  # type: ignore[misc]


def test_ocr_result_line_texts():
    res = OcrResult(lines=(OcrLine("Hello"), OcrLine("World")))
    assert res.line_texts == ["Hello", "World"]
    assert not res.is_empty


def test_ocr_result_empty():
    assert OcrResult(lines=()).is_empty
    assert OcrResult(lines=()).line_texts == []


def test_backend_name_values():
    assert BackendName.GOOGLE_CLOUD.value == "google_cloud"
    assert BackendName.DEEPL.value == "deepl"
    assert BackendName.GEMINI.value == "gemini"


def test_removed_backends_are_gone():
    values = {b.value for b in BackendName}
    assert "argos" not in values
    assert "google_free" not in values  # unofficial endpoint, dropped


def test_translation_result_ok_by_default():
    tr = TranslationResult(
        source_text="hi",
        translated_text="やあ",
        source_lang="en",
        target_lang="ja",
        backend="google_cloud",
    )
    assert tr.error is None
    assert tr.ok is True


def test_translation_result_status_defaults_to_ok():
    tr = TranslationResult("hi", "やあ", "en", "ja", backend="google_cloud")
    assert tr.status is ResultStatus.OK
    assert tr.attempts == ()


def test_failed_factory_builds_a_failed_result():
    attempts = (BackendAttempt("google_cloud", "HTTP 429"), BackendAttempt("gemini", "HTTP 503"))
    tr = TranslationResult.failed("hi", "en", "ja", error="all failed", attempts=attempts)
    assert tr.status is ResultStatus.FAILED
    assert tr.ok is False
    assert tr.error == "all failed"
    assert tr.backend is None
    assert tr.translated_text == ""
    assert tr.source_text == "hi"
    assert tr.attempts == attempts


def test_no_text_factory_is_distinct_from_failure():
    tr = TranslationResult.no_text("en", "ja")
    assert tr.status is ResultStatus.NO_TEXT
    assert tr.ok is False
    assert tr.error is None
    assert tr.backend is None
    assert tr.source_text == "" and tr.translated_text == ""


def test_failed_status_requires_an_error_message():
    with pytest.raises(ValueError):
        TranslationResult("hi", "", "en", "ja", backend=None, status=ResultStatus.FAILED)


def test_translation_result_is_deeply_immutable():
    tr = TranslationResult("hi", "やあ", "en", "ja", backend="x")
    assert not hasattr(tr, "meta")  # the mutable dict escape hatch is gone
    assert isinstance(tr.attempts, tuple)


def test_backend_attempt_ok_when_no_error():
    assert BackendAttempt("google_cloud").ok is True
    assert BackendAttempt("google_cloud", "boom").ok is False


def test_permanent_translation_error_is_a_translation_error():
    # Callers that only know TranslationError still catch it; the chain can special-case it.
    assert issubclass(PermanentTranslationError, TranslationError)
