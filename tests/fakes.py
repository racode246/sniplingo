"""Hand-written fakes implementing the `ports` Protocols.

Used by `core` unit tests so they stay free of real Windows / network / Qt deps
(see `.claude/rules/tdd.md`). Prefer these over MagicMock — they document the contract.
"""

from __future__ import annotations

from sniplingo.domain.models import OcrResult, Region, TranslationResult


class FakeCapturer:
    """Records the regions it was asked to capture and returns a fixed image object."""

    def __init__(self, image: object | None = None) -> None:
        self.image = image if image is not None else object()
        self.captured: list[Region] = []

    def capture(self, region: Region) -> object:
        self.captured.append(region)
        return self.image


class FakeOcr:
    """Returns a canned OcrResult and records the images/langs it was given."""

    def __init__(self, result: OcrResult, available: tuple[str, ...] = ("en", "ja")) -> None:
        self.result = result
        self.available = set(available)
        self.images: list[object] = []
        self.langs: list[str] = []

    def is_language_available(self, lang: str) -> bool:
        return lang in self.available

    def recognize(self, image: object, lang: str) -> OcrResult:
        self.images.append(image)
        self.langs.append(lang)
        return self.result


class FakeTranslator:
    """A Translator that maps known inputs, or raises a preset error to drive fallback."""

    def __init__(
        self,
        name: str = "fake",
        mapping: dict[str, str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.name = name
        self.mapping = mapping or {}
        self.error = error
        self.calls: list[tuple[str, str, str]] = []

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        self.calls.append((text, source, target))
        if self.error is not None:
            raise self.error
        translated = self.mapping.get(text, f"<{text}>")
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )
