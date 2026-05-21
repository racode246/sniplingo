"""Translucent, always-on-top window that shows the translation.

Interactive (not click-through) so the user can drag it to reposition and close it.
It does not steal focus from the game on show (WA_ShowWithoutActivating); it only
captures mouse events within its small box. Drag end emits `moved` so the position
can be persisted and reused next time.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

_CLOSE_SIZE = 18
_CLOSE_MARGIN = 6
_TOP_MARGIN = _CLOSE_MARGIN + _CLOSE_SIZE + 4  # reserve a row for the × so text never overlaps it
_FONT_PX = 16  # overlay font is fixed at 16px


class OverlayWindow(QWidget):
    moved = Signal(int, int)  # new top-left (x, y) after the user drags the box

    def __init__(self, opacity: float = 0.85) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # keep it off the taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)  # don't steal focus
        self.setMouseTracking(True)
        self._text = ""
        self._bg_alpha = max(0, min(255, int(opacity * 255)))
        self._padding = 12
        self._font = QFont()
        self._font.setPixelSize(_FONT_PX)
        self._dragging = False
        self._drag_offset = QPoint()

    def show_translation(
        self, text: str, anchor: QRect, position: tuple[int, int] | None = None
    ) -> None:
        """Show `text`. Use the saved `position` if given, else anchor below `anchor`."""
        self._text = text
        width, height = self._content_size(text, anchor)

        if position is not None:
            origin = QPoint(*position)
        else:
            origin = QPoint(anchor.left(), anchor.bottom() + 8)

        screen = QGuiApplication.screenAt(origin) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        x, y = origin.x(), origin.y()
        if position is None and y + height > avail.bottom():
            y = anchor.top() - 8 - height  # not enough room below -> place above
        x = max(avail.left(), min(x, avail.right() - width))
        y = max(avail.top(), min(y, avail.bottom() - height))

        self.setGeometry(x, y, width, height)
        self.update()
        self.show()
        self.raise_()

    def _content_size(self, text: str, anchor: QRect) -> tuple[int, int]:
        max_w = min(max(anchor.width(), 240), 640)
        metrics = QFontMetrics(self._font)
        text_rect = metrics.boundingRect(
            QRect(0, 0, max_w - 2 * self._padding, 100_000),
            Qt.TextFlag.TextWordWrap,
            text,
        )
        min_width = _CLOSE_SIZE + 2 * _CLOSE_MARGIN + 2 * self._padding
        width = max(text_rect.width() + 2 * self._padding, min_width)
        height = text_rect.height() + _TOP_MARGIN + self._padding
        return width, height

    def _close_rect(self) -> QRect:
        return QRect(
            self.width() - _CLOSE_SIZE - _CLOSE_MARGIN, _CLOSE_MARGIN, _CLOSE_SIZE, _CLOSE_SIZE
        )

    # --- interaction -------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.RightButton:
            self.hide()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._close_rect().contains(event.position().toPoint()):
            self.hide()
            return
        self._dragging = True
        self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._dragging:
            self._dragging = False
            self.moved.emit(self.x(), self.y())

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()

    # --- painting ----------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, self._bg_alpha))
        painter.drawRoundedRect(self.rect(), 8, 8)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(self._font)
        painter.drawText(
            self.rect().adjusted(self._padding, _TOP_MARGIN, -self._padding, -self._padding),
            int(Qt.TextFlag.TextWordWrap),
            self._text,
        )

        # close button: a bare × glyph in the top-right corner (no background)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self._close_rect(), int(Qt.AlignmentFlag.AlignCenter), "×")
