"""Unit tests for PNG and PDF export functionality."""

import os
import sys
import tempfile
import pytest

from PySide6.QtWidgets import QApplication

from doodlelink.export.exporter import export_board_to_pdf, export_page_to_png
from doodlelink.models.canvas_state import CanvasState
from doodlelink.models.multi_page import MultiPageDocument
from doodlelink.models.stroke import ToolType
from doodlelink.storage.board_repository import BoardRepository
from doodlelink.storage.database import DatabaseManager


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance exists for QPainter / QPdfWriter operations."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_export_page_to_png_white_and_transparent(qapp):
    state = CanvasState()
    state.start_stroke(ToolType.PEN, "#FF0000", 0.005, 0.1, 0.1)
    state.append_point(0.2, 0.2)
    state.finish_stroke()

    state.start_stroke(ToolType.ERASER, "#FFFFFF", 0.02, 0.15, 0.15)
    state.finish_stroke()

    with tempfile.TemporaryDirectory() as tmpdir:
        white_path = os.path.join(tmpdir, "test_white.png")
        assert export_page_to_png(state, white_path, transparent=False)
        assert os.path.exists(white_path)
        assert os.path.getsize(white_path) > 100

        trans_path = os.path.join(tmpdir, "test_trans.png")
        assert export_page_to_png(state, trans_path, transparent=True)
        assert os.path.exists(trans_path)
        assert os.path.getsize(trans_path) > 100


def test_export_board_to_pdf_multi_page(qapp):
    db = DatabaseManager(":memory:")
    repo = BoardRepository(db)
    board = repo.create_board("Export Test Board")
    doc = MultiPageDocument(board=board, repository=repo)

    # Page 1: draw a red stroke
    doc.active_canvas_state.start_stroke(ToolType.PEN, "#FF0000", 0.01, 0.2, 0.2)
    doc.active_canvas_state.append_point(0.4, 0.4)
    doc.active_canvas_state.finish_stroke()

    # Add Page 2: draw a blue stroke
    doc.add_page()
    doc.active_canvas_state.start_stroke(ToolType.PEN, "#0000FF", 0.01, 0.5, 0.5)
    doc.active_canvas_state.append_point(0.7, 0.7)
    doc.active_canvas_state.finish_stroke()

    # Add Page 3: blank page
    doc.add_page()

    assert doc.page_count == 3

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "board_export.pdf")
        assert export_board_to_pdf(doc, pdf_path)
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000
