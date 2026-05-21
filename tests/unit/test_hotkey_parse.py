import pytest

from sniplingo.core.hotkey_parse import (
    InvalidHotkeyError,
    build_hotkey,
    is_valid_hotkey,
    parse_hotkey,
)


@pytest.mark.parametrize(
    "combo",
    [
        "<ctrl>+<alt>+t",
        "<ctrl>+<shift>+<f5>",
        "<alt>+x",
        "<ctrl>+1",
        "<cmd>+<shift>+q",
    ],
)
def test_valid_hotkeys(combo):
    assert is_valid_hotkey(combo)


@pytest.mark.parametrize(
    "combo",
    [
        "",  # empty
        "   ",  # blank
        "<ctrl>+",  # trailing plus
        "+t",  # leading plus
        "<ctrl>++t",  # empty token
        "<ctrl>+<alt>",  # no non-modifier key
        "<ctrl>+t+x",  # two non-modifier keys
        "<ctrl>+<bogus>",  # unknown named key
        "t",  # no modifier (unsafe as a global hotkey)
        "<f5>",  # no modifier
    ],
)
def test_invalid_hotkeys(combo):
    assert not is_valid_hotkey(combo)


def test_parse_normalizes_case_and_returns_tokens():
    assert parse_hotkey("<Ctrl>+<Alt>+T") == ["<ctrl>", "<alt>", "t"]


def test_parse_raises_on_invalid():
    with pytest.raises(InvalidHotkeyError):
        parse_hotkey("nope+")


def test_parse_rejects_non_string():
    with pytest.raises(InvalidHotkeyError):
        parse_hotkey(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "modifiers,key,expected",
    [
        (["ctrl", "alt"], "t", "<ctrl>+<alt>+t"),
        (["alt", "ctrl"], "t", "<ctrl>+<alt>+t"),  # canonical modifier order
        (["ctrl"], "f5", "<ctrl>+<f5>"),  # named key token
        (["ctrl", "shift"], "1", "<ctrl>+<shift>+1"),
        (["ctrl", "ctrl"], "t", "<ctrl>+t"),  # duplicate modifiers collapsed
        (["CTRL", "Alt"], "T", "<ctrl>+<alt>+t"),  # case-insensitive
    ],
)
def test_build_hotkey(modifiers, key, expected):
    assert build_hotkey(modifiers, key) == expected


@pytest.mark.parametrize(
    "modifiers,key",
    [
        ([], "t"),  # no modifier -> unsafe global hotkey
        (["ctrl"], ""),  # empty key
        (["ctrl"], "ab"),  # multi-char, not a known named key
        (["bogus"], "t"),  # unknown modifier
    ],
)
def test_build_hotkey_invalid(modifiers, key):
    with pytest.raises(InvalidHotkeyError):
        build_hotkey(modifiers, key)
