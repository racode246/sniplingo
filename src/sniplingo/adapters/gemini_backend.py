"""Optional Gemini translator (Google Generative Language API, v1beta).

Disabled unless the user supplies an API key in config (see `.claude/rules/secrets.md`).
Authentication uses the ``x-goog-api-key`` request header (not a URL query param) so the
key is not visible in URLs that might be echoed by ``requests`` exceptions. The key is
never included in our own exception messages; the linked traceback (``__cause__``) is
preserved for debugging but our message stays generic.

Two entry points:
- :meth:`GeminiTranslator.translate` — text in, text out (implements the
  :class:`Translator` port; used by :class:`TranslatorChain`).
- :meth:`GeminiTranslator.translate_image` — sends the captured image directly
  to Gemini for combined OCR + translation, skipping the Windows OCR pre-process
  (implements the :class:`ImageTranslator` port).
"""

from __future__ import annotations

import base64
import io
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

import requests

from sniplingo.domain.errors import TranslationError
from sniplingo.domain.models import BackendName, TranslationResult

if TYPE_CHECKING:
    from PIL.Image import Image

_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
_DEFAULT_MODEL = "gemini-2.5-flash"
_TIMEOUT_SECONDS = 15.0


class _Response(Protocol):
    status_code: int

    def json(self) -> Any: ...


HttpPost = Callable[[str, dict[str, str], dict[str, Any], float], _Response]


class GeminiTranslator:
    name = BackendName.GEMINI.value

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        http_post: HttpPost | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini backend requires a non-empty API key")
        self._api_key = api_key
        self._model = model or _DEFAULT_MODEL
        self._post = http_post or _default_post

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        payload = {
            "contents": [{"parts": [{"text": _build_text_prompt(text, source, target)}]}],
            "generationConfig": {"temperature": 0.2},
        }
        data = self._call(payload)
        translated = _extract_text(data)
        if not translated:
            raise TranslationError("Gemini returned no text")
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )

    def translate_image(self, image: Image, source: str, target: str) -> TranslationResult:
        png_bytes = _image_to_png_bytes(image)
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": _build_vision_prompt(source, target)},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(png_bytes).decode("ascii"),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2},
        }
        data = self._call(payload)
        translated = _extract_text(data)
        if not translated:
            raise TranslationError("Gemini returned no text for image")
        return TranslationResult(
            source_text="",  # we didn't extract OCR text ourselves
            translated_text=translated,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )

    def _call(self, payload: dict[str, Any]) -> Any:
        url = f"{_API_ROOT}/{self._model}:generateContent"
        headers = {"x-goog-api-key": self._api_key, "Content-Type": "application/json"}
        try:
            response = self._post(url, headers, payload, _TIMEOUT_SECONDS)
        except requests.exceptions.RequestException as exc:
            # Don't include exc text in our message — it can contain the request URL.
            raise TranslationError("Gemini request failed") from exc
        if response.status_code >= 400:
            raise TranslationError(f"Gemini HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise TranslationError("Gemini returned non-JSON response") from exc


def _build_text_prompt(text: str, source: str, target: str) -> str:
    return (
        f"Translate the following text from {source} to {target}. "
        "Output only the translated text — no quotes, no explanations, no extra formatting. "
        "Preserve the original line breaks: produce exactly one translated line per input line, "
        "in the same order.\n\n"
        f"{text}"
    )


def _build_vision_prompt(source: str, target: str) -> str:
    return (
        f"The attached image contains {source} text (typically from a video-game UI: "
        "item tooltips, dialog, menus). Read it accurately, ignoring decorative "
        f"underlines / dividers / icons, and translate it into {target}. "
        "Output only the translated text — no quotes, no source text, no commentary. "
        "Preserve the visual line structure: produce one translated line per visible "
        "row of text, in the same order."
    )


def _extract_text(data: Any) -> str:
    try:
        candidates = data["candidates"]
        parts = candidates[0]["content"]["parts"]
        text = parts[0].get("text", "")
    except (KeyError, IndexError, TypeError):
        return ""
    return text.strip() if isinstance(text, str) else ""


def _image_to_png_bytes(image: Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _default_post(
    url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float
) -> _Response:
    return requests.post(url, headers=headers, json=payload, timeout=timeout)
