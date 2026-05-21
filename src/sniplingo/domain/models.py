"""Pure value types shared across layers. No I/O, no third-party imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True)
class Region:
    """A rectangle in virtual-desktop coordinates (left/top may be negative)."""

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0


@dataclass(frozen=True)
class OcrWord:
    """A single recognized word with its bounding box."""

    text: str
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0


@dataclass(frozen=True)
class OcrLine:
    """A recognized line of text (a sequence of words on one row)."""

    text: str
    words: tuple[OcrWord, ...] = ()


@dataclass(frozen=True)
class OcrResult:
    """The outcome of OCR over a captured image."""

    lines: tuple[OcrLine, ...] = ()

    @property
    def line_texts(self) -> list[str]:
        return [line.text for line in self.lines]

    @property
    def is_empty(self) -> bool:
        return all(not line.text.strip() for line in self.lines)


class BackendName(StrEnum):
    """Identifiers for the pluggable translation backends."""

    GOOGLE_FREE = "google_free"
    ARGOS = "argos"
    DEEPL = "deepl"


@dataclass(frozen=True)
class TranslationResult:
    """The outcome of translating one piece of OCR text."""

    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    backend: str
    error: str | None = None
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None
