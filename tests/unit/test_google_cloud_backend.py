import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError
from tests.fakes import FakeHttpPost, FakeHttpResponse

from sniplingo.adapters.google_cloud_backend import CLOUD_TRANSLATE_URL, GoogleCloudTranslator
from sniplingo.domain.errors import PermanentTranslationError, TranslationError


def _ok(text: str = "やあ") -> dict:
    return {"data": {"translations": [{"translatedText": text}]}}


def _backend(
    payload=None, *, key: str = "cloud-key", status: int = 200, error=None
) -> tuple[GoogleCloudTranslator, FakeHttpPost]:
    post = FakeHttpPost(FakeHttpResponse(status_code=status, payload=payload), error=error)
    return GoogleCloudTranslator(api_key=key, post=post), post


def test_requires_non_empty_api_key():
    with pytest.raises(ValueError):
        GoogleCloudTranslator(api_key="")


def test_success_returns_translation_result():
    backend, _ = _backend(_ok("やあ"))
    result = backend.translate("hi", "en", "ja")
    assert result.translated_text == "やあ"
    assert result.source_text == "hi"
    assert result.backend == "google_cloud"
    assert result.ok


def test_request_uses_v2_endpoint_header_auth_and_plain_text_format():
    backend, post = _backend(_ok(), key="secret-cloud-key")
    backend.translate("Hello\nWorld", "en", "ja")
    call = post.last
    assert call["url"] == CLOUD_TRANSLATE_URL
    # Key only in the header — never in the URL, query or body.
    assert call["headers"]["X-Goog-Api-Key"] == "secret-cloud-key"
    assert "secret-cloud-key" not in call["url"] and "params" not in call
    # format=text: no HTML entity escaping ("&#39;") and newlines are kept.
    assert call["json"] == {"q": ["Hello\nWorld"], "source": "en", "target": "ja", "format": "text"}
    assert call["timeout"] > 0


def test_newlines_in_the_translation_are_preserved():
    backend, _ = _backend(_ok("こんにちは\n世界"))
    assert backend.translate("Hello\nWorld", "en", "ja").translated_text == "こんにちは\n世界"


def test_disabled_api_or_bad_key_is_permanent_with_googles_message():
    body = {"error": {"code": 403, "message": "Cloud Translation API has not been used in project"}}
    backend, _ = _backend(body, key="super-secret-key", status=403)
    with pytest.raises(PermanentTranslationError) as info:
        backend.translate("hi", "en", "ja")
    assert "has not been used" in str(info.value)
    assert "super-secret-key" not in str(info.value)


def test_rate_limit_is_transient():
    backend, _ = _backend({"error": {"message": "quota"}}, status=429)
    with pytest.raises(TranslationError) as info:
        backend.translate("hi", "en", "ja")
    assert not isinstance(info.value, PermanentTranslationError)


def test_network_error_does_not_leak_key():
    backend, _ = _backend(
        key="super-secret-key", error=RequestsConnectionError("key=super-secret-key refused")
    )
    with pytest.raises(TranslationError) as info:
        backend.translate("hi", "en", "ja")
    assert "super-secret-key" not in str(info.value)


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"data": {}}, {"data": {"translations": []}}, _ok(""), _ok("  "), {"data": [1]}],
)
def test_malformed_or_blank_response_is_translation_error(payload):
    backend, _ = _backend(payload)
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")


def test_blank_lines_inserted_by_the_api_are_collapsed():
    """Seen live: "Save your game.\nQuit" came back as "...。\n\n終了". The pipeline never
    sends blank lines, so one translated row per input row is the faithful shape."""
    backend, _ = _backend(_ok("ゲームを保存してください。\n\n終了\n"))
    assert backend.translate("Save your game.\nQuit", "en", "ja").translated_text == (
        "ゲームを保存してください。\n終了"
    )
