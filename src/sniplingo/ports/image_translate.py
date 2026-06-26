"""Port: translate the text inside an image directly (LLM Vision path).

LLMs like Gemini can do OCR and translation in one round-trip, skipping the
Windows OCR pre-process and any line/decoration cleanup that goes with it.
Backends that don't accept images simply don't implement this port; the
pipeline falls back to the text-based :class:`Translator` path then.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from sniplingo.domain.models import TranslationResult

if TYPE_CHECKING:
    from PIL.Image import Image


class ImageTranslator(Protocol):
    name: str

    def translate_image(self, image: Image, source: str, target: str) -> TranslationResult:
        """Read `image` and return its content translated from `source` to `target`.

        On failure, raise :class:`sniplingo.domain.errors.TranslationError` so the
        caller can fall back (typically to the OCR-based text translation path).
        """
        ...
