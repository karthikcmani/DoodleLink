"""Main application window for DoodleLink Whiteboard."""

from __future__ import annotations

from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from doodlelink.models.canvas_state import CanvasState
from doodlelink.models.coordinate import CoordinateMapper, LogicalCanvas
from doodlelink.models.stroke import ToolType
from doodlelink.network.adb_manager import AdbManager
from doodlelink.network.pairing import PairingManager
from doodlelink.network.protocol import (
    build_clear_canvas,
    build_redo,
    build_stroke_cancel,
    build_stroke_end,
    build_stroke_points,
    build_stroke_start,
    build_undo,
)
from doodlelink.network.server import WhiteboardServer
from doodlelink.ui.canvas_widget import CanvasWidget
from doodlelink.ui.pairing_dialog import PairingDialog
from doodlelink.ui.toolbar import WhiteboardToolbar


class MainWindow(QMainWindow):
    """Primary desktop whiteboard window for DoodleLink."""

    def __init__(
        self,
        canvas_state: CanvasState | None = None,
        coord_mapper: CoordinateMapper | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("DoodleLink — Smart Whiteboard")
        self.resize(1280, 800)
        self.setMinimumSize(800, 500)

        # Core logic models
        self.canvas_state = canvas_state or CanvasState()
        self.coord_mapper = coord_mapper or CoordinateMapper(
            logical_canvas=LogicalCanvas(aspect_ratio=16.0 / 9.0)
        )

        # Network host server & pairing
        self.pairing_manager = PairingManager()
        self.server = WhiteboardServer(pairing_manager=self.pairing_manager, parent=self)
        self._sequence: int = 0
        self._handling_remote: bool = False
        self.pairing_dialog: PairingDialog | None = None

        # Main central layout
        central_container = QWidget(self)
        self.setCentralWidget(central_container)
        root_layout = QVBoxLayout(central_container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Top Toolbar
        self.toolbar = WhiteboardToolbar(self)
        root_layout.addWidget(self.toolbar)

        # Drawing Canvas
        self.canvas = CanvasWidget(
            canvas_state=self.canvas_state,
            coord_mapper=self.coord_mapper,
            parent=self,
        )
        root_layout.addWidget(self.canvas, 1)

        # Status Bar
        self._setup_status_bar()

        # Connect Toolbar and Canvas Signals
        self._connect_signals()

        # Start WebSocket Host Server
        self.server.start(host="0.0.0.0", port=8765)

        # Setup Keyboard Shortcuts
        self._setup_shortcuts()

        # Apply Window Styling
        self._apply_styling()

        # Initial UI synchronization
        self._update_status_info()

    def _setup_status_bar(self) -> None:
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #111827;
                color: #9CA3AF;
                border-top: 1px solid #1F2937;
                font-size: 11px;
                padding: 2px 8px;
            }
        """)

        # Tool Info Label
        self.tool_info_label = QLabel("Tool: Pen (4px, #111827)")
        self.status_bar.addWidget(self.tool_info_label)

        # Stroke Count Label
        self.stroke_count_label = QLabel("Strokes: 0")
        self.status_bar.addWidget(self.stroke_count_label)

        # Cursor Coordinates Label (permanent on right)
        self.coord_label = QLabel("X: —  Y: —")
        self.coord_label.setFixedWidth(180)
        self.coord_label.setStyleSheet("font-family: monospace; color: #60A5FA;")
        self.status_bar.addPermanentWidget(self.coord_label)

        # Shortcuts hint
        hint_label = QLabel("P: Pen | E: Eraser | F11: Fullscreen | Ctrl+Z: Undo")
        hint_label.setStyleSheet("color: #6B7280; font-size: 10px;")
        self.status_bar.addPermanentWidget(hint_label)

    def _connect_signals(self) -> None:
        # Toolbar -> Canvas
        self.toolbar.tool_changed.connect(self._on_tool_changed)
        self.toolbar.color_changed.connect(self._on_color_changed)
        self.toolbar.thickness_changed.connect(self._on_thickness_changed)
        self.toolbar.undo_requested.connect(self.undo)
        self.toolbar.redo_requested.connect(self.redo)
        self.toolbar.clear_requested.connect(self.clear_canvas)
        self.toolbar.fullscreen_requested.connect(self.toggle_fullscreen)
        self.toolbar.pair_requested.connect(self._show_pairing_dialog)

        # Canvas -> Status updates
        self.canvas.cursor_moved.connect(self._on_cursor_moved)
        self.canvas.drawing_state_changed.connect(self._update_status_info)

        # Server Signals
        self.server.client_paired.connect(self._on_client_paired)
        self.server.client_disconnected.connect(self._on_client_disconnected)
        self.server.remote_stroke_started.connect(self._handle_remote_stroke_start)
        self.server.remote_stroke_points.connect(self._handle_remote_stroke_points)
        self.server.remote_stroke_ended.connect(self._handle_remote_stroke_end)
        self.server.remote_stroke_cancelled.connect(self._handle_remote_stroke_cancel)
        self.server.remote_undo.connect(self._handle_remote_undo)
        self.server.remote_redo.connect(self._handle_remote_redo)
        self.server.remote_clear.connect(self._handle_remote_clear)

        # Observe local canvas state to broadcast to phone
        self.canvas_state._on_stroke_started.append(self._on_local_stroke_started)
        self.canvas_state._on_point_added.append(self._on_local_point_added)
        self.canvas_state._on_stroke_committed.append(self._on_local_stroke_committed)
        self.canvas_state._on_stroke_cancelled.append(self._on_local_stroke_cancelled)

    def _setup_shortcuts(self) -> None:
        # Undo: Ctrl+Z
        undo_action = QAction(self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        self.addAction(undo_action)

        # Redo: Ctrl+Y and Ctrl+Shift+Z
        redo_action = QAction(self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)
        self.addAction(redo_action)

        redo_alt_action = QAction(self)
        redo_alt_action.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        redo_alt_action.triggered.connect(self.redo)
        self.addAction(redo_alt_action)

        # Clear: Ctrl+L
        clear_action = QAction(self)
        clear_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_action.triggered.connect(self.clear_canvas)
        self.addAction(clear_action)

        # Fullscreen: F11
        fullscreen_action = QAction(self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.addAction(fullscreen_action)

        # Escape exits fullscreen
        escape_action = QAction(self)
        escape_action.setShortcut(QKeySequence("Escape"))
        escape_action.triggered.connect(self._exit_fullscreen_if_active)
        self.addAction(escape_action)

        # Tool shortcuts: P (Pen), E (Eraser)
        pen_action = QAction(self)
        pen_action.setShortcut(QKeySequence("P"))
        pen_action.triggered.connect(lambda: self._select_tool(ToolType.PEN))
        self.addAction(pen_action)

        eraser_action = QAction(self)
        eraser_action.setShortcut(QKeySequence("E"))
        eraser_action.triggered.connect(lambda: self._select_tool(ToolType.ERASER))
        self.addAction(eraser_action)

        # Thickness shortcuts: 1, 2, 3, 4
        preset_shortcuts = [("1", 2.0), ("2", 4.0), ("3", 8.0), ("4", 16.0)]
        for key, size in preset_shortcuts:
            act = QAction(self)
            act.setShortcut(QKeySequence(key))
            act.triggered.connect(lambda _, s=size: self._on_thickness_changed(s))
            self.addAction(act)

    # --- Actions ---

    def _select_tool(self, tool: ToolType) -> None:
        self.toolbar.select_tool(tool)
        self._on_tool_changed(tool)

    def _on_tool_changed(self, tool: ToolType) -> None:
        self.canvas.set_tool(tool)
        self._update_status_info()

    def _on_color_changed(self, hex_color: str) -> None:
        self.canvas.set_color(hex_color)
        self._update_status_info()

    def _on_thickness_changed(self, thickness_px: float) -> None:
        if self.canvas.current_tool == ToolType.PEN:
            self.canvas.set_pen_thickness(thickness_px)
        else:
            self.canvas.set_eraser_thickness(thickness_px)
        self._update_status_info()

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def _show_pairing_dialog(self) -> None:
        if self.pairing_dialog is None:
            self.pairing_dialog = PairingDialog(
                pairing_manager=self.pairing_manager,
                port=self.server.port,
                parent=self,
            )
        self.pairing_dialog.show()
        self.pairing_dialog.raise_()
        self.pairing_dialog.activateWindow()

    def _on_client_paired(self, client_addr: str, client_name: str) -> None:
        self.toolbar.update_connection_status(True, client_name)
        if self.pairing_dialog and self.pairing_dialog.isVisible():
            self.pairing_dialog.update_connected_client(client_name, client_addr)

    def _on_client_disconnected(self, client_addr: str) -> None:
        if self.server.paired_client_count == 0:
            self.toolbar.update_connection_status(False)
            if self.pairing_dialog and self.pairing_dialog.isVisible():
                self.pairing_dialog.update_disconnected()

    # --- Remote Drawing Event Handlers ---

    def _handle_remote_stroke_start(self, data: dict) -> None:
        self._handling_remote = True
        try:
            pts = data.get("points", [])
            start_x = pts[0]["x"] if pts else None
            start_y = pts[0]["y"] if pts else None
            pressure = pts[0].get("pressure", 1.0) if pts else 1.0

            stroke = self.canvas_state.start_stroke(
                tool=ToolType.from_str(data.get("tool", "pen")),
                color=data.get("color", "#000000"),
                width=float(data.get("width", 0.004)),
                start_x=start_x,
                start_y=start_y,
                pressure=pressure,
            )
            stroke.id = data.get("stroke_id", stroke.id)
            self.canvas.update()
        finally:
            self._handling_remote = False

    def _handle_remote_stroke_points(self, data: dict) -> None:
        self._handling_remote = True
        try:
            pts = data.get("points", [])
            for p in pts:
                self.canvas_state.append_point(
                    x=float(p["x"]),
                    y=float(p["y"]),
                    timestamp=float(p.get("timestamp", 0)),
                    pressure=float(p.get("pressure", 1.0)),
                )
            self.canvas.update()
        finally:
            self._handling_remote = False

    def _handle_remote_stroke_end(self, stroke_id: str) -> None:
        self._handling_remote = True
        try:
            self.canvas_state.finish_stroke()
            self.canvas.update()
        finally:
            self._handling_remote = False

    def _handle_remote_stroke_cancel(self, stroke_id: str) -> None:
        self._handling_remote = True
        try:
            self.canvas_state.cancel_stroke()
            self.canvas.update()
        finally:
            self._handling_remote = False

    def _handle_remote_undo(self) -> None:
        self._handling_remote = True
        try:
            self.canvas_state.undo()
            self.canvas.update()
        finally:
            self._handling_remote = False

    def _handle_remote_redo(self) -> None:
        self._handling_remote = True
        try:
            self.canvas_state.redo()
            self.canvas.update()
        finally:
            self._handling_remote = False

    def _handle_remote_clear(self) -> None:
        self._handling_remote = True
        try:
            self.canvas_state.clear()
            self.canvas.update()
        finally:
            self._handling_remote = False

    # --- Local Drawing Event Broadcasts ---

    def _on_local_stroke_started(self, stroke) -> None:
        if self._handling_remote or not self.server.paired_client_count:
            return
        msg = build_stroke_start(stroke, self._next_sequence(), self.pairing_manager.session_id)
        self.server.broadcast_event(msg)

    def _on_local_point_added(self, stroke, pt) -> None:
        if self._handling_remote or not self.server.paired_client_count:
            return
        msg = build_stroke_points(stroke.id, [pt], self._next_sequence(), self.pairing_manager.session_id)
        self.server.broadcast_event(msg)

    def _on_local_stroke_committed(self, stroke) -> None:
        if self._handling_remote or not self.server.paired_client_count:
            return
        msg = build_stroke_end(stroke.id, self._next_sequence(), self.pairing_manager.session_id)
        self.server.broadcast_event(msg)

    def _on_local_stroke_cancelled(self) -> None:
        if self._handling_remote or not self.server.paired_client_count:
            return
        msg = build_stroke_cancel("", self._next_sequence(), self.pairing_manager.session_id)
        self.server.broadcast_event(msg)

    def undo(self) -> None:
        """Revert the most recent action."""
        if self.canvas_state.undo() and not self._handling_remote and self.server.paired_client_count:
            msg = build_undo(self._next_sequence(), self.pairing_manager.session_id)
            self.server.broadcast_event(msg)

    def redo(self) -> None:
        """Restore the most recently reverted action."""
        if self.canvas_state.redo() and not self._handling_remote and self.server.paired_client_count:
            msg = build_redo(self._next_sequence(), self.pairing_manager.session_id)
            self.server.broadcast_event(msg)

    def clear_canvas(self) -> None:
        """Clear all strokes from canvas with complete undo support."""
        if self.canvas_state.stroke_count == 0:
            return
        if self.canvas_state.clear() and not self._handling_remote and self.server.paired_client_count:
            msg = build_clear_canvas(self._next_sequence(), self.pairing_manager.session_id)
            self.server.broadcast_event(msg)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up background server and active ADB reverse port mappings on shutdown."""
        if self.server and self.server.is_running:
            self.server.stop()
        try:
            AdbManager().remove_reverse_port(port=self.server.port if self.server else 8765)
        except Exception:
            pass
        super().closeEvent(event)

    def toggle_fullscreen(self) -> None:
        """Toggle distraction-free presentation mode."""
        if self.isFullScreen():
            self.showNormal()
            self.toolbar.fullscreen_btn.setText("⛶ Fullscreen")
        else:
            self.showFullScreen()
            self.toolbar.fullscreen_btn.setText("🗗 Windowed")

    def _exit_fullscreen_if_active(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.toolbar.fullscreen_btn.setText("⛶ Fullscreen")

    def _on_cursor_moved(self, norm_x: float, norm_y: float, wx: float, wy: float) -> None:
        pct_x = int(norm_x * 100)
        pct_y = int(norm_y * 100)
        self.coord_label.setText(f"{pct_x}% {pct_y}% ({int(wx)}, {int(wy)})")

    def _update_status_info(self) -> None:
        # Update toolbar undo/redo buttons
        self.toolbar.update_history_state(
            can_undo=self.canvas_state.can_undo,
            can_redo=self.canvas_state.can_redo,
        )

        # Update stroke count
        cnt = self.canvas_state.stroke_count
        self.stroke_count_label.setText(f"Strokes: {cnt}")

        # Update tool info
        tool = "Pen" if self.canvas.current_tool == ToolType.PEN else "Eraser"
        thick = int(self.canvas.active_thickness_px)
        color = self.canvas.current_color if self.canvas.current_tool == ToolType.PEN else "Eraser"
        self.tool_info_label.setText(f"Tool: {tool} ({thick}px, {color})")

    def _apply_styling(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F172A;
            }
        """)
