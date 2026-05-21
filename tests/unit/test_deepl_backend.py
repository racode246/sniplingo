import pytest
from deep_translator.exceptions import RequestError

from sniplingo.adapters.deepl_backend import DeepLTranslator
from sniplingo.domain.errors import TranslationError


class _Client:
    def __init__(self, out=None, error=None):
        self._out = out
        self._error = error

    def translate(self, text):
        if self._error is not None:
            raise self._error
        return self._out


def test_requires_non_empty_api_key():
    with pytest.raises(ValueError):
        DeepLTranslator(api_key="")


def test_success_returns_translation_result():
    backend = DeepLTranslator(api_key="k", deepl_factory=lambda key, s, t: _Client(out="やあ"))
    result = backend.translate("hi", "en", "ja")
    assert result.translated_text == "やあ"
    assert result.backend == "deepl"


def test_factory_receives_key_source_target():
    seen = {}

    def factory(key, source, target):
        seen.update(key=key, source=source, target=target)
        return _Client(out="x")

    DeepLTranslator(api_key="secret", deepl_factory=factory).translate("hi", "en", "ja")
    assert seen == {"key": "secret", "source": "en", "target": "ja"}


def test_error_becomes_translation_error_without_leaking_key():
    backend = DeepLTranslator(
        api_key="super-secret-key",
        deepl_factory=lambda key, s, t: _Client(error=RequestError()),
    )
    with pytest.raises(TranslationError) as exc_info:
        backend.translate("hi", "en", "ja")
    assert "super-secret-key" not in str(exc_info.value)
