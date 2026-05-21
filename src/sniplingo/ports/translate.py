"""Port: translate text between languages."""

from __future__ import annotations

from typing import Protocol

from sniplingo.domain.models import TranslationResult


class Translator(Protocol):
    name: str

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        """Translate `text` from `source` to `target`.

        On failure, raise :class:`sniplingo.domain.errors.TranslationError` so the
        translator chain can fall back to the next backend.
        """
        ...
