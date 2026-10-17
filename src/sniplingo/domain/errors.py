"""Domain-level exceptions. Adapters convert third-party failures into these so the
core (pipeline / translator_chain) never depends on concrete libraries."""

from __future__ import annotations


class SnipLingoError(Exception):
    """Base class for all sniplingo errors."""


class CaptureError(SnipLingoError):
    """Screen capture failed."""


class OcrError(SnipLingoError):
    """OCR failed."""


class OcrLanguageUnavailableError(OcrError):
    """The requested OCR language pack is not installed."""


class TranslationError(SnipLingoError):
    """A translation backend failed (rate limit, network, no result, ...).

    The translator chain treats this as transient: it retries the same backend (with
    backoff) and then falls back to the next one.
    """


class PermanentTranslationError(TranslationError):
    """A failure that retrying the same backend cannot fix (bad key, quota, bad request).

    The chain skips any remaining retries for that backend and moves on immediately.
    """


class SecretStoreError(SnipLingoError):
    """Reading, writing or deleting a secret in the OS credential store failed.

    The message explains *why* (it is shown to the user) and never contains the secret.
    """
