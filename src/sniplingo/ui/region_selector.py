"""Full-virtual-desktop drag-to-select overlay that emits a capture Region.

Widget-local coordinates are offset by the virtual desktop's top-left (which can be
negative on multi-monitor setups) to produce global coords that `mss` understands.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sniplingo.domain.geometry import region_from_points


class RegionSelector(QWidget):
    selected = Signal(object)  # Region (global / virtual-desktop coords)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._origin = None
        self._current = None
        self._offset = (0, 0)  # virtual-desktop top-left

    def start(self) -> None:
        vg = QGuiApplication.primaryScreen().virtualGeometry()
        self._offset = (vg.left(), vg.top())
        self.setGeometry(vg)
        self._origin = None
        self._current = None
        self.show()
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._origin = event.position().toPoint()
        self._current = self._origin
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._origin is None:
            return
        end = event.position().toPoint()
        ox, oy = self._offset
        region = region_from_points(
            (self._origin.x() + ox, self._origin.y() + oy),
            (end.x() + ox, end.y() + oy),
        )
        self._origin = None
        self._current = None
        self.hide()
        if region.is_empty:
            self.cancelled.emit()
        else:
            self.selected.emit(region)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._origin = None
            self._current = None
            self.hide()
            self.cancelled.emit()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))  # dim the whole desktop
        if self._origin is not None and self._current is not None:
            sel = QRect(self._origin, self._current).normalized()
            # punch a clear hole so the user sees what they're selecting
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(sel, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(0, 180, 255), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(sel)
