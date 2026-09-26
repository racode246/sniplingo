import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError
from tests.fakes import FakeHttpPost, FakeHttpResponse

from sniplingo.adapters.http import error_for_status, post_json
from sniplingo.domain.errors import PermanentTranslationError, TranslationError


def test_post_json_forwards_request_and_returns_decoded_body():
    post = FakeHttpPost(FakeHttpResponse(payload={"ok": 1}))

    body = post_json(
        post, "https://x.test/api", label="svc", timeout=3.0, headers={"a": "b"}, json={"q": 1}
    )

    assert body == {"ok": 1}
    assert post.last == {
        "url": "https://x.test/api",
        "timeout": 3.0,
        "headers": {"a": "b"},
        "json": {"q": 1},
    }


def test_transport_error_is_transient_and_does_not_echo_the_exception_text():
    # requests messages can include the full URL; keep ours generic (secrets.md).
    post = FakeHttpPost(error=RequestsConnectionError("https://x.test/?key=SECRET refused"))

    with pytest.raises(TranslationError) as info:
        post_json(post, "https://x.test", label="svc", timeout=1.0)

    assert not isinstance(info.value, PermanentTranslationError)
    assert "SECRET" not in str(info.value)
    assert "svc" in str(info.value) and "ConnectionError" in str(info.value)


def test_non_json_body_is_translation_error():
    post = FakeHttpPost(FakeHttpResponse(invalid_json=True))
    with pytest.raises(TranslationError):
        post_json(post, "https://x.test", label="svc", timeout=1.0)


def test_http_error_status_raises_classified_error():
    post = FakeHttpPost(FakeHttpResponse(status_code=403))
    with pytest.raises(PermanentTranslationError, match="svc HTTP 403"):
        post_json(post, "https://x.test", label="svc", timeout=1.0)


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503])
def test_retryable_statuses_are_transient(status):
    err = error_for_status("svc", status)
    assert isinstance(err, TranslationError)
    assert not isinstance(err, PermanentTranslationError)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 456])
def test_other_client_errors_are_permanent(status):
    assert isinstance(error_for_status("svc", status), PermanentTranslationError)


# --- the API's own error message is surfaced (setup problems are otherwise opaque) -----


@pytest.mark.parametrize(
    "body",
    [
        {"error": {"code": 403, "message": "Cloud Translation API has not been used"}},  # Google
        {"message": "Cloud Translation API has not been used"},  # DeepL style
    ],
)
def test_error_body_message_is_included(body):
    post = FakeHttpPost(FakeHttpResponse(status_code=403, payload=body))
    with pytest.raises(PermanentTranslationError) as info:
        post_json(post, "https://x.test", label="svc", timeout=1.0)
    assert str(info.value) == "svc HTTP 403: Cloud Translation API has not been used"


def test_error_detail_masks_given_secrets_and_is_truncated():
    body = {"error": {"message": "bad key SECRET-KEY-123 " + "x" * 500}}
    post = FakeHttpPost(FakeHttpResponse(status_code=400, payload=body))
    with pytest.raises(PermanentTranslationError) as info:
        post_json(post, "https://x.test", label="svc", timeout=1.0, secrets=["SECRET-KEY-123"])
    message = str(info.value)
    assert "SECRET-KEY-123" not in message
    assert "****" in message
    assert len(message) < 300


@pytest.mark.parametrize("payload,invalid", [(None, True), ("<html>", False), ({"x": 1}, False)])
def test_unreadable_error_body_falls_back_to_status_only(payload, invalid):
    post = FakeHttpPost(FakeHttpResponse(status_code=429, payload=payload, invalid_json=invalid))
    with pytest.raises(TranslationError) as info:
        post_json(post, "https://x.test", label="svc", timeout=1.0)
    assert str(info.value) == "svc HTTP 429"


def test_secrets_are_not_forwarded_to_the_http_call():
    post = FakeHttpPost(FakeHttpResponse(payload={}))
    post_json(post, "https://x.test", label="svc", timeout=1.0, secrets=["k"])
    assert "secrets" not in post.last
