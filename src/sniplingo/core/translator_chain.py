"""Try translation backends in order, retrying transient failures with backoff.

A backend signals a recoverable failure by raising
:class:`sniplingo.domain.errors.TranslationError`. Each backend is attempted
``retries + 1`` times (with a backoff sleep between attempts) before moving on to
the next. If every backend fails, a non-crashing error :class:`TranslationResult`
is returned. Unexpected (non-``TranslationError``) exceptions propagate — they are bugs.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from sniplingo.domain.errors import TranslationError
from sniplingo.domain.models import TranslationResult
from sniplingo.ports.translate import Translator


class TranslatorChain:
    def __init__(
        self,
        primary: Translator,
        fallbacks: Sequence[Translator] = (),
        *,
        retries: int = 1,
        backoff_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._backends: list[Translator] = [primary, *fallbacks]
        self._retries = retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        last_error: TranslationError | None = None
        for backend in self._backends:
            for attempt in range(self._retries + 1):
                try:
                    return backend.translate(text, source, target)
                except TranslationError as exc:
                    last_error = exc
                    if attempt < self._retries:
                        self._sleep(self._backoff_seconds)
        message = str(last_error) if last_error else "all translation backends failed"
        return TranslationResult(
            source_text=text,
            translated_text="",
            source_lang=source,
            target_lang=target,
            backend="",
            error=message,
        )
