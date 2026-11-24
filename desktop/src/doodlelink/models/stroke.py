"""Platform-independent logical stroke and point data models."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolType(str, Enum):
    """Drawing tool types supported by DoodleLink."""

    PEN = "pen"
    ERASER = "eraser"

    @classmethod
    def from_str(cls, value: str) -> ToolType:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.PEN


@dataclass(slots=True)
class Point:
    """A single normalized point within the logical canvas [0.0, 1.0] x [0.0, 1.0]."""

    x: float
    y: float
    timestamp: float = field(default_factory=lambda: time.time() * 1000)
    pressure: float = 1.0

    def __post_init__(self) -> None:
        # Clamp to bounds [0.0, 1.0] with generous numerical tolerance
        self.x = max(0.0, min(1.0, float(self.x)))
        self.y = max(0.0, min(1.0, float(self.y)))
        self.pressure = max(0.0, min(1.0, float(self.pressure)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": round(self.x, 6),
            "y": round(self.y, 6),
            "timestamp": round(self.timestamp, 2),
            "pressure": round(self.pressure, 4),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Point:
        return cls(
            x=float(data["x"]),
            y=float(data["y"]),
            timestamp=float(data.get("timestamp", time.time() * 1000)),
            pressure=float(data.get("pressure", 1.0)),
        )


@dataclass
class Stroke:
    """A continuous drawing gesture consisting of ordered normalized points."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool: ToolType = ToolType.PEN
    color: str = "#000000"
    width: float = 0.004  # Normalized width (e.g. 0.004 = 4px on 1000px canvas)
    points: list[Point] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.tool, str):
            self.tool = ToolType.from_str(self.tool)
        self.width = max(0.0001, min(0.5, float(self.width)))
        if not self.color.startswith("#"):
            self.color = f"#{self.color}"

    def add_point(
        self,
        x: float,
        y: float,
        timestamp: float | None = None,
        pressure: float = 1.0,
    ) -> Point:
        """Add a normalized point to the stroke."""
        pt = Point(
            x=x,
            y=y,
            timestamp=timestamp if timestamp is not None else time.time() * 1000,
            pressure=pressure,
        )
        self.points.append(pt)
        return pt

    def is_empty(self) -> bool:
        """Return True if stroke has no points."""
        return len(self.points) == 0

    def bounding_box(self) -> tuple[float, float, float, float] | None:
        """Return normalized (min_x, min_y, max_x, max_y) or None if empty."""
        if not self.points:
            return None
        min_x = min(p.x for p in self.points)
        max_x = max(p.x for p in self.points)
        min_y = min(p.y for p in self.points)
        max_y = max(p.y for p in self.points)
        half_w = self.width / 2.0
        return (
            max(0.0, min_x - half_w),
            max(0.0, min_y - half_w),
            min(1.0, max_x + half_w),
            min(1.0, max_y + half_w),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize stroke to JSON-compatible dictionary."""
        return {
            "id": self.id,
            "tool": self.tool.value,
            "color": self.color,
            "width": round(self.width, 6),
            "points": [p.to_dict() for p in self.points],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Stroke:
        """Deserialize stroke from JSON-compatible dictionary."""
        stroke = cls(
            id=str(data.get("id", str(uuid.uuid4()))),
            tool=ToolType.from_str(data.get("tool", "pen")),
            color=str(data.get("color", "#000000")),
            width=float(data.get("width", 0.004)),
        )
        points_data = data.get("points", [])
        stroke.points = [Point.from_dict(p) for p in points_data]
        return stroke
