"""Export utilities for DoodleLink whiteboard pages and multi-page boards."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QPageSize,
    QPainter,
    QPainterPath,
    QPdfWriter,
    QPen,
)

from doodlelink.models.coordinate import CoordinateMapper
from doodlelink.models.stroke import Stroke, ToolType

if TYPE_CHECKING:
    from doodlelink.models.canvas_state import CanvasState
    from doodlelink.models.multi_page import MultiPageDocument

logger = logging.getLogger("doodlelink.export")


def render_strokes(
    painter: QPainter,
    strokes: list[Stroke],
    width: int,
    height: int,
    background_color: str | None = "#FFFFFF",
) -> None:
    """Render a list of normalized strokes to an active QPainter.

    Args:
        painter: Active QPainter on target device (image or PDF).
        strokes: Ordered list of strokes to render.
        width: Device width in pixels/points.
        height: Device height in pixels/points.
        background_color: Hex color string (e.g. '#FFFFFF') or None for transparent.
    """
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    coord_mapper = CoordinateMapper()
    coord_mapper.update_widget_size(width, height)
    vp = coord_mapper.viewport
    canvas_rect = QRectF(vp.x, vp.y, vp.width, vp.height)

    # Fill background if specified
    if background_color is not None:
        painter.fillRect(canvas_rect, QColor(background_color))

    painter.setClipRect(canvas_rect)

    for stroke in strokes:
        if stroke.is_empty():
            continue

        is_eraser = stroke.tool == ToolType.ERASER

        if is_eraser:
            if background_color is None:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                color = QColor(0, 0, 0, 255)
            else:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                color = QColor(background_color)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            color = QColor(stroke.color)

        pixel_width = max(1.0, coord_mapper.normalized_to_pixel_width(stroke.width))
        pen = QPen(color, pixel_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        pts = stroke.points
        if len(pts) == 1:
            wx, wy = coord_mapper.normalized_to_widget(pts[0].x, pts[0].y)
            painter.setBrush(color)
            r = max(0.5, pixel_width / 2.0)
            painter.drawEllipse(QPointF(wx, wy), r, r)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            continue

        path = QPainterPath()
        start_wx, start_wy = coord_mapper.normalized_to_widget(pts[0].x, pts[0].y)
        path.moveTo(start_wx, start_wy)

        for pt in pts[1:]:
            wx, wy = coord_mapper.normalized_to_widget(pt.x, pt.y)
            path.lineTo(wx, wy)

        painter.drawPath(path)


def export_page_to_image(
    canvas_state: CanvasState,
    width: int = 1920,
    height: int = 1080,
    background_color: str | None = "#FFFFFF",
) -> QImage:
    """Render a canvas state to a high-resolution QImage.

    Args:
        canvas_state: CanvasState to render.
        width: Output width in pixels (defaults to 1920).
        height: Output height in pixels (defaults to 1080).
        background_color: '#FFFFFF' or None for transparent.

    Returns:
        Rendered QImage in Format_ARGB32_Premultiplied.
    """
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    if background_color is None:
        image.fill(Qt.GlobalColor.transparent)
    else:
        image.fill(QColor(background_color))

    painter = QPainter(image)
    render_strokes(
        painter=painter,
        strokes=canvas_state.strokes,
        width=width,
        height=height,
        background_color=background_color,
    )
    painter.end()
    return image


def export_page_to_png(
    canvas_state: CanvasState,
    file_path: str,
    width: int = 1920,
    height: int = 1080,
    transparent: bool = False,
) -> bool:
    """Export a single canvas page to a PNG file.

    Args:
        canvas_state: CanvasState to export.
        file_path: Destination file path.
        width: Output width (default 1920).
        height: Output height (default 1080).
        transparent: True for transparent background, False for white.

    Returns:
        True if the file was successfully written.
    """
    bg = None if transparent else "#FFFFFF"
    image = export_page_to_image(canvas_state, width=width, height=height, background_color=bg)
    saved = image.save(file_path, "PNG")
    if not saved:
        logger.error("Failed to save PNG image to %s", file_path)
    return saved


def export_board_to_pdf(
    document: MultiPageDocument,
    file_path: str,
) -> bool:
    """Export an entire multi-page board to a vector PDF preserving 16:9 aspect ratio.

    Args:
        document: MultiPageDocument to export.
        file_path: Destination PDF file path.

    Returns:
        True if export succeeded.
    """
    if not document.pages:
        logger.warning("Attempted to export empty document to PDF")
        return False

    # Ensure current page in-memory strokes are committed/saved
    document.save_current_page()

    writer = QPdfWriter(file_path)
    # Standard 16:9 presentation dimensions (320mm x 180mm)
    writer.setPageSize(QPageSize(QSizeF(320.0, 180.0), QPageSize.Unit.Millimeter))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0))

    painter = QPainter(writer)
    try:
        pw = writer.width()
        ph = writer.height()

        for idx, page_rec in enumerate(document.pages):
            if idx > 0:
                writer.newPage()

            # Retrieve strokes for this page
            if page_rec.id == document.active_page_id:
                strokes = list(document.active_canvas_state.strokes)
            else:
                strokes = document.repository.load_page_strokes(page_rec.id)

            render_strokes(
                painter=painter,
                strokes=strokes,
                width=pw,
                height=ph,
                background_color="#FFFFFF",
            )
    finally:
        painter.end()

    logger.info("Exported %d pages to PDF: %s", len(document.pages), file_path)
    return True
