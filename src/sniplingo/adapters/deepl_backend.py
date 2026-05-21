"""Optional DeepL translator (`deep-translator`'s DeeplTranslator).

Disabled unless the user supplies an API key in config (see `.claude/rules/secrets.md`).
The key is never logged; failures are converted to TranslationError.
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

_RECOVERABLE = (BaseError, RequestError, ServerException, TooManyRequests, RequestException)


class _DeeplClient(Protocol):
    def translate(self, text: str) -> str: ...


DeeplFactory = Callable[[str, str, str], _DeeplClient]


class DeepLTranslator:
    name = BackendName.DEEPL.value

    def __init__(self, api_key: str, deepl_factory: DeeplFactory | None = None) -> None:
        if not api_key:
            raise ValueError("DeepL backend requires a non-empty API key")
        self._api_key = api_key
        self._factory = deepl_factory or _default_factory

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        try:
            client = self._factory(self._api_key, source, target)
            translated = client.translate(text)
        except _RECOVERABLE as exc:
            # Never include the key/exc detail that might echo it; keep the message generic.
            raise TranslationError("DeepL translate failed") from exc
        if not translated:
            raise TranslationError("DeepL translate returned no text")
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )


def _default_factory(api_key: str, source: str, target: str) -> _DeeplClient:
    from deep_translator import DeeplTranslator

    return DeeplTranslator(api_key=api_key, source=source, target=target, use_free_api=True)
