"""Application configuration: a validated dataclass with JSON persistence.

The config file lives in the user area (``%APPDATA%\\SnipLingo\\config.json``) and is
treated as untrusted on load: wrong types fall back to defaults, unknown keys are
ignored, and corrupt JSON never crashes the app. The optional DeepL key is masked
by :meth:`AppConfig.redacted` so it never reaches logs. See ``.claude/rules/secrets.md``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sniplingo.domain.models import Region

_MASK = "****"


@dataclass
class AppConfig:
    source_lang: str = "en"
    target_lang: str = "ja"
    select_region_hotkey: str = "<ctrl>+<alt>+r"
    default_backend: str = "google_free"
    enable_offline_fallback: bool = True
    deepl_api_key: str | None = None
    region: Region | None = None
    overlay_opacity: float = 0.85
    overlay_position: tuple[int, int] | None = None
    capture_padding: int = 8  # extra pixels grabbed around the selection so OCR keeps a margin
    ocr_scale: int = 2  # upscale factor applied before OCR; helps small/low-contrast text

    @property
    def has_deepl(self) -> bool:
        return bool(self.deepl_api_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "select_region_hotkey": self.select_region_hotkey,
            "default_backend": self.default_backend,
            "enable_offline_fallback": self.enable_offline_fallback,
            "deepl_api_key": self.deepl_api_key,
            "region": _region_to_dict(self.region),
            "overlay_opacity": self.overlay_opacity,
            "overlay_position": list(self.overlay_position) if self.overlay_position else None,
            "capture_padding": self.capture_padding,
            "ocr_scale": self.ocr_scale,
        }

    def redacted(self) -> dict[str, Any]:
        """A copy of :meth:`to_dict` safe to log: the DeepL key is masked."""
        data = self.to_dict()
        data["deepl_api_key"] = _MASK if self.has_deepl else None
        return data

    @classmethod
    def from_dict(cls, data: Any) -> AppConfig:
        """Build a config from untrusted data, falling back to defaults per field."""
        if not isinstance(data, dict):
            return cls()
        d = cls()
        return cls(
            source_lang=_as_str(data, "source_lang", d.source_lang),
            target_lang=_as_str(data, "target_lang", d.target_lang),
            select_region_hotkey=_as_str(data, "select_region_hotkey", d.select_region_hotkey),
            default_backend=_as_str(data, "default_backend", d.default_backend),
            enable_offline_fallback=_as_bool(
                data, "enable_offline_fallback", d.enable_offline_fallback
            ),
            deepl_api_key=_as_optional_str(data, "deepl_api_key"),
            region=_region_from_dict(data.get("region")),
            overlay_opacity=_as_float(data, "overlay_opacity", d.overlay_opacity),
            overlay_position=_position_from_value(data.get("overlay_position")),
            capture_padding=_as_int(data, "capture_padding", d.capture_padding),
            ocr_scale=_as_int(data, "ocr_scale", d.ocr_scale),
        )


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


# --- internal type-safe extractors -------------------------------------------------


def _as_str(data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    return value if isinstance(value, str) else default


def _as_optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def _as_bool(data: dict[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    return value if isinstance(value, bool) else default


def _as_int(data: dict[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly
        return default
    return value if isinstance(value, int) else default


def _as_float(data: dict[str, Any], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool):
        return default
    return float(value) if isinstance(value, (int, float)) else default


def _region_to_dict(region: Region | None) -> dict[str, int] | None:
    if region is None:
        return None
    return {
        "left": region.left,
        "top": region.top,
        "width": region.width,
        "height": region.height,
    }


def _position_from_value(value: Any) -> tuple[int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return (int(value[0]), int(value[1]))
        except (TypeError, ValueError):
            return None
    return None


def _region_from_dict(value: Any) -> Region | None:
    if not isinstance(value, dict):
        return None
    try:
        return Region(
            left=int(value["left"]),
            top=int(value["top"]),
            width=int(value["width"]),
            height=int(value["height"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
