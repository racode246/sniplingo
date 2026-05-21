import pytest
from tests.fakes import FakeTranslator

from sniplingo.core.translator_chain import TranslatorChain
from sniplingo.domain.errors import TranslationError


def _noop_sleep(_seconds: float) -> None:
    pass


def test_primary_success_skips_fallback():
    primary = FakeTranslator(name="google", mapping={"hi": "やあ"})
    fallback = FakeTranslator(name="argos")
    chain = TranslatorChain(primary, [fallback], retries=1, sleep=_noop_sleep)

    result = chain.translate("hi", "en", "ja")

    assert result.translated_text == "やあ"
    assert result.backend == "google"
    assert fallback.calls == []  # never reached


def test_falls_back_after_retrying_primary_once():
    primary = FakeTranslator(name="google", error=TranslationError("rate limited"))
    fallback = FakeTranslator(name="argos", mapping={"hi": "やあ(offline)"})
    sleeps: list[float] = []
    chain = TranslatorChain(
        primary, [fallback], retries=1, backoff_seconds=0.3, sleep=sleeps.append
    )

    result = chain.translate("hi", "en", "ja")

    assert result.backend == "argos"
    assert result.translated_text == "やあ(offline)"
    assert len(primary.calls) == 2  # initial attempt + one retry
    assert sleeps == [0.3]  # exactly one backoff before the retry


def test_retries_count_is_respected_before_fallback():
    primary = FakeTranslator(name="google", error=TranslationError("boom"))
    fallback = FakeTranslator(name="argos", mapping={"hi": "x"})
    sleeps: list[float] = []
    chain = TranslatorChain(
        primary, [fallback], retries=2, backoff_seconds=0.1, sleep=sleeps.append
    )

    chain.translate("hi", "en", "ja")

    assert len(primary.calls) == 3  # initial + two retries
    assert sleeps == [0.1, 0.1]


def test_all_backends_fail_returns_error_result_without_crashing():
    primary = FakeTranslator(name="google", error=TranslationError("net down"))
    fallback = FakeTranslator(name="argos", error=TranslationError("model missing"))
    chain = TranslatorChain(primary, [fallback], retries=0, sleep=_noop_sleep)

    result = chain.translate("hi", "en", "ja")

    assert result.ok is False
    assert result.error
    assert result.translated_text == ""
    assert result.source_text == "hi"


def test_unexpected_exception_is_not_swallowed():
    # Non-TranslationError bugs should surface, not be silently treated as fallback.
    primary = FakeTranslator(name="google", error=ValueError("programming bug"))
    fallback = FakeTranslator(name="argos", mapping={"hi": "x"})
    chain = TranslatorChain(primary, [fallback], retries=0, sleep=_noop_sleep)

    with pytest.raises(ValueError):
        chain.translate("hi", "en", "ja")
