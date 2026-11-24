"""Unit tests for MultiPageDocument: page lifecycle, autosave, and session recovery."""

from __future__ import annotations

import pytest

from doodlelink.models.multi_page import MultiPageDocument
from doodlelink.models.stroke import Point, Stroke, ToolType
from doodlelink.storage.board_repository import BoardRepository
from doodlelink.storage.database import DatabaseManager


@pytest.fixture
def memory_repo() -> BoardRepository:
    db = DatabaseManager(db_path=":memory:")
    return BoardRepository(db_manager=db)


def test_document_initialization(memory_repo: BoardRepository):
    board = memory_repo.create_board("Math Course")
    doc = MultiPageDocument(board, repository=memory_repo)

    assert doc.board.title == "Math Course"
    assert doc.page_count == 1
    assert doc.current_page_number == 1
    assert doc.active_canvas_state.stroke_count == 0


def test_add_and_switch_pages(memory_repo: BoardRepository):
    board = memory_repo.create_board("Lecture 1")
    doc = MultiPageDocument(board, repository=memory_repo)

    # Draw on Page 1
    s1 = Stroke(id="s1", tool=ToolType.PEN, color="#000000", width=0.005, points=[Point(0.1, 0.1)])
    doc.active_canvas_state.strokes.append(s1)
    doc.save_current_page()

    # Add Page 2
    p2 = doc.add_page("Page 2")
    assert doc.page_count == 2
    assert doc.current_page_number == 2
    assert doc.active_page_id == p2.id
    assert doc.active_canvas_state.stroke_count == 0

    # Draw on Page 2
    s2 = Stroke(id="s2", tool=ToolType.PEN, color="#FF0000", width=0.005, points=[Point(0.2, 0.2)])
    doc.active_canvas_state.strokes.append(s2)
    doc.save_current_page()

    # Switch back to Page 1
    ok = doc.prev_page()
    assert ok is True
    assert doc.current_page_number == 1
    assert doc.active_canvas_state.stroke_count == 1
    assert doc.active_canvas_state.strokes[0].id == "s1"

    # Switch next to Page 2
    ok = doc.next_page()
    assert ok is True
    assert doc.current_page_number == 2
    assert doc.active_canvas_state.stroke_count == 1
    assert doc.active_canvas_state.strokes[0].id == "s2"


def test_duplicate_current_page(memory_repo: BoardRepository):
    board = memory_repo.create_board("Dup Board")
    doc = MultiPageDocument(board, repository=memory_repo)

    s1 = Stroke(id="s1", tool=ToolType.PEN, color="#10B981", width=0.005, points=[Point(0.3, 0.3)])
    doc.active_canvas_state.strokes.append(s1)
    doc.save_current_page()

    dup = doc.duplicate_current_page()
    assert doc.page_count == 2
    assert doc.current_page_number == 2
    assert doc.active_page_id == dup.id
    # Cloned content should exist
    assert doc.active_canvas_state.stroke_count == 1
    assert doc.active_canvas_state.strokes[0].id != "s1"
    assert doc.active_canvas_state.strokes[0].color == "#10B981"


def test_delete_page(memory_repo: BoardRepository):
    board = memory_repo.create_board("Delete Page Board")
    doc = MultiPageDocument(board, repository=memory_repo)

    # Cannot delete only page
    assert doc.delete_current_page() is False

    doc.add_page("Page 2")
    assert doc.page_count == 2
    assert doc.current_page_number == 2

    # Delete Page 2
    ok = doc.delete_current_page()
    assert ok is True
    assert doc.page_count == 1
    assert doc.current_page_number == 1


def test_load_or_create_default_recovery(memory_repo: BoardRepository):
    board = memory_repo.create_board("Auto Recover Board")
    doc1 = MultiPageDocument(board, repository=memory_repo)
    p2 = doc1.add_page("Page 2")

    # Record active state
    memory_repo.set_last_active_board_and_page(board.id, p2.id)

    # Reopen document simulating application restart
    doc2 = MultiPageDocument.load_or_create_default(repository=memory_repo)
    assert doc2.board.id == board.id
    assert doc2.active_page_id == p2.id
    assert doc2.current_page_number == 2
