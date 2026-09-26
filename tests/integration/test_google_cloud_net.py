"""Real Google Cloud Translation call. Needs network and an API key in the environment
(never in the repo): $env:SNIPLINGO_GOOGLE_CLOUD_API_KEY = "..."
Run with: pytest tests/integration -m network"""

import os

import pytest

from sniplingo.adapters.google_cloud_backend import GoogleCloudTranslator

pytestmark = pytest.mark.network


@pytest.fixture
def api_key() -> str:
    key = os.environ.get("SNIPLINGO_GOOGLE_CLOUD_API_KEY")
    if not key:
        pytest.skip("SNIPLINGO_GOOGLE_CLOUD_API_KEY not set")
    return key


def test_translate_hello_en_to_ja_returns_text(api_key):
    result = GoogleCloudTranslator(api_key).translate("Hello", "en", "ja")
    assert result.ok
    assert result.translated_text  # some Japanese text came back
    assert result.backend == "google_cloud"


def test_one_translated_row_per_input_row(api_key):
    # Live, the API turned "Save your game.\nQuit" into "...\n\n..."; the adapter drops that.
    source = "Save your game.\nQuit\nQuality: +20%"
    result = GoogleCloudTranslator(api_key).translate(source, "en", "ja")
    assert len(result.translated_text.split("\n")) == 3
