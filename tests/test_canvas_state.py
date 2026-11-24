"""Unit tests for CanvasState, undo/redo, clear, and pointer lifecycle."""

from doodlelink.models.canvas_state import CanvasState
from doodlelink.models.stroke import ToolType


def test_initial_state():
    state = CanvasState()
    assert state.stroke_count == 0
    assert not state.can_undo
    assert not state.can_redo
    assert state.active_stroke is None


def test_pointer_lifecycle_and_commit():
    state = CanvasState()

    # Pointer Down
    active = state.start_stroke(tool=ToolType.PEN, color="#2563EB", width=0.005, start_x=0.1, start_y=0.1)
    assert state.active_stroke is not None
    assert active.tool == ToolType.PEN
    assert len(active.points) == 1

    # Pointer Move
    pt2 = state.append_point(0.2, 0.2)
    assert pt2 is not None
    assert len(active.points) == 2

    # Pointer Up
    committed = state.finish_stroke()
    assert committed is not None
    assert state.active_stroke is None
    assert state.stroke_count == 1
    assert state.can_undo
    assert not state.can_redo


def test_empty_stroke_discarded_on_finish():
    state = CanvasState()
    state.start_stroke()
    # No points added
    committed = state.finish_stroke()
    assert committed is None
    assert state.stroke_count == 0
    assert not state.can_undo


def test_cancel_stroke():
    state = CanvasState()
    state.start_stroke(start_x=0.5, start_y=0.5)
    state.append_point(0.6, 0.6)
    assert state.active_stroke is not None

    state.cancel_stroke()
    assert state.active_stroke is None
    assert state.stroke_count == 0


def test_undo_and_redo_single_stroke():
    state = CanvasState()
    state.start_stroke(start_x=0.1, start_y=0.1)
    state.append_point(0.2, 0.2)
    state.finish_stroke()
    assert state.stroke_count == 1

    # Undo
    assert state.undo() is True
    assert state.stroke_count == 0
    assert not state.can_undo
    assert state.can_redo

    # Redo
    assert state.redo() is True
    assert state.stroke_count == 1
    assert state.can_undo
    assert not state.can_redo


def test_undo_and_redo_multiple_strokes_order():
    state = CanvasState()
    colors = ["#111111", "#222222", "#333333"]

    for c in colors:
        state.start_stroke(color=c, start_x=0.1, start_y=0.1)
        state.append_point(0.2, 0.2)
        state.finish_stroke()

    assert state.stroke_count == 3
    assert [s.color for s in state.strokes] == colors

    # Undo 2 strokes
    state.undo()
    assert state.stroke_count == 2
    state.undo()
    assert state.stroke_count == 1
    assert state.strokes[0].color == "#111111"

    # Redo 1 stroke
    state.redo()
    assert state.stroke_count == 2
    assert state.strokes[1].color == "#222222"

    # Redo 2nd stroke
    state.redo()
    assert state.stroke_count == 3
    assert state.strokes[2].color == "#333333"


def test_new_stroke_clears_redo_stack():
    state = CanvasState()
    # Stroke 1
    state.start_stroke(start_x=0.1, start_y=0.1)
    state.finish_stroke()
    # Undo it -> can redo
    state.undo()
    assert state.can_redo

    # Draw new Stroke 2
    state.start_stroke(start_x=0.3, start_y=0.3)
    state.finish_stroke()

    # Redo stack must be cleared
    assert not state.can_redo
    assert state.stroke_count == 1


def test_clear_canvas_and_undo_clear():
    state = CanvasState()
    # Clear on empty does nothing
    assert state.clear() is False

    # Add 2 strokes
    for _ in range(2):
        state.start_stroke(start_x=0.1, start_y=0.1)
        state.finish_stroke()
    assert state.stroke_count == 2

    # Clear
    assert state.clear() is True
    assert state.stroke_count == 0
    assert state.can_undo

    # Undo Clear -> restores both strokes
    assert state.undo() is True
    assert state.stroke_count == 2

    # Redo Clear -> re-clears
    assert state.redo() is True
    assert state.stroke_count == 0


def test_change_listener_notification():
    state = CanvasState()
    events = []

    def on_change():
        events.append("change")

    state.add_change_listener(on_change)

    state.start_stroke(start_x=0.1, start_y=0.1)
    state.finish_stroke()
    assert "change" in events
    events.clear()

    state.undo()
    assert "change" in events
    events.clear()

    state.redo()
    assert "change" in events
    events.clear()

    state.clear()
    assert "change" in events
