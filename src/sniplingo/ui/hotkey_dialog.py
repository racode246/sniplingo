"""Modal dialog that captures a new global hotkey by pressing the keys.

Qt key/modifier -> token translation lives here (UI layer); the validated assembly
into a pynput combo string is delegated to `core.hotkey_parse.build_hotkey`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from sniplingo.core.hotkey_parse import InvalidHotkeyError, build_hotkey

_PURE_MODIFIER_KEYS = {
    Qt.Key.Key_Control.value,
    Qt.Key.Key_Alt.value,
    Qt.Key.Key_AltGr.value,
    Qt.Key.Key_Shift.value,
    Qt.Key.Key_Meta.value,
}
_NAMED_KEYS = {
    Qt.Key.Key_Space.value: "space",
    Qt.Key.Key_Return.value: "enter",
    Qt.Key.Key_Enter.value: "enter",
    Qt.Key.Key_Tab.value: "tab",
}


def qt_modifiers_to_names(modifiers: Qt.KeyboardModifier) -> list[str]:
    names = []
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        names.append("ctrl")
    if modifiers & Qt.KeyboardModifier.AltModifier:
        names.append("alt")
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        names.append("shift")
    if modifiers & Qt.KeyboardModifier.MetaModifier:
        names.append("cmd")
    return names


def qt_key_to_token(key: int, text: str) -> str | None:
    """Map a Qt key (int) + its text to a build_hotkey key token, or None if unusable."""
    key = int(key)
    if Qt.Key.Key_F1.value <= key <= Qt.Key.Key_F24.value:
        return f"f{key - Qt.Key.Key_F1.value + 1}"
    if key in _NAMED_KEYS:
        return _NAMED_KEYS[key]
    if text and len(text) == 1 and text.isprintable() and not text.isspace():
        return text.lower()
    return None


class HotkeyCaptureDialog(QDialog):
    def __init__(self, current: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ショートカットを設定")
        self.setModal(True)
        self._combo: str | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("新しいショートカットを押してください（修飾キー + 1 キー）"))
        self._preview = QLabel(f"現在: {current}" if current else "（未設定）")
        layout.addWidget(self._preview)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok.setEnabled(False)
        self._ok.setAutoDefault(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt override
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
            return
        if int(key) in _PURE_MODIFIER_KEYS:
            return  # wait for the non-modifier key
        token = qt_key_to_token(key, event.text())
        if token is None:
            return
        try:
            self._combo = build_hotkey(qt_modifiers_to_names(event.modifiers()), token)
        except InvalidHotkeyError:
            self._combo = None
            self._preview.setText("修飾キー(Ctrl/Alt/Shift)を1つ以上含めてください")
            self._ok.setEnabled(False)
            return
        self._preview.setText(self._combo)
        self._ok.setEnabled(True)

    def hotkey(self) -> str | None:
        """The captured combo (e.g. ``<ctrl>+<alt>+t``), or None if nothing valid."""
        return self._combo
