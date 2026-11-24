"""Unit tests for CoordinateMapper and LogicalCanvas."""

from doodlelink.models.coordinate import CoordinateMapper, LogicalCanvas


def test_coordinate_mapper_pillarboxing_wide_aspect():
    # 16:9 canvas inside 24:9 wide widget -> pillarbox (margins on left and right)
    mapper = CoordinateMapper(
        logical_canvas=LogicalCanvas(aspect_ratio=16.0 / 9.0),
        preserve_aspect_ratio=True,
    )
    vp = mapper.update_widget_size(2400, 900)
    # Expected viewport: height=900, width=900*(16/9)=1600. x margin = (2400-1600)/2 = 400.
    assert vp.height == 900.0
    assert vp.width == 1600.0
    assert vp.x == 400.0
    assert vp.y == 0.0

    # Center of widget (1200, 450) maps to normalized (0.5, 0.5)
    norm_x, norm_y = mapper.widget_to_normalized(1200, 450)
    assert abs(norm_x - 0.5) < 1e-6
    assert abs(norm_y - 0.5) < 1e-6

    # Top-left of logical viewport (400, 0) maps to (0.0, 0.0)
    norm_x, norm_y = mapper.widget_to_normalized(400, 0)
    assert norm_x == 0.0
    assert norm_y == 0.0

    # Margins outside viewport are clamped
    norm_x, _ = mapper.widget_to_normalized(100, 450, clamp=True)
    assert norm_x == 0.0


def test_coordinate_mapper_letterboxing_tall_aspect():
    # 16:9 canvas inside 16:18 tall widget -> letterbox (margins on top and bottom)
    mapper = CoordinateMapper(
        logical_canvas=LogicalCanvas(aspect_ratio=16.0 / 9.0),
        preserve_aspect_ratio=True,
    )
    vp = mapper.update_widget_size(1600, 1800)
    # Expected viewport: width=1600, height=1600/(16/9)=900. y margin = (1800-900)/2 = 450.
    assert vp.width == 1600.0
    assert vp.height == 900.0
    assert vp.x == 0.0
    assert vp.y == 450.0

    # Center of widget (800, 900) maps to (0.5, 0.5)
    norm_x, norm_y = mapper.widget_to_normalized(800, 900)
    assert abs(norm_x - 0.5) < 1e-6
    assert abs(norm_y - 0.5) < 1e-6


def test_coordinate_mapper_roundtrip():
    mapper = CoordinateMapper(
        logical_canvas=LogicalCanvas(aspect_ratio=16.0 / 9.0),
        preserve_aspect_ratio=True,
    )
    mapper.update_widget_size(1920, 1080)

    # Test roundtrip from normalized -> widget -> normalized
    test_points = [(0.0, 0.0), (1.0, 1.0), (0.5, 0.5), (0.25, 0.75), (0.8, 0.2)]
    for orig_x, orig_y in test_points:
        wx, wy = mapper.normalized_to_widget(orig_x, orig_y)
        nx, ny = mapper.widget_to_normalized(wx, wy)
        assert abs(nx - orig_x) < 1e-6
        assert abs(ny - orig_y) < 1e-6


def test_stroke_width_conversion():
    mapper = CoordinateMapper()
    mapper.update_widget_size(1000, 500)
    # Viewport width is 1000*(16/9) or fits within widget
    vp_w = mapper.viewport.width

    # 4px on viewport
    norm_w = mapper.pixel_to_normalized_width(4.0)
    assert abs(norm_w - (4.0 / vp_w)) < 1e-6

    # Convert back
    px_w = mapper.normalized_to_pixel_width(norm_w)
    assert abs(px_w - 4.0) < 1e-3
