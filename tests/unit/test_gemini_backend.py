import pytest
import requests

from sniplingo.adapters.gemini_backend import GeminiTranslator
from sniplingo.domain.errors import TranslationError


class _Response:
    """Stand-in for a `requests.Response` — only the bits the adapter touches."""

    def __init__(self, status_code: int = 200, payload=None, raw: str | None = None):
        self.status_code = status_code
        self._payload = payload
        self._raw = raw

    def json(self):
        if self._payload is None and self._raw is not None:
            raise ValueError("not json")
        return self._payload


def _ok_payload(text: str = "やあ") -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_requires_non_empty_api_key():
    with pytest.raises(ValueError):
        GeminiTranslator(api_key="")


def test_success_returns_translation_result():
    backend = GeminiTranslator(
        api_key="k", http_post=lambda *a, **k: _Response(payload=_ok_payload())
    )
    result = backend.translate("hi", "en", "ja")
    assert result.translated_text == "やあ"
    assert result.source_text == "hi"
    assert result.backend == "gemini"
    assert result.ok


def test_request_targets_configured_model_and_uses_header_auth():
    seen: dict = {}

    def fake_post(url, headers, payload, timeout):
        seen.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return _Response(payload=_ok_payload())

    backend = GeminiTranslator(api_key="secret-key", model="gemini-2.5-flash", http_post=fake_post)
    backend.translate("Hello world", "en", "ja")

    # URL targets the chosen model and does NOT leak the API key as a query param.
    assert "gemini-2.5-flash:generateContent" in seen["url"]
    assert "secret-key" not in seen["url"]
    # Auth is via header (modern Google API style); key not echoed elsewhere.
    assert seen["headers"]["x-goog-api-key"] == "secret-key"
    # Prompt body includes the source/target languages and the text to translate.
    prompt = seen["payload"]["contents"][0]["parts"][0]["text"]
    assert "en" in prompt and "ja" in prompt
    assert "Hello world" in prompt
    # Newline preservation is requested so multi-row OCR keeps its line structure.
    assert "line" in prompt.lower()
    assert seen["timeout"] > 0


def test_default_model_is_gemini_2_5_flash():
    seen: dict = {}

    def fake_post(url, headers, payload, timeout):
        seen["url"] = url
        return _Response(payload=_ok_payload())

    GeminiTranslator(api_key="k", http_post=fake_post).translate("hi", "en", "ja")
    assert "gemini-2.5-flash:generateContent" in seen["url"]


def test_http_error_becomes_translation_error_without_key_leak():
    backend = GeminiTranslator(
        api_key="super-secret-key",
        http_post=lambda *a, **k: _Response(status_code=429, payload={"error": "rate limit"}),
    )
    with pytest.raises(TranslationError) as exc_info:
        backend.translate("hi", "en", "ja")
    assert "super-secret-key" not in str(exc_info.value)


def test_network_exception_becomes_translation_error_without_key_leak():
    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError(
            "connection failed to host with key=super-secret-key"
        )

    backend = GeminiTranslator(api_key="super-secret-key", http_post=boom)
    with pytest.raises(TranslationError) as exc_info:
        backend.translate("hi", "en", "ja")
    # The raised exception message must not echo the key (even if the underlying
    # exception's text happens to). Linked traceback is allowed for debugging.
    assert "super-secret-key" not in str(exc_info.value)


def test_non_json_response_becomes_translation_error():
    backend = GeminiTranslator(
        api_key="k",
        http_post=lambda *a, **k: _Response(payload=None, raw="<html>oops</html>"),
    )
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")


def test_empty_candidates_becomes_translation_error():
    backend = GeminiTranslator(
        api_key="k",
        http_post=lambda *a, **k: _Response(payload={"candidates": []}),
    )
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")


def test_blank_text_response_becomes_translation_error():
    backend = GeminiTranslator(
        api_key="k",
        http_post=lambda *a, **k: _Response(payload=_ok_payload(text="   ")),
    )
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")


def test_response_text_is_stripped():
    backend = GeminiTranslator(
        api_key="k",
        http_post=lambda *a, **k: _Response(payload=_ok_payload(text="  やあ  \n")),
    )
    result = backend.translate("hi", "en", "ja")
    assert result.translated_text == "やあ"


# --- translate_image (Vision path) -------------------------------------------------


class _StubImage:
    """Minimal stand-in for PIL.Image.Image — exposes only what the adapter needs."""

    def __init__(self, payload: bytes = b"\x89PNG\r\n\x1a\nFAKE") -> None:
        self._payload = payload
        self.save_calls: list[tuple[object, str]] = []

    def save(self, fp, format) -> None:  # noqa: A002 - matches PIL signature
        self.save_calls.append((fp, format))
        fp.write(self._payload)


def test_translate_image_sends_image_inline_with_prompt():
    import base64

    seen: dict = {}

    def fake_post(url, headers, payload, timeout):
        seen.update(url=url, headers=headers, payload=payload)
        return _Response(payload=_ok_payload(text="やあ世界"))

    img = _StubImage(payload=b"\x89PNG\r\n\x1a\nDATA")
    backend = GeminiTranslator(api_key="k", model="gemini-2.5-flash", http_post=fake_post)
    result = backend.translate_image(img, "en", "ja")

    # Image was serialized to PNG and base64-encoded into inline_data.
    parts = seen["payload"]["contents"][0]["parts"]
    inline = next(p["inline_data"] for p in parts if "inline_data" in p)
    assert inline["mime_type"] == "image/png"
    assert base64.b64decode(inline["data"]) == b"\x89PNG\r\n\x1a\nDATA"
    # A text part instructs the model to OCR + translate (no separate Windows OCR).
    text_part = next(p["text"] for p in parts if "text" in p)
    assert "ja" in text_part and "en" in text_part
    # Same model + header auth as the text path.
    assert "gemini-2.5-flash:generateContent" in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "k"

    assert result.translated_text == "やあ世界"
    assert result.backend == "gemini"
    assert result.source_text == ""  # no OCR text was extracted by us
    assert result.ok


def test_translate_image_http_error_becomes_translation_error_without_key_leak():
    backend = GeminiTranslator(
        api_key="super-secret-vision-key",
        http_post=lambda *a, **k: _Response(status_code=429, payload={"error": "rate"}),
    )
    with pytest.raises(TranslationError) as exc_info:
        backend.translate_image(_StubImage(), "en", "ja")
    assert "super-secret-vision-key" not in str(exc_info.value)


def test_translate_image_network_failure_is_translation_error():
    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("no route")

    backend = GeminiTranslator(api_key="k", http_post=boom)
    with pytest.raises(TranslationError):
        backend.translate_image(_StubImage(), "en", "ja")


def test_translate_image_blank_response_is_translation_error():
    backend = GeminiTranslator(
        api_key="k",
        http_post=lambda *a, **k: _Response(payload=_ok_payload(text="")),
    )
    with pytest.raises(TranslationError):
        backend.translate_image(_StubImage(), "en", "ja")
