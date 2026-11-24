"""Interactive PySide6 whiteboard canvas widget for mouse and stylus input."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import QWidget

from doodlelink.models.canvas_state import CanvasState
from doodlelink.models.coordinate import CoordinateMapper
from doodlelink.models.stroke import Stroke, ToolType


class CanvasWidget(QWidget):
    """High-performance drawing widget rendering normalized whiteboard strokes."""

    cursor_moved = Signal(float, float, float, float)  # norm_x, norm_y, widget_x, widget_y
    drawing_state_changed = Signal()

    def __init__(
        self,
        canvas_state: CanvasState | None = None,
        coord_mapper: CoordinateMapper | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.canvas_state = canvas_state or CanvasState()
        self.coord_mapper = coord_mapper or CoordinateMapper()

        # Canvas styling & colors
        self.canvas_bg_color = QColor("#FFFFFF")
        self.outer_bg_color = QColor("#1E1E2E")  # Dark modern surround for letterbox
        self.border_color = QColor("#3B4252")

        # Active drawing tool properties
        self.current_tool: ToolType = ToolType.PEN
        self.current_color: str = "#000000"
        self.pen_thickness_px: float = 4.0
        self.eraser_thickness_px: float = 24.0

        # Enable mouse tracking for coordinate readouts and cursor styling
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Wire up canvas state listener to trigger repaints and signals
        self.canvas_state.add_change_listener(self._on_state_changed)
        self._update_cursor()

    def set_canvas_state(self, new_state: CanvasState) -> None:
        """Replace the active canvas state (e.g. when switching pages)."""
        if self.canvas_state == new_state:
            return
        self.canvas_state.remove_change_listener(self._on_state_changed)
        self.canvas_state = new_state
        self.canvas_state.add_change_listener(self._on_state_changed)
        self.update()
        self.drawing_state_changed.emit()

    @property
    def active_thickness_px(self) -> float:
        """Return the pixel thickness for the currently active tool."""
        return self.eraser_thickness_px if self.current_tool == ToolType.ERASER else self.pen_thickness_px

    # --- Tool Configuration Setters ---

    def set_tool(self, tool: ToolType) -> None:
        """Switch between Pen and Eraser tools."""
        self.current_tool = tool
        self._update_cursor()
        self.drawing_state_changed.emit()

    def set_color(self, hex_color: str) -> None:
        """Set pen stroke color (hex RGB)."""
        if not hex_color.startswith("#"):
            hex_color = f"#{hex_color}"
        self.current_color = hex_color
        self.drawing_state_changed.emit()

    def set_pen_thickness(self, thickness_px: float) -> None:
        """Set pen thickness in pixels."""
        self.pen_thickness_px = max(1.0, min(100.0, float(thickness_px)))
        if self.current_tool == ToolType.PEN:
            self._update_cursor()
        self.drawing_state_changed.emit()

    def set_eraser_thickness(self, thickness_px: float) -> None:
        """Set eraser thickness in pixels."""
        self.eraser_thickness_px = max(4.0, min(200.0, float(thickness_px)))
        if self.current_tool == ToolType.ERASER:
            self._update_cursor()
        self.drawing_state_changed.emit()

    # --- Cursor Styling ---

    def _update_cursor(self) -> None:
        """Set appropriate visual cursor depending on active tool and size."""
        if self.current_tool == ToolType.ERASER:
            # Create a circular eraser cursor
            size = max(12, int(min(64, self.eraser_thickness_px)))
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor("#4C566A"), 1.5))
            painter.setBrush(QColor(255, 255, 255, 120))
            painter.drawEllipse(1, 1, size - 2, size - 2)
            painter.end()
            self.setCursor(QCursor(pixmap, size // 2, size // 2))
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    # --- Event Handlers ---

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.coord_mapper.update_widget_size(self.width(), self.height())
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            wx, wy = event.position().x(), event.position().y()
            norm_x, norm_y = self.coord_mapper.widget_to_normalized(wx, wy)
            norm_width = self.coord_mapper.pixel_to_normalized_width(self.active_thickness_px)

            color = self.current_color if self.current_tool == ToolType.PEN else "#FFFFFF"
            self.canvas_state.start_stroke(
                tool=self.current_tool,
                color=color,
                width=norm_width,
                start_x=norm_x,
                start_y=norm_y,
                pressure=1.0,
            )
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        wx, wy = event.position().x(), event.position().y()
        norm_x, norm_y = self.coord_mapper.widget_to_normalized(wx, wy)
        self.cursor_moved.emit(norm_x, norm_y, wx, wy)

        if event.buttons() & Qt.MouseButton.LeftButton and self.canvas_state.active_stroke:
            self.canvas_state.append_point(norm_x, norm_y, pressure=1.0)
            self.update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.canvas_state.active_stroke:
            self.canvas_state.finish_stroke()
            self.update()
        super().mouseReleaseEvent(event)

    def _on_state_changed(self) -> None:
        self.update()
        self.drawing_state_changed.emit()

    # --- Rendering ---

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Fill outer widget background (letterbox margins)
        painter.fillRect(self.rect(), self.outer_bg_color)

        # 2. Draw logical canvas viewport
        vp = self.coord_mapper.viewport
        canvas_rect = QRectF(vp.x, vp.y, vp.width, vp.height)

        painter.fillRect(canvas_rect, self.canvas_bg_color)
        painter.setPen(QPen(self.border_color, 1.0))
        painter.drawRect(canvas_rect)

        # 3. Clip drawing to the canvas rectangle so strokes never spill outside
        painter.setClipRect(canvas_rect)

        # 4. Render all committed strokes
        for stroke in self.canvas_state.strokes:
            self._render_stroke(painter, stroke)

        # 5. Render active stroke in progress
        if self.canvas_state.active_stroke:
            self._render_stroke(painter, self.canvas_state.active_stroke)

        painter.end()

    def _render_stroke(self, painter: QPainter, stroke: Stroke) -> None:
        if stroke.is_empty():
            return

        # Determine stroke color and pixel thickness
        if stroke.tool == ToolType.ERASER:
            color = self.canvas_bg_color
        else:
            color = QColor(stroke.color)

        pixel_width = self.coord_mapper.normalized_to_pixel_width(stroke.width)
        pen = QPen(color, pixel_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        pts = stroke.points
        if len(pts) == 1:
            # Single click -> render a dot
            wx, wy = self.coord_mapper.normalized_to_widget(pts[0].x, pts[0].y)
            painter.setBrush(color)
            r = max(1.0, pixel_width / 2.0)
            painter.drawEllipse(QPointF(wx, wy), r, r)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            return

        # Continuous gesture -> render path
        path = QPainterPath()
        start_wx, start_wy = self.coord_mapper.normalized_to_widget(pts[0].x, pts[0].y)
        path.moveTo(start_wx, start_wy)

        for pt in pts[1:]:
            wx, wy = self.coord_mapper.normalized_to_widget(pt.x, pt.y)
            path.lineTo(wx, wy)

        painter.drawPath(path)
