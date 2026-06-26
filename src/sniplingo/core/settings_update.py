"""Pure mapping from a settings-dialog form to an updated :class:`AppConfig`.

Kept out of ``ui/`` so the rule ("blank input = no change, clear flag = set to None,
typed input = overwrite") is unit-testable without PySide6. The dialog only collects
values into :class:`SettingsForm` and hands them to :func:`apply_settings`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from sniplingo.core.config import AppConfig


@dataclass(frozen=True)
class SettingsForm:
    """Values captured from the translation-settings dialog.

    Secret inputs follow a three-state rule: blank+no-clear means "keep what's
    saved", a non-empty string overwrites, and ``*_clear=True`` explicitly sets
    the saved key to ``None`` (clear wins over a typed value).
    """

    default_backend: str
    enable_offline_fallback: bool
    deepl_key_input: str
    deepl_clear: bool
    gemini_key_input: str
    gemini_clear: bool
    gemini_model: str

    @classmethod
    def from_config(cls, config: AppConfig) -> SettingsForm:
        """Seed the form from the current config (secret inputs always start blank)."""
        return cls(
            default_backend=config.default_backend,
            enable_offline_fallback=config.enable_offline_fallback,
            deepl_key_input="",
            deepl_clear=False,
            gemini_key_input="",
            gemini_clear=False,
            gemini_model=config.gemini_model,
        )


def apply_settings(config: AppConfig, form: SettingsForm) -> AppConfig:
    """Return a new config with the form's values applied (input is not mutated)."""
    return replace(
        config,
        default_backend=form.default_backend,
        enable_offline_fallback=form.enable_offline_fallback,
        deepl_api_key=_resolve_key(config.deepl_api_key, form.deepl_key_input, form.deepl_clear),
        gemini_api_key=_resolve_key(
            config.gemini_api_key, form.gemini_key_input, form.gemini_clear
        ),
        gemini_model=form.gemini_model.strip() or config.gemini_model,
    )


def _resolve_key(current: str | None, typed: str, clear: bool) -> str | None:
    if clear:
        return None
    if typed:
        return typed
    return current
