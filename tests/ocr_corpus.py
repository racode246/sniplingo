"""OCR ground-truth corpus: image + same-named ``.txt`` answer pairs under tests/data/ocr.

Drop ``<name>.png`` (or .jpg/.jpeg/.bmp) next to ``<name>.txt`` holding the text the
pipeline *should* send to the translator (a soft-wrapped paragraph is one line;
standalone rows such as tooltip stats stay one per line). Subfolders are
scanned too; ``local/`` is git-ignored for screenshots that can't be redistributed.
See tests/data/ocr/README.md.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

# (case name, similarity) pairs collected during a run, printed by tests/conftest.py.
OCR_CORPUS_SCORES = pytest.StashKey[list[tuple[str, float]]]()

CORPUS_DIR = Path(__file__).parent / "data" / "ocr"
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".bmp"})
ANSWER_SUFFIX = ".txt"

_BOM = chr(0xFEFF)
_FULL_WIDTH_SPACE = chr(0x3000)
_SPACES = re.compile(f"[ \t{_FULL_WIDTH_SPACE}]+")


@dataclass(frozen=True)
class OcrCase:
    name: str  # path relative to the corpus root, without suffix ("local/poe_gloves")
    image: Path
    expected: Path

    def expected_text(self) -> str:
        return self.expected.read_text(encoding="utf-8-sig")


def _files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file()) if root.is_dir() else []


def _images(root: Path) -> list[Path]:
    return [p for p in _files(root) if p.suffix.lower() in IMAGE_SUFFIXES]


def discover_cases(root: Path = CORPUS_DIR) -> list[OcrCase]:
    """Every image that has a same-named ``.txt`` answer, sorted by name."""
    cases = []
    for image in _images(root):
        answer = image.with_suffix(ANSWER_SUFFIX)
        if answer.is_file():
            name = image.relative_to(root).with_suffix("").as_posix()
            cases.append(OcrCase(name=name, image=image, expected=answer))
    return sorted(cases, key=lambda c: c.name)


def find_orphans(root: Path = CORPUS_DIR) -> list[Path]:
    """Images without an answer, and answers without an image."""
    images = _images(root)
    image_stems = {p.with_suffix("") for p in images}
    lonely_images = [p for p in images if not p.with_suffix(ANSWER_SUFFIX).is_file()]
    lonely_answers = [
        p
        for p in _files(root)
        if p.suffix == ANSWER_SUFFIX and p.with_suffix("") not in image_stems
    ]
    return lonely_images + lonely_answers


def normalize(text: str) -> str:
    """Compare what matters: per-line content, not case / spacing / blank lines / BOM."""
    lines = (_SPACES.sub(" ", line).strip() for line in text.lstrip(_BOM).splitlines())
    return "\n".join(line for line in lines if line).casefold()


def similarity(actual: str, expected: str) -> float:
    """Character-level similarity in [0, 1] (difflib ratio)."""
    return difflib.SequenceMatcher(None, actual, expected, autojunk=False).ratio()


def diff(actual: str, expected: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            expected.splitlines(), actual.splitlines(), "expected", "actual", lineterm=""
        )
    )
