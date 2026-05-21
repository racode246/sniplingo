"""Validate / normalize global-hotkey strings (pynput's ``<ctrl>+<alt>+t`` syntax).

Pure string logic — `core` must not import pynput (see `.claude/rules/architecture.md`).
A valid hotkey has exactly one non-modifier key and at least one modifier, so it's
safe to register globally.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_MODIFIERS = {"<ctrl>", "<alt>", "<shift>", "<cmd>"}
_MOD_ORDER = ["<ctrl>", "<alt>", "<shift>", "<cmd>"]
_NAMED_KEYS = {
    "<space>",
    "<enter>",
    "<tab>",
    "<esc>",
    "<backspace>",
    "<insert>",
    "<delete>",
    "<home>",
    "<end>",
    "<page_up>",
    "<page_down>",
    "<up>",
    "<down>",
    "<left>",
    "<right>",
}
_F_KEY = re.compile(r"^<f([1-9]|1[0-9]|2[0-4])>$")


class InvalidHotkeyError(ValueError):
    """Raised when a hotkey string is malformed or unsafe for a global hotkey."""


def parse_hotkey(combo: str) -> list[str]:
    """Return normalized (lowercased) tokens for `combo`, or raise InvalidHotkeyError."""
    if not isinstance(combo, str) or not combo.strip():
        raise InvalidHotkeyError("hotkey must be a non-empty string")

    parts = [part.strip().lower() for part in combo.split("+")]
    if any(not part for part in parts):
        raise InvalidHotkeyError(f"malformed hotkey: {combo!r}")

    tokens: list[str] = []
    for part in parts:
        if part in _MODIFIERS or part in _NAMED_KEYS or _F_KEY.match(part):
            tokens.append(part)
        elif len(part) == 1 and part.isprintable():
            tokens.append(part)
        else:
            raise InvalidHotkeyError(f"unknown key token: {part!r}")

    if len(tokens) != len(set(tokens)):
        raise InvalidHotkeyError(f"duplicate keys in hotkey: {combo!r}")

    keys = [t for t in tokens if t not in _MODIFIERS]
    modifiers = [t for t in tokens if t in _MODIFIERS]
    if len(keys) != 1:
        raise InvalidHotkeyError("hotkey must contain exactly one non-modifier key")
    if not modifiers:
        raise InvalidHotkeyError("hotkey must include at least one modifier")
    return tokens


def is_valid_hotkey(combo: str) -> bool:
    try:
        parse_hotkey(combo)
        return True
    except InvalidHotkeyError:
        return False


def build_hotkey(modifiers: Iterable[str], key: str) -> str:
    """Assemble a normalized, validated hotkey from primitive parts.

    `modifiers` are bare names (``ctrl``/``alt``/``shift``/``cmd``); `key` is a single
    character (``t``/``1``) or a named key (``f5``/``space``) without angle brackets.
    Modifiers are de-duplicated and emitted in canonical order. Raises
    InvalidHotkeyError for unknown modifiers or an invalid combination.
    """
    seen: set[str] = set()
    for raw in modifiers:
        token = f"<{raw.strip().lower()}>"
        if token not in _MODIFIERS:
            raise InvalidHotkeyError(f"unknown modifier: {raw!r}")
        seen.add(token)
    ordered = sorted(seen, key=_MOD_ORDER.index)

    stripped = key.strip().lower()
    key_token = stripped if len(stripped) == 1 else f"<{stripped}>"

    combo = "+".join([*ordered, key_token])
    parse_hotkey(combo)  # validate (raises InvalidHotkeyError if malformed)
    return combo
