"""Integration test verifying Phase 5 multi-page whiteboard synchronization, SQLite persistence, and export."""

import asyncio
import json
import os
import sys
import tempfile
import pytest
import websockets

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from doodlelink.export.exporter import export_board_to_pdf, export_page_to_png
from doodlelink.models.multi_page import MultiPageDocument
from doodlelink.models.stroke import ToolType
from doodlelink.network.pairing import PairingManager
from doodlelink.network.protocol import build_page_switch
from doodlelink.network.server import WhiteboardServer
from doodlelink.storage.board_repository import BoardRepository
from doodlelink.storage.database import DatabaseManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.mark.asyncio
async def test_multi_page_end_to_end_sync(qapp):
    # Isolated in-memory database and multi-page document
    db = DatabaseManager(":memory:")
    repo = BoardRepository(db)
    board = repo.create_board("Phase 5 Sync Board")
    doc = MultiPageDocument(board=board, repository=repo)

    pairing_mgr = PairingManager()
    code = pairing_mgr.generate_new_code()
    server = WhiteboardServer(pairing_manager=pairing_mgr)

    # Wire server signals to doc
    def on_remote_page_switch(data: dict):
        direction = data.get("direction")
        if direction == "add":
            doc.add_page()
        elif direction == "next":
            doc.next_page()
        elif direction == "prev":
            doc.prev_page()
        # Broadcast page info
        from doodlelink.network.protocol import build_page_info
        msg = build_page_info(
            board_id=doc.board.id,
            page_id=doc.active_page_id,
            page_number=doc.current_page_number,
            total_pages=doc.page_count,
            strokes=doc.active_canvas_state.strokes,
            sequence=1,
            session_id=pairing_mgr.session_id,
        )
        server.broadcast_event(msg)

    server.remote_page_switch.connect(on_remote_page_switch, Qt.ConnectionType.DirectConnection)
    server.start(host="127.0.0.1", port=8991)

    await asyncio.sleep(0.3)

    uri = "ws://127.0.0.1:8991"
    async with websockets.connect(uri) as ws:
        # 1. Pairing handshake
        pair_req = {
            "version": 1,
            "type": "pair",
            "code": code,
            "client_name": "Test Runner Phone",
        }
        await ws.send(json.dumps(pair_req))
        resp_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(resp_raw)
        assert resp["type"] == "pair_success"

        # 2. Client requests adding a page
        add_req = build_page_switch("add", session_id=pairing_mgr.session_id)
        await ws.send(json.dumps(add_req))

        # 3. Receive broadcast page_info from host
        page_info_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        page_info = json.loads(page_info_raw)
        assert page_info["type"] == "page_info"
        assert page_info["page_number"] == 2
        assert page_info["total_pages"] == 2
        assert doc.page_count == 2
        assert doc.current_page_number == 2

        # 4. Draw on page 2
        doc.active_canvas_state.start_stroke(ToolType.PEN, "#00FF00", 0.01, 0.3, 0.3)
        doc.active_canvas_state.finish_stroke()
        doc.save_current_page()

        # 5. Client requests prev page
        prev_req = build_page_switch("prev", session_id=pairing_mgr.session_id)
        await ws.send(json.dumps(prev_req))

        page_info_prev_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        page_info_prev = json.loads(page_info_prev_raw)
        assert page_info_prev["type"] == "page_info"
        assert page_info_prev["page_number"] == 1
        assert page_info_prev["total_pages"] == 2
        assert doc.current_page_number == 1

        # 6. Verify export of this multi-page board
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "sync_test.pdf")
            png_path = os.path.join(tmpdir, "page1.png")

            assert export_page_to_png(doc.active_canvas_state, png_path)
            assert os.path.exists(png_path)
            assert os.path.getsize(png_path) > 100

            assert export_board_to_pdf(doc, pdf_path)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 1000

    server.stop()
