"""Which backends run, in which order — decided from config alone (no adapters here)."""

import pytest

from sniplingo.core.backend_plan import BackendPlan, plan_backends
from sniplingo.core.config import AppConfig
from sniplingo.domain.models import BackendName

G = BackendName.GOOGLE_FREE
D = BackendName.DEEPL
M = BackendName.GEMINI


def test_default_config_is_google_only():
    assert plan_backends(AppConfig()) == BackendPlan(vision=None, text=(G,))


def test_deepl_key_becomes_a_fallback_after_google():
    config = AppConfig(deepl_api_key="d")
    assert plan_backends(config) == BackendPlan(vision=None, text=(G, D))


@pytest.mark.parametrize("primary", [G, D])
def test_gemini_is_never_a_fallback(primary):
    """Gemini runs only when chosen as the default — a configured key alone doesn't enlist it."""
    config = AppConfig(default_backend=primary, deepl_api_key="d", gemini_api_key="g")
    plan = plan_backends(config)
    assert plan.vision is None
    assert M not in plan.text


def test_keyed_primary_goes_first():
    config = AppConfig(default_backend=D, deepl_api_key="d")
    assert plan_backends(config).text == (D, G)


@pytest.mark.parametrize("primary", [D, M])
def test_keyed_primary_without_key_falls_back_to_google(primary):
    plan = plan_backends(AppConfig(default_backend=primary))
    assert plan == BackendPlan(vision=None, text=(G,))


def test_gemini_primary_uses_vision_and_is_excluded_from_text_path():
    """The text chain is Vision's fallback — re-trying Gemini would hit the same limit."""
    config = AppConfig(default_backend=M, gemini_api_key="g", deepl_api_key="d")
    assert plan_backends(config) == BackendPlan(vision=M, text=(G, D))


def test_text_path_never_contains_duplicates():
    config = AppConfig(default_backend=G, gemini_api_key="g")
    text = plan_backends(config).text
    assert len(text) == len(set(text))
