import pytest

from sniplingo.domain.models import OcrLine, OcrResult
from sniplingo.domain.text_postprocess import clean_ocr_lines, clean_ocr_text, join_lines


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


@pytest.mark.parametrize(
    "lines,expected",
    [
        # 各行が独立して保持される (一覧画面の各項目を 1 行ずつ翻訳できるように)
        (
            ["GLOVES", "QUALITY: +20%", "EVASION RATING: 126"],
            ["GLOVES", "QUALITY: +20%", "EVASION RATING: 126"],
        ),
        # 単一行はそのまま 1 要素
        (["Press X to continue"], ["Press X to continue"]),
        # 空行・空白のみ行は除去
        (["Hello", "  ", "", "World"], ["Hello", "World"]),
        # 行内の連続空白は単一空白に
        (["Hello    there"], ["Hello there"]),
        # 末尾ハイフン継続は前行とマージ (改行を跨いだ単語の折り返し)
        (["beauti-", "ful day"], ["beautiful day"]),
        # 末尾ハイフンに続く行が無い場合はそのまま残る
        (["word-"], ["word-"]),
        # 先頭・末尾の下線/装飾記号 (_ = ~ |) はトリム
        (["_GLOVES_"], ["GLOVES"]),
        (["===Corrupted==="], ["Corrupted"]),
        (["~Quality: +20%~"], ["Quality: +20%"]),
        # マイナス符号 ('-2 to xxx') は意味を持つので保護する
        (["-2 to Level of Skills"], ["-2 to Level of Skills"]),
        # 英数字を含まない装飾のみの行 (罫線など) はまるごと除去
        (["___", "Hello", "==="], ["Hello"]),
        (["----"], []),
        # 完全に空の入力
        ([], []),
        # 全て空白
        (["   ", ""], []),
    ],
)
def test_clean_ocr_lines(lines, expected):
    result = OcrResult(lines=tuple(OcrLine(text=line) for line in lines))
    assert clean_ocr_lines(result) == expected
