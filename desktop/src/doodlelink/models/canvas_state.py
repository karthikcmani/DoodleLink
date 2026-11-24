"""Logical canvas state management with undo/redo and pointer lifecycle support."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from doodlelink.models.stroke import Point, Stroke, ToolType


class CanvasAction(ABC):
    """Abstract base command for undoable canvas mutations."""

    @abstractmethod
    def apply(self, state: CanvasState) -> None:
        """Apply or re-apply this action to the canvas."""

    @abstractmethod
    def undo(self, state: CanvasState) -> None:
        """Revert this action from the canvas."""


class AddStrokeAction(CanvasAction):
    """Action representing the addition of a stroke."""

    def __init__(self, stroke: Stroke) -> None:
        self.stroke = stroke

    def apply(self, state: CanvasState) -> None:
        if self.stroke not in state.strokes:
            state.strokes.append(self.stroke)

    def undo(self, state: CanvasState) -> None:
        if self.stroke in state.strokes:
            state.strokes.remove(self.stroke)


class ClearCanvasAction(CanvasAction):
    """Action representing clearing all strokes from the canvas."""

    def __init__(self, cleared_strokes: list[Stroke]) -> None:
        self.cleared_strokes = list(cleared_strokes)

    def apply(self, state: CanvasState) -> None:
        state.strokes.clear()

    def undo(self, state: CanvasState) -> None:
        state.strokes = list(self.cleared_strokes)


class CanvasState:
    """Manages ordered strokes, pointer lifecycle, undo/redo history, and change notifications.

    Completely decoupled from any UI framework, allowing reuse in headless tests
    and the future WebSocket synchronization server.
    """

    def __init__(self) -> None:
        self.strokes: list[Stroke] = []
        self._active_stroke: Stroke | None = None
        self._undo_stack: list[CanvasAction] = []
        self._redo_stack: list[CanvasAction] = []

        # Observer callbacks
        self._on_stroke_started: list[Callable[[Stroke], None]] = []
        self._on_point_added: list[Callable[[Stroke, Point], None]] = []
        self._on_stroke_committed: list[Callable[[Stroke], None]] = []
        self._on_stroke_cancelled: list[Callable[[], None]] = []
        self._on_state_changed: list[Callable[[], None]] = []

    # --- Properties ---

    @property
    def active_stroke(self) -> Stroke | None:
        """The in-progress stroke currently being drawn by pointer down/move, if any."""
        return self._active_stroke

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def stroke_count(self) -> int:
        return len(self.strokes)

    # --- Observer Subscriptions ---

    def add_change_listener(self, callback: Callable[[], None]) -> None:
        """Add a callback invoked on any canvas modification (undo, redo, clear, commit)."""
        if callback not in self._on_state_changed:
            self._on_state_changed.append(callback)

    def remove_change_listener(self, callback: Callable[[], None]) -> None:
        if callback in self._on_state_changed:
            self._on_state_changed.remove(callback)

    def _notify_change(self) -> None:
        for cb in self._on_state_changed:
            cb()

    # --- Pointer Lifecycle (Drawing Input) ---

    def start_stroke(
        self,
        tool: ToolType | str = ToolType.PEN,
        color: str = "#000000",
        width: float = 0.004,
        start_x: float | None = None,
        start_y: float | None = None,
        pressure: float = 1.0,
    ) -> Stroke:
        """Begin a new stroke when pointer / mouse is pressed down."""
        stroke = Stroke(tool=tool, color=color, width=width)
        if start_x is not None and start_y is not None:
            pt = stroke.add_point(start_x, start_y, pressure=pressure)
            for cb in self._on_point_added:
                cb(stroke, pt)

        self._active_stroke = stroke
        for cb in self._on_stroke_started:
            cb(stroke)
        return stroke

    def append_point(
        self,
        x: float,
        y: float,
        timestamp: float | None = None,
        pressure: float = 1.0,
    ) -> Point | None:
        """Append a normalized point to the currently active stroke."""
        if not self._active_stroke:
            return None
        pt = self._active_stroke.add_point(x, y, timestamp=timestamp, pressure=pressure)
        for cb in self._on_point_added:
            cb(self._active_stroke, pt)
        return pt

    def finish_stroke(self) -> Stroke | None:
        """Finalize and commit the active stroke on pointer up."""
        if not self._active_stroke:
            return None
        stroke = self._active_stroke
        self._active_stroke = None

        if stroke.is_empty():
            self._notify_change()
            return None

        self.strokes.append(stroke)
        action = AddStrokeAction(stroke)
        self._undo_stack.append(action)
        self._redo_stack.clear()

        for cb in self._on_stroke_committed:
            cb(stroke)
        self._notify_change()
        return stroke

    def cancel_stroke(self) -> None:
        """Cancel and discard the active stroke on gesture interruption or pointer cancel."""
        if self._active_stroke:
            self._active_stroke = None
            for cb in self._on_stroke_cancelled:
                cb()
            self._notify_change()

    # --- Direct Stroke Addition (e.g., from network sync) ---

    def add_remote_stroke(self, stroke: Stroke) -> None:
        """Add a completed stroke received externally, recording it in history."""
        self.strokes.append(stroke)
        self._undo_stack.append(AddStrokeAction(stroke))
        self._redo_stack.clear()
        self._notify_change()

    # --- Undo / Redo / Clear ---

    def undo(self) -> bool:
        """Undo the most recent action. Returns True if an action was undone."""
        if not self.can_undo:
            return False
        action = self._undo_stack.pop()
        action.undo(self)
        self._redo_stack.append(action)
        self._notify_change()
        return True

    def redo(self) -> bool:
        """Redo the most recently undone action. Returns True if an action was redone."""
        if not self.can_redo:
            return False
        action = self._redo_stack.pop()
        action.apply(self)
        self._undo_stack.append(action)
        self._notify_change()
        return True

    def clear(self) -> bool:
        """Clear all strokes from the canvas. Preserves undoability."""
        if not self.strokes:
            return False
        action = ClearCanvasAction(list(self.strokes))
        action.apply(self)
        self._undo_stack.append(action)
        self._redo_stack.clear()
        self._notify_change()
        return True
