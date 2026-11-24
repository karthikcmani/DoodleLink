"""Comprehensive tests for DoodleLink SQLite persistence, migrations, and repository operations."""

from __future__ import annotations

import sqlite3
import pytest

from doodlelink.models.canvas_state import (
    AddStrokeAction,
    CanvasAction,
    CanvasState,
    ClearCanvasAction,
)
from doodlelink.models.stroke import Point, Stroke, ToolType
from doodlelink.storage.board_repository import BoardRepository
from doodlelink.storage.database import DatabaseManager
from doodlelink.storage.schema import CURRENT_SCHEMA_VERSION, apply_migrations


@pytest.fixture
def memory_repo() -> BoardRepository:
    db = DatabaseManager(db_path=":memory:")
    return BoardRepository(db_manager=db)


def test_schema_migrations():
    conn = sqlite3.connect(":memory:")
    version = apply_migrations(conn)
    assert version == CURRENT_SCHEMA_VERSION

    # Calling again should be idempotent
    version_again = apply_migrations(conn)
    assert version_again == CURRENT_SCHEMA_VERSION
    conn.close()


def test_board_creation_and_auto_page_1(memory_repo: BoardRepository):
    board = memory_repo.create_board(title="Algebra 101")
    assert board.title == "Algebra 101"
    assert board.page_count == 1

    fetched = memory_repo.get_board(board.id)
    assert fetched is not None
    assert fetched.id == board.id
    assert fetched.title == "Algebra 101"
    assert fetched.page_count == 1

    # Verify Page 1 was automatically initialized
    pages = memory_repo.get_pages_for_board(board.id)
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].title == "Page 1"


def test_board_listing_and_rename(memory_repo: BoardRepository):
    b1 = memory_repo.create_board("First Board")
    b2 = memory_repo.create_board("Second Board")

    boards = memory_repo.list_boards()
    assert len(boards) >= 2
    assert boards[0].id == b2.id  # Ordered by updated_at DESC

    # Rename
    ok = memory_repo.rename_board(b1.id, "Renamed Board")
    assert ok is True
    updated = memory_repo.get_board(b1.id)
    assert updated is not None
    assert updated.title == "Renamed Board"


def test_board_delete_cascades_pages_and_strokes(memory_repo: BoardRepository):
    board = memory_repo.create_board("To Delete")
    page = memory_repo.get_pages_for_board(board.id)[0]

    # Save a stroke
    stroke = Stroke(
        id="s-del-1",
        tool=ToolType.PEN,
        color="#2563EB",
        width=0.005,
        points=[Point(0.1, 0.2), Point(0.3, 0.4)],
    )
    memory_repo.save_page_canvas_state(page.id, [stroke], [AddStrokeAction(stroke)], [])

    # Delete board
    ok = memory_repo.delete_board(board.id)
    assert ok is True
    assert memory_repo.get_board(board.id) is None
    assert len(memory_repo.get_pages_for_board(board.id)) == 0

    # Ensure strokes table has no orphaned rows
    conn = memory_repo.db.connect()
    cur = conn.execute("SELECT COUNT(*) FROM strokes WHERE page_id = ?;", (page.id,))
    assert cur.fetchone()[0] == 0


def test_page_creation_and_renumbering_on_delete(memory_repo: BoardRepository):
    board = memory_repo.create_board("Multi-page")
    p1 = memory_repo.get_pages_for_board(board.id)[0]
    p2 = memory_repo.create_page(board.id, "Page 2")
    p3 = memory_repo.create_page(board.id, "Page 3")

    pages = memory_repo.get_pages_for_board(board.id)
    assert len(pages) == 3
    assert [p.page_number for p in pages] == [1, 2, 3]

    # Delete middle page (Page 2)
    ok = memory_repo.delete_page(p2.id)
    assert ok is True

    # Remaining pages must be renumbered sequentially: 1, 2
    pages_after = memory_repo.get_pages_for_board(board.id)
    assert len(pages_after) == 2
    assert pages_after[0].id == p1.id
    assert pages_after[0].page_number == 1
    assert pages_after[1].id == p3.id
    assert pages_after[1].page_number == 2


def test_cannot_delete_only_page(memory_repo: BoardRepository):
    board = memory_repo.create_board("Single Page")
    p1 = memory_repo.get_pages_for_board(board.id)[0]

    with pytest.raises(ValueError, match="Cannot delete the only page"):
        memory_repo.delete_page(p1.id)


