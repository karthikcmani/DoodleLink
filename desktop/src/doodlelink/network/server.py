"""Asynchronous WebSocket host server integrating local networking with the drawing canvas."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

from PySide6.QtCore import QObject, Signal
import websockets
from websockets.asyncio.server import ServerConnection, serve

from doodlelink.network.pairing import PairingManager
from doodlelink.network.protocol import (
    build_error,
    build_pair_success,
    build_pong,
    validate_message,
)

logger = logging.getLogger(__name__)


class WhiteboardServer(QObject):
    """Local WebSocket host server.

    Manages connected Android clients, enforces session pairing, and safely
    bridges network drawing events to the Qt application thread via Qt signals.
    """

    # Qt Signals for GUI integration
    server_started = Signal(str, int, str)  # host_ip, port, pairing_code
    server_stopped = Signal()
    client_connected = Signal(str)  # client_address
    client_paired = Signal(str, str)  # client_address, client_name
    client_disconnected = Signal(str)

    remote_stroke_started = Signal(dict)
    remote_stroke_points = Signal(dict)
    remote_stroke_ended = Signal(str)
    remote_stroke_cancelled = Signal(str)
    remote_undo = Signal()
    remote_redo = Signal()
    remote_clear = Signal()
    remote_page_switch = Signal(dict)

    def __init__(
        self,
        pairing_manager: PairingManager | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.pairing_manager = pairing_manager or PairingManager()
        self.port: int = 8765
        self.host_ip: str = "0.0.0.0"

        self._server = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._is_running: bool = False
        self._paired_clients: set[ServerConnection] = set()

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def paired_client_count(self) -> int:
        return len(self._paired_clients)

    def start(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        """Start the WebSocket server in a background event loop thread."""
        if self._is_running:
            return

        self.host_ip = host
        self.port = port
        self._is_running = True

        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the WebSocket server and shut down background event loop."""
        if not self._is_running:
            return

        self._is_running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._stop_internal(), self._loop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self.server_stopped.emit()

    def broadcast_event(self, event_data: dict[str, Any]) -> None:
        """Broadcast a drawing event from desktop to all connected paired clients."""
        if not self._is_running or not self._loop or not self._paired_clients:
            return
        payload = json.dumps(event_data)
        asyncio.run_coroutine_threadsafe(self._broadcast_coro(payload), self._loop)

    async def _broadcast_coro(self, payload: str) -> None:
        targets = list(self._paired_clients)
        if not targets:
            return
        await asyncio.gather(
            *[client.send(payload) for client in targets],
            return_exceptions=True,
        )

    def _run_event_loop(self) -> None:
        """Entry point for the background network thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        finally:
            self._loop.close()

    async def _serve(self) -> None:
        async with serve(self._handle_connection, self.host_ip, self.port) as server:
            self._server = server
            primary_ip = self.pairing_manager.get_primary_ip()
            self.server_started.emit(primary_ip, self.port, self.pairing_manager.current_code)

            while self._is_running:
                await asyncio.sleep(0.5)

    async def _stop_internal(self) -> None:
        for client in list(self._paired_clients):
            try:
                await client.close(code=1000, reason="Server shutting down")
            except Exception:
                pass
        self._paired_clients.clear()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        """Handle individual client lifecycle: authentication, message loop, disconnect."""
        addr_str = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.client_connected.emit(addr_str)

        # 1. Pairing Authentication Phase (15-second timeout)
        try:
            pair_raw = await asyncio.wait_for(websocket.recv(), timeout=15.0)
            pair_data = json.loads(pair_raw)
        except Exception:
            await websocket.close(code=4001, reason="Pairing timeout or invalid JSON")
            self.client_disconnected.emit(addr_str)
            return

        is_valid, reason = validate_message(pair_data)
        if not is_valid or pair_data.get("type") != "pair":
            await websocket.send(json.dumps(build_error("INVALID_PROTOCOL", reason or "Expected pair event")))
            await websocket.close(code=4002, reason="Invalid handshake")
            self.client_disconnected.emit(addr_str)
            return

        candidate_code = pair_data.get("code")
        candidate_session = pair_data.get("session_id")

        is_reconnecting = bool(
            candidate_session and self.pairing_manager.verify_session(candidate_session)
        )
        is_new_pairing = bool(
            candidate_code and self.pairing_manager.verify_and_consume_code(candidate_code)
        )

        if not is_reconnecting and not is_new_pairing:
            await websocket.send(
                json.dumps(build_error("INVALID_PAIRING_CODE", "Incorrect, expired, or already-used pairing code"))
            )
            await websocket.close(code=4003, reason="Unauthorized")
            self.client_disconnected.emit(addr_str)
            return

        # Authentication Succeeded!
        client_name = pair_data.get("client_name", "Android Device")
        self._paired_clients.add(websocket)
        await websocket.send(json.dumps(build_pair_success(self.pairing_manager.session_id)))
        self.client_paired.emit(addr_str, client_name)

        # 2. Main Event Loop
        try:
            async for raw_message in websocket:
                try:
                    data = json.loads(raw_message)
                except Exception:
                    continue

                valid, err = validate_message(data)
                if not valid:
                    continue

                msg_type = data.get("type")
                if msg_type == "ping":
                    await websocket.send(json.dumps(build_pong()))
                elif msg_type == "stroke_start":
                    self.remote_stroke_started.emit(data)
                elif msg_type == "stroke_points":
                    self.remote_stroke_points.emit(data)
                elif msg_type == "stroke_end":
                    self.remote_stroke_ended.emit(data.get("stroke_id", ""))
                elif msg_type == "stroke_cancel":
                    self.remote_stroke_cancelled.emit(data.get("stroke_id", ""))
                elif msg_type == "undo":
                    self.remote_undo.emit()
                elif msg_type == "redo":
                    self.remote_redo.emit()
                elif msg_type == "clear_canvas":
                    self.remote_clear.emit()
                elif msg_type == "page_switch":
                    self.remote_page_switch.emit(data)

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._paired_clients.discard(websocket)
            self.client_disconnected.emit(addr_str)
