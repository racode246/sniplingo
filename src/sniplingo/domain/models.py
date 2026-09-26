"""Pure value types shared across layers. No I/O, no third-party imports."""

from __future__ import annotations

from dataclasses import dataclass
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

    GOOGLE_CLOUD = "google_cloud"
    DEEPL = "deepl"
    GEMINI = "gemini"


class ResultStatus(StrEnum):
    """Outcome of one translation run, as the UI needs to branch on it."""

    OK = "ok"
    NO_TEXT = "no_text"  # nothing recognized in the region — not an error
    FAILED = "failed"


@dataclass(frozen=True)
class BackendAttempt:
    """One backend tried during a run; ``error`` is ``None`` when it succeeded."""

    backend: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class TranslationResult:
    """The outcome of translating one captured region.

    ``attempts`` records every backend that was tried, in order (including a failed
    Vision attempt before the text path), so failures and fallbacks are diagnosable.
    """

    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    backend: str | None
    status: ResultStatus = ResultStatus.OK
    error: str | None = None
    attempts: tuple[BackendAttempt, ...] = ()

    def __post_init__(self) -> None:
        if self.status is ResultStatus.FAILED and not self.error:
            raise ValueError("a FAILED TranslationResult needs an error message")

    @property
    def ok(self) -> bool:
        return self.status is ResultStatus.OK

    @classmethod
    def failed(
        cls,
        source_text: str,
        source_lang: str,
        target_lang: str,
        *,
        error: str,
        attempts: tuple[BackendAttempt, ...] = (),
    ) -> TranslationResult:
        return cls(
            source_text=source_text,
            translated_text="",
            source_lang=source_lang,
            target_lang=target_lang,
            backend=None,
            status=ResultStatus.FAILED,
            error=error,
            attempts=attempts,
        )

    @classmethod
    def no_text(
        cls,
        source_lang: str,
        target_lang: str,
        *,
        attempts: tuple[BackendAttempt, ...] = (),
    ) -> TranslationResult:
        return cls(
            source_text="",
            translated_text="",
            source_lang=source_lang,
            target_lang=target_lang,
            backend=None,
            status=ResultStatus.NO_TEXT,
            attempts=attempts,
        )
