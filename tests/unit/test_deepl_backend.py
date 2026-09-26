import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError
from tests.fakes import FakeHttpPost, FakeHttpResponse

from sniplingo.adapters.deepl_backend import DEEPL_FREE_URL, DEEPL_PRO_URL, DeepLTranslator
from sniplingo.domain.errors import PermanentTranslationError, TranslationError


def _ok(text: str = "やあ") -> dict:
    return {"translations": [{"detected_source_language": "EN", "text": text}]}


def _backend(
    payload=None, *, key: str = "key:fx", status: int = 200, error=None
) -> tuple[DeepLTranslator, FakeHttpPost]:
    post = FakeHttpPost(FakeHttpResponse(status_code=status, payload=payload), error=error)
    return DeepLTranslator(api_key=key, post=post), post


def test_requires_non_empty_api_key():
    with pytest.raises(ValueError):
        DeepLTranslator(api_key="")


def test_success_returns_translation_result():
    backend, _ = _backend(_ok("やあ"))
    result = backend.translate("hi", "en", "ja")
    assert result.translated_text == "やあ"
    assert result.source_text == "hi"
    assert result.backend == "deepl"
    assert result.ok


def test_request_uses_header_auth_and_json_body():
    backend, post = _backend(_ok(), key="secret-key:fx")
    backend.translate("Hello\nWorld", "en", "ja")
    call = post.last
    assert call["headers"]["Authorization"] == "DeepL-Auth-Key secret-key:fx"
    # The key must not travel in the URL or body (deep-translator used to put it in params).
    assert "secret-key" not in call["url"]
    assert "params" not in call and "data" not in call
    assert call["json"] == {"text": ["Hello\nWorld"], "source_lang": "EN", "target_lang": "JA"}
    assert call["timeout"] > 0


def test_free_keys_use_the_free_endpoint_and_others_the_pro_one():
    free, free_post = _backend(_ok(), key="abc:fx")
    pro, pro_post = _backend(_ok(), key="abc")
    free.translate("hi", "en", "ja")
    pro.translate("hi", "en", "ja")
    assert free_post.last["url"] == DEEPL_FREE_URL
    assert pro_post.last["url"] == DEEPL_PRO_URL


@pytest.mark.parametrize(
    "target,expected",
    [("ja", "JA"), ("en", "EN-US"), ("pt", "PT-BR"), ("zh", "ZH"), ("en-GB", "EN-GB")],
)
def test_target_language_codes_are_mapped_to_deepl_codes(target, expected):
    backend, post = _backend(_ok())
    backend.translate("hi", "ja", target)
    assert post.last["json"]["target_lang"] == expected


def test_source_language_drops_region_variant():
    backend, post = _backend(_ok())
    backend.translate("hi", "en-US", "ja")
    assert post.last["json"]["source_lang"] == "EN"


@pytest.mark.parametrize("status", [403, 456])  # bad key / quota exceeded
def test_auth_and_quota_errors_are_permanent_and_do_not_leak_key(status):
    backend, _ = _backend(key="super-secret-key", status=status)
    with pytest.raises(PermanentTranslationError) as info:
        backend.translate("hi", "en", "ja")
    assert "super-secret-key" not in str(info.value)


def test_rate_limit_is_transient():
    backend, _ = _backend(status=429)
    with pytest.raises(TranslationError) as info:
        backend.translate("hi", "en", "ja")
    assert not isinstance(info.value, PermanentTranslationError)


def test_network_error_does_not_leak_key():
    backend, _ = _backend(
        key="super-secret-key", error=RequestsConnectionError("auth_key=super-secret-key")
    )
    with pytest.raises(TranslationError) as info:
        backend.translate("hi", "en", "ja")
    assert "super-secret-key" not in str(info.value)


@pytest.mark.parametrize("payload", [None, {}, {"translations": []}, _ok(""), _ok("  ")])
def test_malformed_or_blank_response_is_translation_error(payload):
    backend, _ = _backend(payload)
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")
