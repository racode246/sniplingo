import pytest

from sniplingo.domain.models import OcrLine, OcrResult
from sniplingo.domain.text_postprocess import clean_ocr_text, join_lines


@pytest.mark.parametrize(
    "lines,expected",
    [
        (["Hello", "World"], "Hello World"),  # basic join with single space
        (["Press X to continue"], "Press X to continue"),  # single line untouched
        (["Hello    there"], "Hello there"),  # collapse internal runs of spaces
        (["Hello", "  ", "", "World"], "Hello World"),  # drop blank/whitespace lines
        (["  Hello  "], "Hello"),  # trim outer whitespace
        ([], ""),  # empty input
        (["   ", ""], ""),  # all-blank input
        (["beauti-", "ful day"], "beautiful day"),  # de-hyphenate across line break
        (["foo -", "bar"], "foo - bar"),  # standalone dash is NOT de-hyphenated
        (["word-"], "word-"),  # trailing hyphen with no continuation is kept
    ],
)
def test_join_lines(lines, expected):
    assert join_lines(lines) == expected


def test_clean_ocr_text_uses_line_texts():
    result = OcrResult(lines=(OcrLine("Save your"), OcrLine("progress?")))
    assert clean_ocr_text(result) == "Save your progress?"


def test_clean_ocr_text_empty_result():
    assert clean_ocr_text(OcrResult(lines=())) == ""
