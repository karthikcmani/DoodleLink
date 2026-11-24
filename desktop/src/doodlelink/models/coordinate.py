"""Coordinate mapping between widget pixels and normalized logical whiteboard coordinates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ViewportRect:
    """The pixel rectangle within a widget where the logical canvas is rendered."""

    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.right and self.y <= py <= self.bottom


@dataclass
class LogicalCanvas:
    """Logical canvas configuration."""

    # Default to 16:9 presentation aspect ratio; set to None for free aspect ratio
    aspect_ratio: float | None = 16.0 / 9.0
    reference_width: float = 1920.0
    reference_height: float = 1080.0


class CoordinateMapper:
    """Translates between physical widget pixel space and normalized [0.0, 1.0] logical canvas space.

    Ensures strokes remain crisp, consistent, and geometrically aligned across window
    resizes and across different devices (e.g. phone vs PC) by letterboxing or pillarboxing
    the logical canvas inside the drawing viewport.
    """

    def __init__(
        self,
        logical_canvas: LogicalCanvas | None = None,
        preserve_aspect_ratio: bool = True,
    ) -> None:
        self.logical_canvas = logical_canvas or LogicalCanvas()
        self.preserve_aspect_ratio = preserve_aspect_ratio
        self._viewport = ViewportRect(0.0, 0.0, 1.0, 1.0)

    @property
    def viewport(self) -> ViewportRect:
        return self._viewport

    def update_widget_size(self, widget_width: float, widget_height: float) -> ViewportRect:
        """Compute the centered viewport rectangle fitting the logical canvas within the widget."""
        w = max(1.0, float(widget_width))
        h = max(1.0, float(widget_height))

        if not self.preserve_aspect_ratio or self.logical_canvas.aspect_ratio is None:
            self._viewport = ViewportRect(0.0, 0.0, w, h)
            return self._viewport

        target_ratio = self.logical_canvas.aspect_ratio
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Widget is wider than logical canvas -> pillarbox (left/right margins)
            viewport_h = h
            viewport_w = h * target_ratio
            viewport_x = (w - viewport_w) / 2.0
            viewport_y = 0.0
        else:
            # Widget is taller than logical canvas -> letterbox (top/bottom margins)
            viewport_w = w
            viewport_h = w / target_ratio
            viewport_x = 0.0
            viewport_y = (h - viewport_h) / 2.0

        self._viewport = ViewportRect(viewport_x, viewport_y, viewport_w, viewport_h)
        return self._viewport

    def widget_to_normalized(
        self,
        widget_x: float,
        widget_y: float,
        clamp: bool = True,
    ) -> tuple[float, float]:
        """Convert widget pixel coordinates to normalized logical canvas coordinates [0.0, 1.0]."""
        vp = self._viewport
        if vp.width <= 0 or vp.height <= 0:
            return 0.0, 0.0

        norm_x = (widget_x - vp.x) / vp.width
        norm_y = (widget_y - vp.y) / vp.height

        if clamp:
            norm_x = max(0.0, min(1.0, norm_x))
            norm_y = max(0.0, min(1.0, norm_y))

        return norm_x, norm_y

    def normalized_to_widget(self, norm_x: float, norm_y: float) -> tuple[float, float]:
        """Convert normalized logical canvas coordinates [0.0, 1.0] to widget pixel coordinates."""
        vp = self._viewport
        wx = vp.x + norm_x * vp.width
        wy = vp.y + norm_y * vp.height
        return wx, wy

    def normalized_to_pixel_width(self, norm_width: float) -> float:
        """Convert normalized stroke width to current viewport pixels."""
        return max(1.0, norm_width * self._viewport.width)

    def pixel_to_normalized_width(self, px_width: float) -> float:
        """Convert pixel stroke width on current viewport to normalized stroke width."""
        vp_width = max(1.0, self._viewport.width)
        return max(0.0001, px_width / vp_width)
