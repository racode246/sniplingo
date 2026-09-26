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
