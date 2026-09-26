"""Which backends run, in which order — decided from config alone (no adapters here)."""

import pytest

from sniplingo.core.backend_plan import BackendPlan, plan_backends
from sniplingo.core.config import AppConfig
from sniplingo.domain.models import BackendName

C = BackendName.GOOGLE_CLOUD
D = BackendName.DEEPL
M = BackendName.GEMINI


def test_without_any_key_nothing_can_run():
    """Every backend is keyed now; the UI asks for a key instead of translating."""
    plan = plan_backends(AppConfig())
    assert plan == BackendPlan(vision=None, text=())
    assert plan.is_empty


def test_google_cloud_with_key_is_the_default_path():
    plan = plan_backends(AppConfig(google_cloud_api_key="c"))
    assert plan == BackendPlan(vision=None, text=(C,))
    assert not plan.is_empty


def test_deepl_key_becomes_a_fallback_after_google_cloud():
    config = AppConfig(google_cloud_api_key="c", deepl_api_key="d")
    assert plan_backends(config).text == (C, D)


def test_keyed_primary_goes_first():
    config = AppConfig(default_backend=D, deepl_api_key="d", google_cloud_api_key="c")
    assert plan_backends(config).text == (D, C)


def test_primary_without_key_falls_back_to_the_next_usable_one():
    config = AppConfig(default_backend=D, google_cloud_api_key="c")
    assert plan_backends(config) == BackendPlan(vision=None, text=(C,))


@pytest.mark.parametrize("primary", [C, D])
def test_gemini_is_never_a_fallback(primary):
    """Gemini runs only when chosen as the default — a configured key alone doesn't enlist it."""
    config = AppConfig(
        default_backend=primary, google_cloud_api_key="c", deepl_api_key="d", gemini_api_key="g"
    )
    plan = plan_backends(config)
    assert plan.vision is None
    assert M not in plan.text


def test_gemini_primary_uses_vision_and_is_excluded_from_text_path():
    """The text chain is Vision's fallback — re-trying Gemini would hit the same limit."""
    config = AppConfig(default_backend=M, gemini_api_key="g", google_cloud_api_key="c")
    assert plan_backends(config) == BackendPlan(vision=M, text=(C,))


def test_gemini_vision_alone_is_a_runnable_plan():
    plan = plan_backends(AppConfig(default_backend=M, gemini_api_key="g"))
    assert plan == BackendPlan(vision=M, text=())
    assert not plan.is_empty


def test_text_path_never_contains_duplicates():
    config = AppConfig(default_backend=C, google_cloud_api_key="c", deepl_api_key="d")
    text = plan_backends(config).text
    assert len(text) == len(set(text))
