"""Optional Gemini translator (Google Generative Language API, v1beta).

Disabled unless the user supplies an API key in config (see `.claude/rules/secrets.md`).
Authentication uses the ``x-goog-api-key`` request header (not a URL query param) so the
key is not visible in URLs that might be echoed by ``requests`` exceptions. The key is
never included in our own exception messages. HTTP goes through the shared
:mod:`sniplingo.adapters.http` seam (injectable ``post``), which also classifies
failures: 429 / 5xx are transient, other 4xx (bad key, bad model) are permanent.

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
from typing import TYPE_CHECKING, Any

from sniplingo.adapters.http import HttpPost, post_json, requests_post
from sniplingo.domain.errors import TranslationError
from sniplingo.domain.models import BackendName, TranslationResult

if TYPE_CHECKING:
    from PIL.Image import Image

_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
_DEFAULT_MODEL = "gemini-2.5-flash"
_TIMEOUT_SECONDS = 15.0


class GeminiTranslator:
    name = BackendName.GEMINI.value

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        post: HttpPost = requests_post,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini backend requires a non-empty API key")
        self._api_key = api_key
        self._model = model or _DEFAULT_MODEL
        self._post = post

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
        return post_json(
            self._post,
            f"{_API_ROOT}/{self._model}:generateContent",
            label="Gemini",
            timeout=_TIMEOUT_SECONDS,
            headers={"x-goog-api-key": self._api_key, "Content-Type": "application/json"},
            json=payload,
        )


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
