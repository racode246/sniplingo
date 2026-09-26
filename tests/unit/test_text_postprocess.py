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


# --- soft-wrapped paragraphs are rejoined so a sentence reaches the translator whole ---


@pytest.mark.parametrize(
    "lines,expected",
    [
        # 行末が文の途中 + 次行が小文字始まり = 画面幅での折り返し -> 結合
        (
            ["Restoring save slots may also be", "corrupted. For this reason, enable backups."],
            ["Restoring save slots may also be corrupted. For this reason, enable backups."],
        ),
        # 3 行以上にまたがる段落も 1 行に
        (
            ["Once the slot is loaded,", "character information will be", "properly updated."],
            ["Once the slot is loaded, character information will be properly updated."],
        ),
        # 小文字の接続語で終わる行は、次行が大文字でも続きとみなす
        (
            ["Enable automatic save backups in the", "Launcher settings."],
            ["Enable automatic save backups in the Launcher settings."],
        ),
        # 段落の境目 (文末 + 大文字始まり) では結合しない
        (
            ["in the Launcher settings.", "IMPORTANT: After restoring a backup slot"],
            ["in the Launcher settings.", "IMPORTANT: After restoring a backup slot"],
        ),
        # 文末句読点の後は小文字始まりでも結合しない
        (["Saved.", "then quit"], ["Saved.", "then quit"]),
        # ツールチップ: 各行が独立した項目 (大文字/数字/+ 始まり) -> 結合しない
        (
            ["+126 to maximum Life", "+2 to Level of all Projectile Skills", "Corrupted"],
            ["+126 to maximum Life", "+2 to Level of all Projectile Skills", "Corrupted"],
        ),
        (
            ["Evasion Rating: 126", "Requires Level 60, 56 Dex", "8% increased Attack Speed"],
            ["Evasion Rating: 126", "Requires Level 60, 56 Dex", "8% increased Attack Speed"],
        ),
        # スモールキャップスの全大文字 OCR は接続語でも結合しない
        (["ADDS 2 TO", "ATTACKS"], ["ADDS 2 TO", "ATTACKS"]),
        # ハイフン折り返しと段落結合の併用
        (
            ["a beauti-", "ful day and a", "quiet night"],
            ["a beautiful day and a quiet night"],
        ),
    ],
)
def test_clean_ocr_lines_rejoins_soft_wrapped_paragraphs(lines, expected):
    result = OcrResult(lines=tuple(OcrLine(text=line) for line in lines))
    assert clean_ocr_lines(result) == expected
