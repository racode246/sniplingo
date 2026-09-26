"""Hand-written fakes implementing the `ports` Protocols.

Used by `core` unit tests so they stay free of real Windows / network / Qt deps
(see `.claude/rules/tdd.md`). Prefer these over MagicMock — they document the contract.
"""

from __future__ import annotations

from sniplingo.domain.models import OcrResult, Region, TranslationResult


class FakeCapturer:
    """Records the regions it was asked to capture and returns a fixed image object."""

    def __init__(self, image: object | None = None, error: Exception | None = None) -> None:
        self.image = image if image is not None else object()
        self.error = error
        self.captured: list[Region] = []

    def capture(self, region: Region) -> object:
        self.captured.append(region)
        if self.error is not None:
            raise self.error
        return self.image


class FakeOcr:
    """Returns a canned OcrResult and records the images/langs it was given."""

    def __init__(
        self,
        result: OcrResult,
        available: tuple[str, ...] = ("en", "ja"),
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.available = set(available)
        self.error = error
        self.images: list[object] = []
        self.langs: list[str] = []

    def is_language_available(self, lang: str) -> bool:
        return lang in self.available

    def recognize(self, image: object, lang: str) -> OcrResult:
        self.images.append(image)
        self.langs.append(lang)
        if self.error is not None:
            raise self.error
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


class FakeImageTranslator:
    """An ImageTranslator that returns a canned translation per image identity."""

    def __init__(
        self,
        name: str = "fake-vision",
        translated_text: str = "(translated)",
        error: Exception | None = None,
    ) -> None:
        self.name = name
        self.translated_text = translated_text
        self.error = error
        self.calls: list[tuple[object, str, str]] = []

    def translate_image(self, image: object, source: str, target: str) -> TranslationResult:
        self.calls.append((image, source, target))
        if self.error is not None:
            raise self.error
        return TranslationResult(
            source_text="",
            translated_text=self.translated_text,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )


class FakeHttpResponse:
    """Stand-in for a `requests.Response`: only `status_code` and `json()` are used."""

    def __init__(self, status_code: int = 200, payload: object = None, invalid_json: bool = False):
        self.status_code = status_code
        self._payload = payload
        self._invalid_json = invalid_json

    def json(self) -> object:
        if self._invalid_json:
            raise ValueError("not json")
        return self._payload


class FakeHttpPost:
    """An `HttpPost` that records each call and returns a canned response (or raises)."""

    def __init__(
        self, response: FakeHttpResponse | None = None, error: Exception | None = None
    ) -> None:
        self.response = response or FakeHttpResponse()
        self.error = error
        self.calls: list[dict] = []

    def __call__(self, url: str, **kwargs) -> FakeHttpResponse:
        self.calls.append({"url": url, **kwargs})
        if self.error is not None:
            raise self.error
        return self.response

    @property
    def last(self) -> dict:
        return self.calls[-1]
