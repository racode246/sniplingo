"""Port: recognize text in an image."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from sniplingo.domain.models import OcrResult

if TYPE_CHECKING:
    from PIL.Image import Image


class OcrEngine(Protocol):
    def is_language_available(self, lang: str) -> bool:
        """Whether the OCR engine can recognize `lang` (e.g. an installed pack)."""
        ...

    def recognize(self, image: Image, lang: str) -> OcrResult:
        """Recognize text of language `lang` in `image`."""
        ...
