import logging

import pytest
from tests.fakes import FakeTranslator

from sniplingo.core.translator_chain import TranslatorChain
from sniplingo.domain.errors import PermanentTranslationError, TranslationError
from sniplingo.domain.models import BackendAttempt, ResultStatus


def _noop_sleep(_seconds: float) -> None:
    pass


def test_requires_at_least_one_backend():
    with pytest.raises(ValueError):
        TranslatorChain([])


def test_primary_success_skips_fallback():
    primary = FakeTranslator(name="google", mapping={"hi": "やあ"})
    fallback = FakeTranslator(name="gemini")
    chain = TranslatorChain([primary, fallback], retries=1, sleep=_noop_sleep)

    result = chain.translate("hi", "en", "ja")

    assert result.translated_text == "やあ"
    assert result.backend == "google"
    assert result.attempts == (BackendAttempt("google"),)
    assert fallback.calls == []  # never reached


def test_falls_back_after_retrying_transient_failure_once():
    primary = FakeTranslator(name="google", error=TranslationError("rate limited"))
    fallback = FakeTranslator(name="gemini", mapping={"hi": "やあ(gemini)"})
    sleeps: list[float] = []
    chain = TranslatorChain(
        [primary, fallback], retries=1, backoff_seconds=0.3, sleep=sleeps.append
    )

    result = chain.translate("hi", "en", "ja")

    assert result.backend == "gemini"
    assert result.translated_text == "やあ(gemini)"
    assert len(primary.calls) == 2  # initial attempt + one retry
    assert sleeps == [0.3]  # exactly one backoff before the retry
    assert result.attempts == (
        BackendAttempt("google", "rate limited"),
        BackendAttempt("gemini"),
    )


def test_retries_count_is_respected_before_fallback():
    primary = FakeTranslator(name="google", error=TranslationError("boom"))
    fallback = FakeTranslator(name="gemini", mapping={"hi": "x"})
    sleeps: list[float] = []
    chain = TranslatorChain(
        [primary, fallback], retries=2, backoff_seconds=0.1, sleep=sleeps.append
    )

    chain.translate("hi", "en", "ja")

    assert len(primary.calls) == 3  # initial + two retries
    assert sleeps == [0.1, 0.1]


def test_permanent_failure_skips_retries_and_backoff():
    """A bad key / quota / block won't fix itself in 0.5 s — go straight to the next one."""
    primary = FakeTranslator(name="deepl", error=PermanentTranslationError("HTTP 403"))
    fallback = FakeTranslator(name="google", mapping={"hi": "やあ"})
    sleeps: list[float] = []
    chain = TranslatorChain([primary, fallback], retries=3, sleep=sleeps.append)

    result = chain.translate("hi", "en", "ja")

    assert len(primary.calls) == 1
    assert sleeps == []
    assert result.backend == "google"


def test_all_backends_fail_returns_failed_result_reporting_every_backend():
    """The error must name every backend — not just the last one, which may be irrelevant."""
    primary = FakeTranslator(name="google", error=TranslationError("net down"))
    fallback = FakeTranslator(name="gemini", error=PermanentTranslationError("HTTP 403"))
    chain = TranslatorChain([primary, fallback], retries=0, sleep=_noop_sleep)

    result = chain.translate("hi", "en", "ja")

    assert result.status is ResultStatus.FAILED
    assert result.translated_text == ""
    assert result.source_text == "hi"
    assert result.backend is None
    assert "google: net down" in result.error
    assert "gemini: HTTP 403" in result.error
    assert result.attempts == (
        BackendAttempt("google", "net down"),
        BackendAttempt("gemini", "HTTP 403"),
    )


def test_each_failure_is_logged_as_a_warning(caplog):
    primary = FakeTranslator(name="google", error=TranslationError("net down"))
    fallback = FakeTranslator(name="gemini", mapping={"hi": "x"})
    chain = TranslatorChain([primary, fallback], retries=0, sleep=_noop_sleep)

    with caplog.at_level(logging.WARNING, logger="sniplingo"):
        chain.translate("hi", "en", "ja")

    assert any("google" in r.getMessage() and "net down" in r.getMessage() for r in caplog.records)


def test_unexpected_exception_is_not_swallowed():
    # Non-TranslationError bugs should surface, not be silently treated as fallback.
    primary = FakeTranslator(name="google", error=ValueError("programming bug"))
    fallback = FakeTranslator(name="gemini", mapping={"hi": "x"})
    chain = TranslatorChain([primary, fallback], retries=0, sleep=_noop_sleep)

    with pytest.raises(ValueError):
        chain.translate("hi", "en", "ja")
