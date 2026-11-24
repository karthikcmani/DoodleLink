"""GUI tests for PySide6 CanvasWidget, WhiteboardToolbar, and MainWindow."""

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from doodlelink.models.canvas_state import CanvasState
from doodlelink.models.coordinate import CoordinateMapper, LogicalCanvas
from doodlelink.models.stroke import ToolType
from doodlelink.ui.canvas_widget import CanvasWidget
from doodlelink.ui.main_window import MainWindow
from doodlelink.ui.toolbar import WhiteboardToolbar


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_canvas_widget_mouse_drawing(qapp):
    state = CanvasState()
    mapper = CoordinateMapper(logical_canvas=LogicalCanvas(aspect_ratio=16.0 / 9.0))
    widget = CanvasWidget(canvas_state=state, coord_mapper=mapper)
    widget.resize(800, 600)
    mapper.update_widget_size(800, 600)

    # Simulate mouse press at center
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(400.0, 300.0),
        QPointF(400.0, 300.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mousePressEvent(press_event)
    assert state.active_stroke is not None
    assert len(state.active_stroke.points) == 1

    # Simulate mouse move
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(450.0, 350.0),
        QPointF(450.0, 350.0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mouseMoveEvent(move_event)
    assert len(state.active_stroke.points) == 2

    # Simulate mouse release
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(450.0, 350.0),
        QPointF(450.0, 350.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mouseReleaseEvent(release_event)
    assert state.active_stroke is None
    assert state.stroke_count == 1
    assert state.strokes[0].tool == ToolType.PEN


def test_canvas_widget_eraser_mode(qapp):
    state = CanvasState()
    widget = CanvasWidget(canvas_state=state)
    widget.resize(800, 600)
    widget.coord_mapper.update_widget_size(800, 600)

    widget.set_tool(ToolType.ERASER)
    widget.set_eraser_thickness(30.0)
    assert widget.current_tool == ToolType.ERASER
    assert widget.active_thickness_px == 30.0

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(400.0, 300.0),
        QPointF(400.0, 300.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mousePressEvent(press)
    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(400.0, 300.0),
        QPointF(400.0, 300.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mouseReleaseEvent(release)

    assert state.stroke_count == 1
    assert state.strokes[0].tool == ToolType.ERASER


def test_toolbar_controls(qapp):
    toolbar = WhiteboardToolbar()
    tool_events = []
    color_events = []
    thickness_events = []

    toolbar.tool_changed.connect(tool_events.append)
    toolbar.color_changed.connect(color_events.append)
    toolbar.thickness_changed.connect(thickness_events.append)

    # Click eraser button
    toolbar.eraser_btn.click()
    assert ToolType.ERASER in tool_events

    # Click pen button
    toolbar.pen_btn.click()
    assert ToolType.PEN in tool_events

    # Select color
    toolbar.color_palette.select_color("#2563EB")
    assert "#2563EB" in color_events

    # Select thickness
    toolbar._on_preset_clicked(8.0)
    assert 8.0 in thickness_events


def test_main_window_integration(qapp):
    window = MainWindow()
    window.resize(1000, 600)

    assert window.windowTitle() == "DoodleLink — Smart Whiteboard"
    assert window.canvas_state.stroke_count == 0

    # Draw a stroke programmatically
    window.canvas_state.start_stroke(start_x=0.1, start_y=0.1)
    window.canvas_state.append_point(0.2, 0.2)
    window.canvas_state.finish_stroke()

    assert window.canvas_state.stroke_count == 1
    assert "Strokes: 1" in window.stroke_count_label.text()

    # Test Undo via MainWindow action
    window.undo()
    assert window.canvas_state.stroke_count == 0
    assert "Strokes: 0" in window.stroke_count_label.text()

    # Test Redo
    window.redo()
    assert window.canvas_state.stroke_count == 1

    # Test Clear
    window.clear_canvas()
    assert window.canvas_state.stroke_count == 0

    # Test Undo of Clear
    window.undo()
    assert window.canvas_state.stroke_count == 1

    # Test Fullscreen toggle
    assert not window.isFullScreen()
    window.toggle_fullscreen()
    assert window.isFullScreen()
    window.toggle_fullscreen()
    assert not window.isFullScreen()

    window.close()
