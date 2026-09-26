"""The OCR ground-truth corpus: discovery, pairing and text comparison (no OCR here).

The real-OCR run over the corpus lives in tests/integration/test_ocr_corpus_real.py.
"""

import pytest
from tests.ocr_corpus import CORPUS_DIR, discover_cases, find_orphans, normalize, similarity


def _touch(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8") if path.suffix == ".txt" else path.write_bytes(b"x")


def test_discovers_image_text_pairs_recursively_sorted(tmp_path):
    _touch(tmp_path / "b_menu.png")
    _touch(tmp_path / "b_menu.txt", "Menu")
    _touch(tmp_path / "a_dialog.JPG")
    _touch(tmp_path / "a_dialog.txt", "Hello")
    _touch(tmp_path / "local" / "tooltip.jpeg")
    _touch(tmp_path / "local" / "tooltip.txt", "Gloves")

    cases = discover_cases(tmp_path)

    assert [c.name for c in cases] == ["a_dialog", "b_menu", "local/tooltip"]
    assert cases[0].image == tmp_path / "a_dialog.JPG"
    assert cases[0].expected_text() == "Hello"


def test_unpaired_files_are_reported_as_orphans_not_cases(tmp_path):
    _touch(tmp_path / "no_answer.png")
    _touch(tmp_path / "no_image.txt", "x")
    _touch(tmp_path / "README.md", "docs are ignored")
    _touch(tmp_path / "notes.json", "{}")

    assert discover_cases(tmp_path) == []
    assert sorted(p.name for p in find_orphans(tmp_path)) == ["no_answer.png", "no_image.txt"]


def test_missing_corpus_dir_yields_no_cases(tmp_path):
    assert discover_cases(tmp_path / "absent") == []
    assert find_orphans(tmp_path / "absent") == []


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Hello\r\nWorld\r\n", "hello\nworld"),
        ("  Hello   there  \n\n\n  World ", "hello there\nworld"),
        ("QUALITY: +20%", "quality: +20%"),  # small-caps game fonts: case is ignored
        (chr(0xFEFF) + "BOM first", "bom first"),
        ("A" + chr(0x3000) * 2 + "B", "a b"),  # full-width spaces
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_similarity_bounds():
    assert similarity("abc", "abc") == 1.0
    assert similarity("abc", "xyz") == 0.0
    assert 0.0 < similarity("hello world", "hello word") < 1.0


# --- the checked-in corpus itself --------------------------------------------------


def test_real_corpus_has_no_orphans():
    orphans = find_orphans(CORPUS_DIR)
    assert not orphans, f"each image needs a same-named .txt and vice versa: {orphans}"


@pytest.mark.parametrize("case", discover_cases(CORPUS_DIR), ids=lambda c: c.name)
def test_real_corpus_answers_are_non_empty_utf8(case):
    assert normalize(case.expected_text()), f"{case.expected} is empty"
