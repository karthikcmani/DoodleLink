"""Integration tests for WhiteboardServer WebSocket pairing and drawing event stream."""

import asyncio
import json
import time

import pytest
import websockets
from doodlelink.network.pairing import PairingManager
from doodlelink.network.server import WhiteboardServer
from PySide6.QtWidgets import QApplication


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def server(qapp):
    manager = PairingManager()
    srv = WhiteboardServer(pairing_manager=manager)
    # Use ephemeral high port for testing
    srv.start(host="127.0.0.1", port=18765)
    # Wait briefly for server loop to bind
    time.sleep(0.3)
    yield srv
    srv.stop()


@pytest.mark.asyncio
async def test_server_rejects_unauthorized_client(server):
    uri = "ws://127.0.0.1:18765"
    async with websockets.connect(uri) as ws:
        # Send bad code
        bad_pair = {"version": 1, "type": "pair", "code": "000000"}
        await ws.send(json.dumps(bad_pair))

        resp_raw = await ws.recv()
        resp = json.loads(resp_raw)
        assert resp["type"] == "error"
        assert resp["code"] == "INVALID_PAIRING_CODE"


@pytest.mark.asyncio
async def test_server_successful_pairing_and_events(server, qapp):
    uri = "ws://127.0.0.1:18765"
    code = server.pairing_manager.current_code

    received_signals = []
    server.client_paired.connect(lambda addr, name: received_signals.append(("paired", name)))
    server.remote_stroke_started.connect(lambda data: received_signals.append(("start", data["stroke_id"])))
    server.remote_stroke_points.connect(lambda data: received_signals.append(("points", len(data["points"]))))
    server.remote_stroke_ended.connect(lambda s_id: received_signals.append(("end", s_id)))
    server.remote_undo.connect(lambda: received_signals.append(("undo",)))
    server.remote_redo.connect(lambda: received_signals.append(("redo",)))
    server.remote_clear.connect(lambda: received_signals.append(("clear",)))

    async with websockets.connect(uri) as ws:
        # 1. Pair
        pair_req = {"version": 1, "type": "pair", "code": code, "client_name": "Test Phone"}
        await ws.send(json.dumps(pair_req))

        resp_raw = await ws.recv()
        resp = json.loads(resp_raw)
        assert resp["type"] == "pair_success"
        assert resp["session_id"] == server.pairing_manager.session_id

        await asyncio.sleep(0.1)
        qapp.processEvents()
        assert any(sig[0] == "paired" and sig[1] == "Test Phone" for sig in received_signals)

        # 2. Stroke Start
        start_msg = {
            "version": 1,
            "type": "stroke_start",
            "stroke_id": "stroke-abc",
            "sequence": 1,
            "tool": "pen",
            "color": "#2563EB",
            "width": 0.005,
            "points": [{"x": 0.1, "y": 0.1}],
        }
        await ws.send(json.dumps(start_msg))
        await asyncio.sleep(0.1)
        qapp.processEvents()
        assert any(sig == ("start", "stroke-abc") for sig in received_signals)

        # 3. Stroke Points
        pts_msg = {
            "version": 1,
            "type": "stroke_points",
            "stroke_id": "stroke-abc",
            "sequence": 2,
            "points": [{"x": 0.2, "y": 0.2}, {"x": 0.3, "y": 0.3}],
        }
        await ws.send(json.dumps(pts_msg))
        await asyncio.sleep(0.1)
        qapp.processEvents()
        assert any(sig == ("points", 2) for sig in received_signals)

        # 4. Stroke End
        end_msg = {
            "version": 1,
            "type": "stroke_end",
            "stroke_id": "stroke-abc",
            "sequence": 3,
        }
        await ws.send(json.dumps(end_msg))
        await asyncio.sleep(0.1)
        qapp.processEvents()
        assert any(sig == ("end", "stroke-abc") for sig in received_signals)

        # 5. Undo, Redo, Clear
        await ws.send(json.dumps({"version": 1, "type": "undo", "sequence": 4}))
        await ws.send(json.dumps({"version": 1, "type": "redo", "sequence": 5}))
        await ws.send(json.dumps({"version": 1, "type": "clear_canvas", "sequence": 6}))
        await asyncio.sleep(0.1)
        qapp.processEvents()

        assert any(sig == ("undo",) for sig in received_signals)
        assert any(sig == ("redo",) for sig in received_signals)
        assert any(sig == ("clear",) for sig in received_signals)

        # 6. Heartbeat Ping -> Pong
        await ws.send(json.dumps({"version": 1, "type": "ping", "timestamp": 12345.0}))
        pong_raw = await ws.recv()
        pong = json.loads(pong_raw)
        assert pong["type"] == "pong"

        # 7. Broadcast from Server to Client
        server.broadcast_event({"version": 1, "type": "desktop_draw", "data": 42})
        bcast_raw = await ws.recv()
        bcast = json.loads(bcast_raw)
        assert bcast["type"] == "desktop_draw"
        assert bcast["data"] == 42


@pytest.mark.asyncio
async def test_replayed_pairing_code_rejected_and_session_reconnect_accepted(server, qapp):
    uri = "ws://127.0.0.1:18765"
    code = server.pairing_manager.current_code

    # 1. First client connects with code -> succeeds and consumes code
    async with websockets.connect(uri) as ws1:
        pair_req = {"version": 1, "type": "pair", "code": code, "client_name": "Device 1"}
        await ws1.send(json.dumps(pair_req))
        resp_raw = await ws1.recv()
        resp = json.loads(resp_raw)
        assert resp["type"] == "pair_success"
        session_id = resp["session_id"]

    # 2. Replay attempt with same code -> rejected because code is consumed
    async with websockets.connect(uri) as ws2:
        replay_req = {"version": 1, "type": "pair", "code": code, "client_name": "Attacker"}
        await ws2.send(json.dumps(replay_req))
        resp2_raw = await ws2.recv()
        resp2 = json.loads(resp2_raw)
        assert resp2["type"] == "error"
        assert resp2["code"] == "INVALID_PAIRING_CODE"

    # 3. Legitimate reconnect with session_id -> succeeds
    async with websockets.connect(uri) as ws3:
        reconnect_req = {"version": 1, "type": "pair", "session_id": session_id, "client_name": "Device 1"}
        await ws3.send(json.dumps(reconnect_req))
        resp3_raw = await ws3.recv()
        resp3 = json.loads(resp3_raw)
        assert resp3["type"] == "pair_success"
        assert resp3["session_id"] == session_id
