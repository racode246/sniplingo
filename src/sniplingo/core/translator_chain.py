"""Try translation backends in order, retrying transient failures with backoff.

A backend signals a recoverable failure by raising
:class:`sniplingo.domain.errors.TranslationError`: the chain retries that backend
``retries`` more times (sleeping ``backoff_seconds`` between tries) and then moves on.
A :class:`~sniplingo.domain.errors.PermanentTranslationError` (bad key, quota, bad
request) skips the retries — waiting won't fix it.

Every backend tried is recorded in :attr:`TranslationResult.attempts`. If all fail, a
FAILED result whose error names *every* backend is returned (never raised). Unexpected
(non-``TranslationError``) exceptions propagate — they are bugs.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import replace

from sniplingo.domain.errors import PermanentTranslationError, TranslationError
from sniplingo.domain.models import BackendAttempt, TranslationResult
from sniplingo.ports.translate import Translator

logger = logging.getLogger(__name__)


class TranslatorChain:
    def __init__(
        self,
        backends: Sequence[Translator],
        *,
        retries: int = 1,
        backoff_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not backends:
            raise ValueError("TranslatorChain needs at least one backend")
        self._backends = list(backends)
        self._retries = retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep

    @property
    def backend_names(self) -> list[str]:
        return [backend.name for backend in self._backends]

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        attempts: list[BackendAttempt] = []
        for backend in self._backends:
            try:
                result = self._try_backend(backend, text, source, target)
            except TranslationError as exc:
                attempts.append(BackendAttempt(backend.name, str(exc)))
                continue
            return replace(result, attempts=(*attempts, BackendAttempt(backend.name)))

        error = "; ".join(f"{a.backend}: {a.error}" for a in attempts)
        return TranslationResult.failed(text, source, target, error=error, attempts=tuple(attempts))

    def _try_backend(
        self, backend: Translator, text: str, source: str, target: str
    ) -> TranslationResult:
        """Call one backend with retries; raise its last TranslationError if it gives up."""
        tries = self._retries + 1
        for attempt in range(1, tries + 1):
            try:
                return backend.translate(text, source, target)
            except PermanentTranslationError as exc:
                logger.warning("backend %s failed permanently: %s", backend.name, exc)
                raise
            except TranslationError as exc:
                logger.warning(
                    "backend %s failed (try %d/%d): %s", backend.name, attempt, tries, exc
                )
                if attempt == tries:
                    raise
                self._sleep(self._backoff_seconds)
        raise AssertionError("unreachable")  # pragma: no cover
