"""Default translator: Google Cloud Translation API v2 (Basic), authenticated by API key.

The official, supported Google translation API (the key-less ``client=gtx`` endpoint we
used before is internal to Google's own clients and gets IP-blocked as bot traffic).
Needs a Google Cloud project with the Cloud Translation API enabled and an API key
(billing account required; the first 500k characters per month are free).

The key travels only in the ``X-Goog-Api-Key`` header — never in the URL or body — and
is masked if Google echoes it in an error. ``format=text`` keeps newlines and avoids
HTML entity escaping; blank lines the API inserts are dropped. HTTP goes through the
shared :mod:`sniplingo.adapters.http` seam: 429 / 5xx are transient; 400 (bad key) /
403 (API disabled, billing) are permanent and carry Google's own explanation.
"""

from __future__ import annotations

from typing import Any

from sniplingo.adapters.http import HttpPost, post_json, requests_post
from sniplingo.domain.errors import TranslationError
from sniplingo.domain.models import BackendName, TranslationResult

CLOUD_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"
_TIMEOUT_SECONDS = 10.0
_LABEL = "Google Cloud Translation"


class GoogleCloudTranslator:
    name = BackendName.GOOGLE_CLOUD.value

    def __init__(self, api_key: str, post: HttpPost = requests_post) -> None:
        if not api_key:
            raise ValueError("Google Cloud Translation requires a non-empty API key")
        self._api_key = api_key
        self._post = post

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        data = post_json(
            self._post,
            CLOUD_TRANSLATE_URL,
            label=_LABEL,
            timeout=_TIMEOUT_SECONDS,
            secrets=[self._api_key],
            headers={"X-Goog-Api-Key": self._api_key},
            json={"q": [text], "source": source, "target": target, "format": "text"},
        )
        # The API sometimes inserts blank lines between rows; our input never has any,
        # so keep exactly one output row per non-empty line.
        rows = [line for line in _extract_text(data).splitlines() if line.strip()]
        translated = "\n".join(rows)
        if not translated:
            raise TranslationError(f"{_LABEL} returned no text")
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )


def _extract_text(data: Any) -> str:
    """``{"data": {"translations": [{"translatedText": ...}]}}`` -> the text, else ``""``."""
    inner = data.get("data") if isinstance(data, dict) else None
    translations = inner.get("translations") if isinstance(inner, dict) else None
    if not isinstance(translations, list) or not translations:
        return ""
    first = translations[0]
    text = first.get("translatedText") if isinstance(first, dict) else None
    return text if isinstance(text, str) else ""
