"""Real network translation (Google free endpoint). Flaky by nature.
Run with: pytest tests/integration -m network"""

import pytest

from sniplingo.adapters.deep_translator_backend import GoogleFreeTranslator

pytestmark = pytest.mark.network


def test_translate_hello_en_to_ja_returns_text():
    result = GoogleFreeTranslator().translate("Hello", "en", "ja")
    assert result.ok
    assert result.translated_text  # some Japanese text came back
    assert result.backend == "google_free"
