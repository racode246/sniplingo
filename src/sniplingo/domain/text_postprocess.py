"""Clean OCR output into translatable strings.

Game OCR tends to split a sentence across several lines, sometimes hyphenating
words at the wrap point. We also see decoration noise around lines that the
recognizer picked up from underlines / dividers (``_``, ``=``, ``~``, ``|``).

Two views are exposed:
- :func:`clean_ocr_lines` keeps the line structure (one element per logical row)
  so the pipeline can translate each independently and preserve newlines.
- :func:`clean_ocr_text` / :func:`join_lines` collapse everything into one string
  (kept for callers that want a single blob).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from sniplingo.domain.models import OcrResult

_WHITESPACE_RUN = re.compile(r"\s+")
# A word character immediately followed by a trailing hyphen = a wrapped word.
_WRAP_HYPHEN = re.compile(r"\w-$")
# Edge decoration characters to strip. '-' is intentionally excluded so leading
# minus signs ("-2 to ...") and trailing wrap hyphens survive for later handling.
_EDGE_NOISE = " \t_=~|"
_HAS_ALNUM = re.compile(r"[A-Za-z0-9]")


def clean_ocr_lines(result: OcrResult) -> list[str]:
    """Return cleaned, translatable lines from an OCR result.

    Drops blank / decoration-only rows, strips edge noise (``_``, ``=``, ``~``,
    ``|``) and merges words wrapped across a line break (``"beauti-"`` +
    ``"ful day"`` -> ``"beautiful day"``). The remaining lines stay separate so
    each can be translated on its own.
    """
    normalized: list[str] = []
    for raw in result.line_texts:
        line = raw.strip().strip(_EDGE_NOISE).strip()
        if not line or not _HAS_ALNUM.search(line):
            continue
        normalized.append(line)

    merged: list[str] = []
    for line in normalized:
        if merged and _WRAP_HYPHEN.search(merged[-1]):
            merged[-1] = merged[-1][:-1] + line
        else:
            merged.append(line)
    return [_WHITESPACE_RUN.sub(" ", line).strip() for line in merged]


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
