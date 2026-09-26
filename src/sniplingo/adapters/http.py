"""Shared HTTP seam for the translation adapters (Google Cloud / DeepL / Gemini).

Every HTTP backend takes an injectable :class:`HttpPost` (defaulting to
:func:`requests_post`) so unit tests drive it with a hand-written fake, and all of
them turn transport / status / decode failures into the same domain errors via
:func:`post_json`:

- network errors, 408, 429, 5xx -> :class:`TranslationError` (transient; retried)
- any other 4xx (bad key, quota, bad request) -> :class:`PermanentTranslationError`

Error messages never include the underlying exception text (``requests`` messages
may echo the request URL); the original exception is kept as ``__cause__``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import requests
from requests.exceptions import RequestException

from sniplingo.domain.errors import PermanentTranslationError, TranslationError

_TRANSIENT_STATUSES = frozenset({408, 429})
_MASK = "****"
_MAX_DETAIL = 200


class HttpResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


class HttpPost(Protocol):
    """Subset of ``requests.post``: ``post(url, *, timeout, headers=, params=, data=, json=)``."""

    def __call__(self, url: str, **kwargs: Any) -> HttpResponse: ...


def requests_post(url: str, **kwargs: Any) -> HttpResponse:
    """Default :class:`HttpPost` backed by ``requests``."""
    return requests.post(url, **kwargs)


def error_for_status(label: str, status: int, detail: str | None = None) -> TranslationError:
    """Classify an HTTP error status into a transient or permanent domain error."""
    message = f"{label} HTTP {status}" + (f": {detail}" if detail else "")
    if status in _TRANSIENT_STATUSES or status >= 500:
        return TranslationError(message)
    return PermanentTranslationError(message)


def post_json(
    post: HttpPost,
    url: str,
    *,
    label: str,
    timeout: float,
    secrets: Sequence[str] = (),
    **kwargs: Any,
) -> Any:
    """POST via ``post`` and return the decoded JSON body, raising domain errors on failure.

    On an HTTP error the API's own message (``{"error": {"message"}}`` or ``{"message"}``)
    is appended — it's what explains setup problems like a disabled API or a bad key.
    Any of ``secrets`` appearing in it is masked.
    """
    try:
        response = post(url, timeout=timeout, **kwargs)
    except RequestException as exc:
        raise TranslationError(f"{label} request failed ({type(exc).__name__})") from exc
    if response.status_code >= 400:
        detail = _error_detail(response, secrets)
        raise error_for_status(label, response.status_code, detail)
    try:
        return response.json()
    except ValueError as exc:
        raise TranslationError(f"{label} returned a non-JSON response") from exc


def _error_detail(response: HttpResponse, secrets: Sequence[str]) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    message = error.get("message") if isinstance(error, dict) else body.get("message")
    if not isinstance(message, str) or not message.strip():
        return None
    for secret in secrets:
        if secret:
            message = message.replace(secret, _MASK)
    message = " ".join(message.split())
    return message if len(message) <= _MAX_DETAIL else message[: _MAX_DETAIL - 1] + "…"
