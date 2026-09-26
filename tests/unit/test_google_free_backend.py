import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError
from tests.fakes import FakeHttpPost, FakeHttpResponse

from sniplingo.adapters.google_free_backend import GTX_URL, GoogleFreeTranslator
from sniplingo.domain.errors import PermanentTranslationError, TranslationError


def _payload(*segments: str) -> list:
    """Shape of a real `client=gtx` response: data[0] is a list of [translated, source, ...]."""
    return [[[seg, "src", None, None, 10] for seg in segments], None, "en"]


def _backend(payload=None, *, status=200, error=None) -> tuple[GoogleFreeTranslator, FakeHttpPost]:
    post = FakeHttpPost(FakeHttpResponse(status_code=status, payload=payload), error=error)
    return GoogleFreeTranslator(post=post), post


def test_success_returns_translation_result():
    backend, _ = _backend(_payload("やあ"))
    result = backend.translate("hi", "en", "ja")
    assert result.translated_text == "やあ"
    assert result.source_text == "hi"
    assert result.backend == "google_free"
    assert result.ok


def test_segments_are_concatenated_preserving_newlines():
    backend, _ = _backend(_payload("こんにちは。\n", "続ける"))
    result = backend.translate("Hello.\nContinue", "en", "ja")
    assert result.translated_text == "こんにちは。\n続ける"


def test_request_posts_text_in_body_to_the_gtx_endpoint():
    backend, post = _backend(_payload("x"))
    backend.translate("hi\nthere", "en", "ja")
    call = post.last
    assert call["url"] == GTX_URL
    assert call["params"] == {"client": "gtx", "sl": "en", "tl": "ja", "dt": "t"}
    # POST body, so long OCR output doesn't hit URL length limits.
    assert call["data"] == {"q": "hi\nthere"}
    assert call["timeout"] > 0


def test_rate_limit_is_transient():
    backend, _ = _backend(status=429)
    with pytest.raises(TranslationError) as info:
        backend.translate("hi", "en", "ja")
    assert not isinstance(info.value, PermanentTranslationError)


def test_client_error_is_permanent():
    backend, _ = _backend(status=400)
    with pytest.raises(PermanentTranslationError):
        backend.translate("hi", "en", "ja")


def test_network_error_is_translation_error():
    backend, _ = _backend(error=RequestsConnectionError("offline"))
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")


@pytest.mark.parametrize("payload", [None, [], [None], "oops", [[["x"], 5]], {"a": 1}])
def test_malformed_payload_is_translation_error(payload):
    backend, _ = _backend(payload)
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")


@pytest.mark.parametrize("segments", [("",), ("  ", "\n")])
def test_blank_result_is_translation_error(segments):
    backend, _ = _backend(_payload(*segments))
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")
