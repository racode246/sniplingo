"""Default translator: Google's free endpoint via `deep-translator` (no API key).

The underlying client is built by an injectable factory so unit tests can drive it
without network. Library/network failures are converted to
:class:`sniplingo.domain.errors.TranslationError` so the chain can fall back.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from deep_translator.exceptions import (
    BaseError,
    RequestError,
    ServerException,
    TooManyRequests,
)
from requests.exceptions import RequestException

from sniplingo.domain.errors import TranslationError
from sniplingo.domain.models import BackendName, TranslationResult

# deep-translator raises a mix of BaseError subclasses and bare Exceptions; cover both,
# plus requests-level connection failures.
_RECOVERABLE = (BaseError, RequestError, ServerException, TooManyRequests, RequestException)


class _TranslatorClient(Protocol):
    def translate(self, text: str) -> str: ...


TranslatorFactory = Callable[[str, str], _TranslatorClient]


class GoogleFreeTranslator:
    name = BackendName.GOOGLE_FREE.value

    def __init__(self, translator_factory: TranslatorFactory | None = None) -> None:
        self._factory = translator_factory or _default_factory

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        try:
            client = self._factory(source, target)
            translated = client.translate(text)
        except _RECOVERABLE as exc:
            raise TranslationError(f"google free translate failed: {exc}") from exc
        if not translated:
            raise TranslationError("google free translate returned no text")
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )


def _default_factory(source: str, target: str) -> _TranslatorClient:
    from deep_translator import GoogleTranslator

    return GoogleTranslator(source=source, target=target)
