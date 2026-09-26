"""Optional DeepL translator (DeepL API v2, called directly).

Disabled unless the user supplies an API key in config (see `.claude/rules/secrets.md`).
The key travels only in the ``Authorization: DeepL-Auth-Key`` header — never in the URL
or body — and never appears in our error messages. Free-plan keys end in ``:fx`` and use
the ``api-free`` host; any other key uses the Pro host.

HTTP goes through the shared :mod:`sniplingo.adapters.http` seam (injectable ``post``).
Status 403 (bad key) and 456 (quota exceeded) are permanent; 429 / 5xx are transient.
"""

from __future__ import annotations

from typing import Any

from sniplingo.adapters.http import HttpPost, post_json, requests_post
from sniplingo.domain.errors import TranslationError
from sniplingo.domain.models import BackendName, TranslationResult

DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"
_TIMEOUT_SECONDS = 10.0
_LABEL = "DeepL"

# Bare target codes DeepL no longer accepts on their own; pick the common variant.
_TARGET_VARIANTS = {"EN": "EN-US", "PT": "PT-BR"}


class DeepLTranslator:
    name = BackendName.DEEPL.value

    def __init__(self, api_key: str, post: HttpPost = requests_post) -> None:
        if not api_key:
            raise ValueError("DeepL backend requires a non-empty API key")
        self._api_key = api_key
        self._post = post

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        data = post_json(
            self._post,
            DEEPL_FREE_URL if self._api_key.endswith(":fx") else DEEPL_PRO_URL,
            label=_LABEL,
            timeout=_TIMEOUT_SECONDS,
            headers={"Authorization": f"DeepL-Auth-Key {self._api_key}"},
            json={
                "text": [text],
                "source_lang": _source_code(source),
                "target_lang": _target_code(target),
            },
        )
        translated = _extract_text(data)
        if not translated.strip():
            raise TranslationError(f"{_LABEL} returned no text")
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )


def _source_code(lang: str) -> str:
    """DeepL source codes have no region variant: ``en-US`` -> ``EN``."""
    return lang.split("-")[0].upper()


def _target_code(lang: str) -> str:
    code = lang.upper()
    return _TARGET_VARIANTS.get(code, code)


def _extract_text(data: Any) -> str:
    translations = data.get("translations") if isinstance(data, dict) else None
    if not isinstance(translations, list) or not translations:
        return ""
    first = translations[0]
    text = first.get("text") if isinstance(first, dict) else None
    return text if isinstance(text, str) else ""
