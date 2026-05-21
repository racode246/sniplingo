import pytest

from sniplingo.adapters.argos_backend import ArgosTranslator
from sniplingo.domain.errors import TranslationError


def test_success_returns_translation_result():
    backend = ArgosTranslator(translate_fn=lambda text, s, t: "やあ(offline)")
    result = backend.translate("hi", "en", "ja")
    assert result.translated_text == "やあ(offline)"
    assert result.backend == "argos"
    assert result.ok


def test_translate_fn_receives_text_source_target():
    seen = {}

    def fn(text, source, target):
        seen.update(text=text, source=source, target=target)
        return "x"

    ArgosTranslator(translate_fn=fn).translate("hi", "en", "ja")
    assert seen == {"text": "hi", "source": "en", "target": "ja"}


def test_backend_error_becomes_translation_error():
    def fn(text, source, target):
        raise RuntimeError("offline model not installed")

    with pytest.raises(TranslationError):
        ArgosTranslator(translate_fn=fn).translate("hi", "en", "ja")


def test_empty_result_is_translation_error():
    with pytest.raises(TranslationError):
        ArgosTranslator(translate_fn=lambda *a: "").translate("hi", "en", "ja")
