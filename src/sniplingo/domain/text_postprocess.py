"""Clean OCR output into a single translatable string.

Game OCR tends to split a sentence across several lines, sometimes hyphenating
words at the wrap point. We join lines into one string, de-hyphenate genuine
word breaks, drop blank lines, and collapse runs of whitespace.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from sniplingo.domain.models import OcrResult

_WHITESPACE_RUN = re.compile(r"\s+")
# A word character immediately followed by a trailing hyphen = a wrapped word.
_WRAP_HYPHEN = re.compile(r"\w-$")


def join_lines(lines: Iterable[str]) -> str:
    """Join OCR lines into one normalized string."""
    cleaned = [stripped for line in lines if (stripped := line.strip())]
    if not cleaned:
        return ""

    out = cleaned[0]
    for line in cleaned[1:]:
        if _WRAP_HYPHEN.search(out):
            out = out[:-1] + line  # merge the wrapped word, dropping the hyphen
        else:
            out = f"{out} {line}"
    return _WHITESPACE_RUN.sub(" ", out).strip()


def clean_ocr_text(result: OcrResult) -> str:
    """Convenience wrapper: normalize all line texts of an `OcrResult`."""
    return join_lines(result.line_texts)
