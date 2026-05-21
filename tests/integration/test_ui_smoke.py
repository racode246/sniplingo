"""Qt UI smoke tests. Run with: pytest tests/integration -m qt
Headless: set QT_QPA_PLATFORM=offscreen first."""

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from sniplingo.domain.models import Region
from sniplingo.ui.hotkey import GlobalHotkey, HotkeyBridge
from sniplingo.ui.hotkey_dialog import HotkeyCaptureDialog, qt_key_to_token
from sniplingo.ui.overlay_window import OverlayWindow
from sniplingo.ui.region_selector import RegionSelector

pytestmark = pytest.mark.qt


def test_hotkey_bridge_emits(qtbot):
    bridge = HotkeyBridge()
    with qtbot.waitSignal(bridge.triggered, timeout=1000):
        bridge.triggered.emit()


def test_overlay_anchors_below_region_when_no_saved_position(qtbot):
    window = OverlayWindow(0.8)
    qtbot.addWidget(window)
    window.show_translation("テスト訳です", QRect(100, 100, 200, 40))
    assert window.width() > 0
    assert window.height() > 0


def test_overlay_uses_saved_position(qtbot):
    window = OverlayWindow(0.8)
    qtbot.addWidget(window)
    window.show_translation("テスト訳", QRect(0, 0, 200, 40), position=(60, 50))
    assert (window.x(), window.y()) == (60, 50)


def test_overlay_emits_moved_after_drag(qtbot):
    window = OverlayWindow(0.8)
    qtbot.addWidget(window)
    window.show_translation("テスト翻訳テキスト", QRect(0, 0, 200, 40), position=(100, 100))
    press = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        QPointF(110, 110),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.mousePressEvent(press)
    move = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(90, 80),
        QPointF(190, 170),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.mouseMoveEvent(move)
    release = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(90, 80),
        QPointF(190, 170),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(window.moved, timeout=1000) as blocker:
        window.mouseReleaseEvent(release)
    assert blocker.args == [180, 160]


def test_overlay_close_button_hides(qtbot):
    window = OverlayWindow(0.8)
    qtbot.addWidget(window)
    window.show_translation("テスト翻訳テキスト", QRect(0, 0, 200, 40), position=(100, 100))
    assert window.isVisible()
    center = window._close_rect().center()
    press = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(center),
        QPointF(100 + center.x(), 100 + center.y()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.mousePressEvent(press)
    assert not window.isVisible()


def test_region_selector_emits_global_region(qtbot):
    selector = RegionSelector()
    qtbot.addWidget(selector)
    selector._offset = (-1920, -10)  # simulate a monitor left/above the primary
    selector._origin = QPoint(30, 40)
    selector._current = QPoint(130, 110)
    release = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(130, 110),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(selector.selected, timeout=1000) as blocker:
        selector.mouseReleaseEvent(release)
    assert blocker.args[0] == Region(left=-1890, top=30, width=100, height=70)


def test_region_selector_escape_cancels(qtbot):
    selector = RegionSelector()
    qtbot.addWidget(selector)
    selector._origin = QPoint(0, 0)
    selector._current = QPoint(5, 5)
    escape = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    with qtbot.waitSignal(selector.cancelled, timeout=1000):
        selector.keyPressEvent(escape)


def test_qt_key_to_token_handles_letters_and_function_keys():
    assert qt_key_to_token(int(Qt.Key.Key_T), "t") == "t"
    assert qt_key_to_token(int(Qt.Key.Key_T), "T") == "t"
    assert qt_key_to_token(int(Qt.Key.Key_F5), "") == "f5"
    assert qt_key_to_token(int(Qt.Key.Key_Control), "") is None


def test_hotkey_dialog_captures_modifier_plus_key(qtbot):
    dialog = HotkeyCaptureDialog("<ctrl>+<alt>+t")
    qtbot.addWidget(dialog)
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_J,
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
        "j",
    )
    dialog.keyPressEvent(event)
    assert dialog.hotkey() == "<ctrl>+<shift>+j"


def test_hotkey_dialog_rejects_key_without_modifier(qtbot):
    dialog = HotkeyCaptureDialog()
    qtbot.addWidget(dialog)
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_T, Qt.KeyboardModifier.NoModifier, "t")
    dialog.keyPressEvent(event)
    assert dialog.hotkey() is None


def test_global_hotkey_set_combo_validates(qtbot):
    hotkey = GlobalHotkey("<ctrl>+<alt>+t")
    hotkey.set_combo("<ctrl>+<shift>+j")
    assert hotkey.combo == "<ctrl>+<shift>+j"
    with pytest.raises(ValueError):
        hotkey.set_combo("nope")
