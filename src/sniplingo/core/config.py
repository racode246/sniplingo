"""Application configuration: an immutable, validated dataclass with JSON persistence.

The config file lives in the user area (``%APPDATA%\\SnipLingo\\config.json``) and is
treated as untrusted on load: wrong types *and* out-of-range values fall back to the
field default, unknown keys are ignored, and corrupt JSON never crashes the app.
API keys (Google Cloud / DeepL / Gemini) are masked by :meth:`AppConfig.redacted` so they
never reach logs. See ``.claude/rules/secrets.md``.

Serialization is driven by the field *types*: adding a field only needs the dataclass
line (plus an entry in ``_CONSTRAINTS`` if it has a valid range). A field whose type
has no codec fails loudly at import time.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, get_type_hints

from sniplingo.core.hotkey_parse import is_valid_hotkey
from sniplingo.domain.models import BackendName, Region

_MASK = "****"
_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True)
class AppConfig:
    source_lang: str = "en"
    target_lang: str = "ja"
    select_region_hotkey: str = "<ctrl>+<alt>+r"
    default_backend: BackendName = BackendName.GOOGLE_CLOUD
    google_cloud_api_key: str | None = None
    deepl_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = _DEFAULT_GEMINI_MODEL
    region: Region | None = None
    overlay_opacity: float = 0.85
    overlay_position: tuple[int, int] | None = None
    capture_padding: int = 8  # extra pixels grabbed around the selection so OCR keeps a margin
    ocr_scale: int = 2  # upscale factor applied before OCR; helps small/low-contrast text

    @property
    def has_google_cloud(self) -> bool:
        return bool(self.google_cloud_api_key)

    @property
    def has_deepl(self) -> bool:
        return bool(self.deepl_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    def to_dict(self) -> dict[str, Any]:
        return {f.name: _dump(getattr(self, f.name)) for f in fields(self)}

    def redacted(self) -> dict[str, Any]:
        """A copy of :meth:`to_dict` safe to log: API keys are masked."""
        data = self.to_dict()
        for name in SECRET_FIELDS:
            data[name] = _MASK if data[name] else None
        return data

    def secrets(self) -> list[str]:
        """The configured secret values (for log redaction)."""
        return [value for name in SECRET_FIELDS if (value := getattr(self, name))]

    @classmethod
    def from_dict(cls, data: Any) -> AppConfig:
        """Build a config from untrusted data, falling back to defaults per field."""
        if not isinstance(data, dict):
            return cls()
        values: dict[str, Any] = {}
        for f in fields(cls):
            if f.name not in data:
                continue
            value = _CODECS[_FIELD_TYPES[f.name]](data[f.name])
            if value is _INVALID:
                continue
            check = _CONSTRAINTS.get(f.name)
            if check is not None and not check(value):
                continue
            values[f.name] = value
        return cls(**values)


SECRET_FIELDS: tuple[str, ...] = ("google_cloud_api_key", "deepl_api_key", "gemini_api_key")


def default_config_path() -> Path:
    """Location of the user config file (``%APPDATA%\\SnipLingo\\config.json``)."""
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "SnipLingo" / "config.json"
    return Path.home() / ".sniplingo" / "config.json"


def load_config(path: str | os.PathLike[str]) -> AppConfig:
    """Load config from `path`. Missing file or corrupt JSON yields defaults."""
    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError):
        return AppConfig()
    return AppConfig.from_dict(data)


def save_config(config: AppConfig, path: str | os.PathLike[str]) -> None:
    """Persist config to `path` (creating parent directories)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


# --- per-type codecs ---------------------------------------------------------------

_INVALID = object()  # sentinel: the raw value can't be converted to the field type


def _parse_str(raw: Any) -> Any:
    return raw if isinstance(raw, str) else _INVALID


def _parse_optional_str(raw: Any) -> Any:
    return raw if raw is None or isinstance(raw, str) else _INVALID


def _parse_bool(raw: Any) -> Any:
    return raw if isinstance(raw, bool) else _INVALID


def _parse_int(raw: Any) -> Any:
    # bool is an int subclass; reject it explicitly
    return raw if isinstance(raw, int) and not isinstance(raw, bool) else _INVALID


def _parse_float(raw: Any) -> Any:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return _INVALID
    return float(raw)


def _parse_backend(raw: Any) -> Any:
    try:
        return BackendName(raw)
    except ValueError:
        return _INVALID


def _parse_region(raw: Any) -> Any:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return _INVALID
    try:
        return Region(
            left=int(raw["left"]),
            top=int(raw["top"]),
            width=int(raw["width"]),
            height=int(raw["height"]),
        )
    except (KeyError, TypeError, ValueError):
        return _INVALID


def _parse_position(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        try:
            return (int(raw[0]), int(raw[1]))
        except (TypeError, ValueError):
            return _INVALID
    return _INVALID


def _dump(value: Any) -> Any:
    if isinstance(value, Region):
        return {"left": value.left, "top": value.top, "width": value.width, "height": value.height}
    if isinstance(value, tuple):
        return list(value)
    return value


_CODECS: dict[Any, Callable[[Any], Any]] = {
    str: _parse_str,
    str | None: _parse_optional_str,
    bool: _parse_bool,
    int: _parse_int,
    float: _parse_float,
    BackendName: _parse_backend,
    Region | None: _parse_region,
    tuple[int, int] | None: _parse_position,
}


def _nonblank(value: str) -> bool:
    return bool(value.strip())


# Valid ranges for fields whose type alone is not enough.
_CONSTRAINTS: dict[str, Callable[[Any], bool]] = {
    "source_lang": _nonblank,
    "target_lang": _nonblank,
    "gemini_model": _nonblank,
    "select_region_hotkey": is_valid_hotkey,
    "region": lambda region: region is None or not region.is_empty,
    "overlay_opacity": lambda v: 0.1 <= v <= 1.0,
    "capture_padding": lambda v: 0 <= v <= 64,
    "ocr_scale": lambda v: 1 <= v <= 4,
}

_FIELD_TYPES: dict[str, Any] = get_type_hints(AppConfig)
_missing = {name for name, tp in _FIELD_TYPES.items() if tp not in _CODECS}
if _missing:  # pragma: no cover - guards future edits
    raise TypeError(f"AppConfig fields without a codec: {sorted(_missing)}")
