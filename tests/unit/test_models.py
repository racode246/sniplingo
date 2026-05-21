import dataclasses

import pytest

from sniplingo.domain.models import (
    BackendName,
    OcrLine,
    OcrResult,
    Region,
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
    assert BackendName.GOOGLE_FREE.value == "google_free"
    assert BackendName.ARGOS.value == "argos"
    assert BackendName.DEEPL.value == "deepl"


def test_translation_result_ok_by_default():
    tr = TranslationResult(
        source_text="hi",
        translated_text="やあ",
        source_lang="en",
        target_lang="ja",
        backend="google_free",
    )
    assert tr.error is None
    assert tr.ok is True


def test_translation_result_failure_is_not_ok():
    tr = TranslationResult(
        source_text="hi",
        translated_text="",
        source_lang="en",
        target_lang="ja",
        backend="",
        error="all backends failed",
    )
    assert tr.ok is False