def test_duplicate_page(memory_repo: BoardRepository):
    board = memory_repo.create_board("Duplicate Test")
    page = memory_repo.get_pages_for_board(board.id)[0]

    stroke = Stroke(
        id="s-orig-1",
        tool=ToolType.PEN,
        color="#10B981",
        width=0.008,
        points=[Point(0.2, 0.2), Point(0.5, 0.5)],
    )
    memory_repo.save_page_canvas_state(page.id, [stroke], [AddStrokeAction(stroke)], [])

    dup_page = memory_repo.duplicate_page(page.id)
    assert dup_page.page_number == 2
    assert "Copy" in dup_page.title

    # Verify duplicated strokes
    strokes, undo_stack, redo_stack = memory_repo.load_page_canvas_state(dup_page.id)
    assert len(strokes) == 1
    assert strokes[0].id != "s-orig-1"  # New cloned ID
    assert strokes[0].color == "#10B981"
    assert len(strokes[0].points) == 2
    assert len(undo_stack) == 1


def test_full_canvas_state_and_undo_redo_persistence(memory_repo: BoardRepository):
    board = memory_repo.create_board("Undo/Redo Test")
    page = memory_repo.get_pages_for_board(board.id)[0]

    # Simulate a canvas session:
    # 1. User draws s1
    # 2. User draws s2
    # 3. User hits Undo (s2 is undone -> visible: [s1], undo: [s1], redo: [s2])
    s1 = Stroke(id="s1", tool=ToolType.PEN, color="#000000", width=0.004, points=[Point(0.1, 0.1)])
    s2 = Stroke(id="s2", tool=ToolType.ERASER, color="#FFFFFF", width=0.02, points=[Point(0.2, 0.2)])

    visible = [s1]
    undo_stack: list[CanvasAction] = [AddStrokeAction(s1)]
    redo_stack: list[CanvasAction] = [AddStrokeAction(s2)]

    # Save to SQLite
    memory_repo.save_page_canvas_state(page.id, visible, undo_stack, redo_stack)

    # Load back (simulating app restart)
    loaded_visible, loaded_undo, loaded_redo = memory_repo.load_page_canvas_state(page.id)

    assert len(loaded_visible) == 1
    assert loaded_visible[0].id == "s1"
    assert loaded_visible[0].tool == ToolType.PEN

    assert len(loaded_undo) == 1
    assert isinstance(loaded_undo[0], AddStrokeAction)
    assert loaded_undo[0].stroke.id == "s1"

    assert len(loaded_redo) == 1
    assert isinstance(loaded_redo[0], AddStrokeAction)
    assert loaded_redo[0].stroke.id == "s2"

    # Reconstruct CanvasState and verify Redo works!
    canvas = CanvasState()
    canvas.strokes = list(loaded_visible)
    canvas._undo_stack = list(loaded_undo)
    canvas._redo_stack = list(loaded_redo)

    assert canvas.can_redo is True
    ok = canvas.redo()
    assert ok is True
    assert canvas.stroke_count == 2
    assert canvas.strokes[1].id == "s2"
    assert canvas.can_redo is False
    assert canvas.can_undo is True


def test_clear_canvas_persistence_and_undo(memory_repo: BoardRepository):
    board = memory_repo.create_board("Clear Test")
    page = memory_repo.get_pages_for_board(board.id)[0]

    s1 = Stroke(id="s1", tool=ToolType.PEN, color="#FF0000", width=0.005, points=[Point(0.1, 0.1)])
    s2 = Stroke(id="s2", tool=ToolType.PEN, color="#00FF00", width=0.005, points=[Point(0.2, 0.2)])

    # Canvas cleared: visible is empty, undo stack has ClearCanvasAction([s1, s2])
    visible: list[Stroke] = []
    undo_stack: list[CanvasAction] = [ClearCanvasAction([s1, s2])]
    redo_stack: list[CanvasAction] = []

    memory_repo.save_page_canvas_state(page.id, visible, undo_stack, redo_stack)

    loaded_visible, loaded_undo, loaded_redo = memory_repo.load_page_canvas_state(page.id)
    assert len(loaded_visible) == 0
    assert len(loaded_undo) == 1
    assert isinstance(loaded_undo[0], ClearCanvasAction)
    assert len(loaded_undo[0].cleared_strokes) == 2

    # Verify Undo restores cleared strokes!
    canvas = CanvasState()
    canvas.strokes = list(loaded_visible)
    canvas._undo_stack = list(loaded_undo)
    canvas._redo_stack = list(loaded_redo)

    assert canvas.can_undo is True
    ok = canvas.undo()
    assert ok is True
    assert canvas.stroke_count == 2
    assert [s.id for s in canvas.strokes] == ["s1", "s2"]


def test_app_state_last_active_board_and_page(memory_repo: BoardRepository):
    assert memory_repo.get_last_active_board_and_page() == (None, None)

    memory_repo.set_last_active_board_and_page("b-123", "p-456")
    b, p = memory_repo.get_last_active_board_and_page()
    assert b == "b-123"
    assert p == "p-456"

    # Update again
    memory_repo.set_last_active_board_and_page("b-789", "p-999")
    assert memory_repo.get_last_active_board_and_page() == ("b-789", "p-999")
