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

    The translator chain treats this as recoverable and falls back to the next backend.
    """
