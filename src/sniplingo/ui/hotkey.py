"""Global hotkey via pynput, bridged to Qt with a thread-safe signal.

pynput callbacks run on the OS input thread and must NEVER block (that would freeze
input system-wide). The callback only emits a Qt signal; the heavy work is dispatched
on the GUI thread via a queued connection. See CLAUDE.md (thread model).
"""

from __future__ import annotations

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

from sniplingo.core.hotkey_parse import is_valid_hotkey


class HotkeyBridge(QObject):
    triggered = Signal()


class GlobalHotkey:
    def __init__(self, combo: str) -> None:
        if not is_valid_hotkey(combo):
            raise ValueError(f"invalid hotkey: {combo!r}")
        self._combo = combo
        self.bridge = HotkeyBridge()
        self._listener: keyboard.GlobalHotKeys | None = None

    def set_combo(self, combo: str) -> None:
        """Validate and store a new combo. Call `start()` to (re)register it."""
        if not is_valid_hotkey(combo):
            raise ValueError(f"invalid hotkey: {combo!r}")
        self._combo = combo

    @property
    def combo(self) -> str:
        return self._combo

    def start(self) -> None:
        self.stop()  # idempotent: drop any previous listener first
        self._listener = keyboard.GlobalHotKeys({self._combo: self._on_activate})
        self._listener.start()

    def _on_activate(self) -> None:
        # Input thread: emit only, return immediately.
        self.bridge.triggered.emit()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
