import pytest
from deep_translator.exceptions import (
    NotValidLength,
    RequestError,
    TooManyRequests,
    TranslationNotFound,
)

from sniplingo.adapters.deep_translator_backend import GoogleFreeTranslator
from sniplingo.domain.errors import TranslationError


class _Client:
    def __init__(self, out=None, error=None):
        self._out = out
        self._error = error

    def translate(self, text):
        if self._error is not None:
            raise self._error
        return self._out


def test_success_returns_translation_result():
    backend = GoogleFreeTranslator(translator_factory=lambda s, t: _Client(out="やあ"))
    result = backend.translate("hi", "en", "ja")
    assert result.translated_text == "やあ"
    assert result.source_text == "hi"
    assert result.backend == "google_free"
    assert result.ok


def test_factory_receives_source_and_target():
    seen = {}

    def factory(source, target):
        seen["source"], seen["target"] = source, target
        return _Client(out="x")

    GoogleFreeTranslator(translator_factory=factory).translate("hi", "en", "ja")
    assert seen == {"source": "en", "target": "ja"}


@pytest.mark.parametrize(
    "exc",
    [
        RequestError(),
        TooManyRequests(),
        TranslationNotFound("hi"),
        NotValidLength("hi", 0, 5000),
    ],
)
def test_recoverable_library_errors_become_translation_error(exc):
    backend = GoogleFreeTranslator(translator_factory=lambda s, t: _Client(error=exc))
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")


def test_empty_result_is_translation_error():
    backend = GoogleFreeTranslator(translator_factory=lambda s, t: _Client(out=""))
    with pytest.raises(TranslationError):
        backend.translate("hi", "en", "ja")
