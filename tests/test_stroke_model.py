"""Unit tests for Point, Stroke, and ToolType models."""

from doodlelink.models.stroke import Point, Stroke, ToolType


def test_point_creation_and_bounds_clamping():
    p = Point(x=0.5, y=0.5, timestamp=1000.0, pressure=0.8)
    assert p.x == 0.5
    assert p.y == 0.5
    assert p.timestamp == 1000.0
    assert p.pressure == 0.8

    # Test out-of-bounds clamping
    p_clamped = Point(x=-0.2, y=1.5, pressure=1.2)
    assert p_clamped.x == 0.0
    assert p_clamped.y == 1.0
    assert p_clamped.pressure == 1.0


def test_point_serialization():
    p = Point(x=0.1234567, y=0.9876543, timestamp=12345678.9, pressure=0.75)
    d = p.to_dict()
    assert d["x"] == 0.123457
    assert d["y"] == 0.987654
    assert d["pressure"] == 0.75

    p_restored = Point.from_dict(d)
    assert abs(p_restored.x - p.x) < 1e-5
    assert abs(p_restored.y - p.y) < 1e-5
    assert p_restored.pressure == 0.75


def test_stroke_creation_and_defaults():
    stroke = Stroke()
    assert stroke.id is not None
    assert stroke.tool == ToolType.PEN
    assert stroke.color == "#000000"
    assert stroke.width == 0.004
    assert stroke.is_empty()


def test_stroke_add_point_and_bounding_box():
    stroke = Stroke(tool=ToolType.PEN, color="#FF0000", width=0.01)
    assert stroke.bounding_box() is None

    stroke.add_point(0.2, 0.3)
    stroke.add_point(0.6, 0.7)
    assert not stroke.is_empty()
    assert len(stroke.points) == 2

    bbox = stroke.bounding_box()
    assert bbox is not None
    min_x, min_y, max_x, max_y = bbox
    assert min_x <= 0.2
    assert min_y <= 0.3
    assert max_x >= 0.6
    assert max_y >= 0.7


def test_stroke_serialization():
    stroke = Stroke(tool=ToolType.ERASER, color="#FFFFFF", width=0.02)
    stroke.add_point(0.1, 0.2)
    stroke.add_point(0.3, 0.4)

    d = stroke.to_dict()
    assert d["tool"] == "eraser"
    assert d["color"] == "#FFFFFF"
    assert d["width"] == 0.02
    assert len(d["points"]) == 2

    restored = Stroke.from_dict(d)
    assert restored.id == stroke.id
    assert restored.tool == ToolType.ERASER
    assert restored.color == "#FFFFFF"
    assert restored.width == 0.02
    assert len(restored.points) == 2
    assert abs(restored.points[0].x - 0.1) < 1e-5


def test_tool_type_from_str():
    assert ToolType.from_str("pen") == ToolType.PEN
    assert ToolType.from_str("PEN") == ToolType.PEN
    assert ToolType.from_str("eraser") == ToolType.ERASER
    assert ToolType.from_str("invalid") == ToolType.PEN
