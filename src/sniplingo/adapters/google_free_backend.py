"""Default translator: Google's free `client=gtx` JSON endpoint (no API key).

We call ``translate.googleapis.com/translate_a/single`` directly instead of going
through `deep-translator`'s ``GoogleTranslator``: that one scrapes the
``translate.google.com/m`` HTML page, which Google readily puts behind a CAPTCHA
(HTTP 429 -> ``google.com/sorry``) for the whole IP — every request then fails
until the block lifts. The JSON API is not affected by that block.

HTTP goes through the shared :mod:`sniplingo.adapters.http` seam (injectable ``post``).
"""

from __future__ import annotations

from typing import Any

from sniplingo.adapters.http import HttpPost, post_json, requests_post
from sniplingo.domain.errors import TranslationError
from sniplingo.domain.models import BackendName, TranslationResult

GTX_URL = "https://translate.googleapis.com/translate_a/single"
_TIMEOUT_SECONDS = 10.0
_LABEL = "google free translate"


class GoogleFreeTranslator:
    name = BackendName.GOOGLE_FREE.value

    def __init__(self, post: HttpPost = requests_post) -> None:
        self._post = post

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        # Text goes in the POST body, so long OCR output doesn't hit URL length limits.
        payload = post_json(
            self._post,
            GTX_URL,
            label=_LABEL,
            timeout=_TIMEOUT_SECONDS,
            params={"client": "gtx", "sl": source, "tl": target, "dt": "t"},
            data={"q": text},
        )
        translated = _join_segments(payload)
        if not translated.strip():
            raise TranslationError(f"{_LABEL} returned no text")
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )


def _join_segments(payload: Any) -> str:
    """``payload[0]`` is a list of ``[translated, source, ...]`` sentence segments.

    Segments carry their own trailing whitespace/newlines, so plain concatenation
    reproduces the original line structure.
    """
    segments = payload[0] if isinstance(payload, list) and payload else None
    if not isinstance(segments, list) or not all(
        isinstance(seg, list) and seg and isinstance(seg[0], str) for seg in segments
    ):
        raise TranslationError(f"{_LABEL} returned an unexpected response")
    return "".join(seg[0] for seg in segments)
