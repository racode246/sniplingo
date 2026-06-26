"""Tests for the pure form-values -> AppConfig update rule (no PySide6 here)."""

from sniplingo.core.config import AppConfig
from sniplingo.core.settings_update import SettingsForm, apply_settings


def _form(**kw) -> SettingsForm:
    """Build a form with all fields explicit; tests override what they care about."""
    defaults = dict(
        default_backend="google_free",
        enable_offline_fallback=True,
        deepl_key_input="",
        deepl_clear=False,
        gemini_key_input="",
        gemini_clear=False,
        gemini_model="gemini-2.5-flash",
    )
    defaults.update(kw)
    return SettingsForm(**defaults)


def test_blank_inputs_keep_existing_keys():
    base = AppConfig(deepl_api_key="old-deepl", gemini_api_key="old-gemini")
    out = apply_settings(base, _form())
    assert out.deepl_api_key == "old-deepl"
    assert out.gemini_api_key == "old-gemini"


def test_typed_input_overwrites_existing_key():
    base = AppConfig(deepl_api_key="old-deepl", gemini_api_key="old-gemini")
    out = apply_settings(base, _form(deepl_key_input="new-deepl", gemini_key_input="new-gemini"))
    assert out.deepl_api_key == "new-deepl"
    assert out.gemini_api_key == "new-gemini"


def test_clear_flag_sets_key_to_none():
    base = AppConfig(deepl_api_key="old-deepl", gemini_api_key="old-gemini")
    out = apply_settings(base, _form(deepl_clear=True, gemini_clear=True))
    assert out.deepl_api_key is None
    assert out.gemini_api_key is None


def test_clear_wins_over_typed_input():
    """If user typed and then hit clear, clearing is the explicit intent."""
    base = AppConfig(deepl_api_key="old")
    out = apply_settings(base, _form(deepl_key_input="ignored", deepl_clear=True))
    assert out.deepl_api_key is None


def test_default_backend_and_offline_fallback_are_replaced():
    base = AppConfig(default_backend="google_free", enable_offline_fallback=True)
    out = apply_settings(base, _form(default_backend="gemini", enable_offline_fallback=False))
    assert out.default_backend == "gemini"
    assert out.enable_offline_fallback is False


def test_gemini_model_overrides_when_nonblank():
    base = AppConfig(gemini_model="gemini-2.5-flash")
    out = apply_settings(base, _form(gemini_model="gemini-2.5-pro"))
    assert out.gemini_model == "gemini-2.5-pro"


def test_blank_gemini_model_keeps_existing():
    """A blank input must not clobber the saved model (treat as 'no change')."""
    base = AppConfig(gemini_model="gemini-2.5-flash-lite")
    out = apply_settings(base, _form(gemini_model="   "))
    assert out.gemini_model == "gemini-2.5-flash-lite"


def test_unrelated_fields_are_preserved():
    """The update is targeted — region/overlay/hotkey survive untouched."""
    from sniplingo.domain.models import Region

    base = AppConfig(
        region=Region(1, 2, 3, 4),
        overlay_position=(50, 60),
        select_region_hotkey="<ctrl>+<shift>+t",
        overlay_opacity=0.5,
    )
    out = apply_settings(base, _form())
    assert out.region == Region(1, 2, 3, 4)
    assert out.overlay_position == (50, 60)
    assert out.select_region_hotkey == "<ctrl>+<shift>+t"
    assert out.overlay_opacity == 0.5


def test_returns_new_instance_without_mutating_input():
    base = AppConfig(deepl_api_key="orig")
    out = apply_settings(base, _form(deepl_key_input="changed"))
    assert base.deepl_api_key == "orig"  # input unchanged
    assert out.deepl_api_key == "changed"
    assert out is not base


def test_from_existing_helper_seeds_form_with_current_values():
    """The dialog calls this to pre-fill non-secret fields (model, backend, ...)."""
    base = AppConfig(
        default_backend="gemini",
        enable_offline_fallback=False,
        gemini_model="gemini-2.5-flash-lite",
    )
    form = SettingsForm.from_config(base)
    assert form.default_backend == "gemini"
    assert form.enable_offline_fallback is False
    assert form.gemini_model == "gemini-2.5-flash-lite"
    # Secrets are never pre-filled, even when set.
    assert form.deepl_key_input == ""
    assert form.gemini_key_input == ""
    assert form.deepl_clear is False
    assert form.gemini_clear is False
