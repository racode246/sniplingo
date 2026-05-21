"""System-tray icon and menu — the app's main control surface."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def _make_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(0, 120, 215))
    painter.setPen(QColor(255, 255, 255))
    painter.drawRoundedRect(2, 2, 60, 60, 12, 12)
    font = QFont()
    font.setPointSize(28)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "訳")
    painter.end()
    return QIcon(pixmap)


class Tray(QObject):
    select_region_requested = Signal()
    translate_now_requested = Signal()
    set_hotkey_requested = Signal()
    quit_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._tray = QSystemTrayIcon(_make_icon())
        self._tray.setToolTip("SnipLingo — ゲーム翻訳オーバーレイ")

        menu = QMenu()
        menu.addAction("範囲を選択して翻訳", self.select_region_requested.emit)
        menu.addAction("現在の範囲を再翻訳", self.translate_now_requested.emit)
        menu.addAction("範囲選択のショートカットを設定…", self.set_hotkey_requested.emit)
        menu.addSeparator()
        self._status: QAction = menu.addAction("バックエンド: -")
        self._status.setEnabled(False)
        menu.addSeparator()
        menu.addAction("終了", self.quit_requested.emit)

        self._tray.setContextMenu(menu)
        self._tray.show()

    def set_status(self, text: str) -> None:
        self._status.setText(f"バックエンド: {text}")

    def notify(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, _make_icon(), 4000)
