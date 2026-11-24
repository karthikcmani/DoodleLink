"""Main application window for DoodleLink Whiteboard."""

from __future__ import annotations

from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from doodlelink.export.exporter import export_board_to_pdf, export_page_to_png
from doodlelink.models.canvas_state import CanvasState
from doodlelink.models.coordinate import CoordinateMapper, LogicalCanvas
from doodlelink.models.multi_page import MultiPageDocument
from doodlelink.models.stroke import ToolType
from doodlelink.network.adb_manager import AdbManager
from doodlelink.network.pairing import PairingManager
from doodlelink.network.protocol import (
    build_clear_canvas,
    build_page_info,
    build_redo,
    build_stroke_cancel,
    build_stroke_end,
    build_stroke_points,
    build_stroke_start,
    build_undo,
)
from doodlelink.network.server import WhiteboardServer
from doodlelink.ui.board_dialog import BoardManagementDialog
from doodlelink.ui.canvas_widget import CanvasWidget
from doodlelink.ui.page_panel import PagePanel
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
        self.resize(1280, 800)
        self.setMinimumSize(800, 500)

        # Core logic models & persistence
        if canvas_state is not None:
            # Standalone test mode
            self.doc: MultiPageDocument | None = None
            self.canvas_state = canvas_state
            self.setWindowTitle("DoodleLink — Smart Whiteboard")
        else:
            self.doc = MultiPageDocument.load_or_create_default()
            self.canvas_state = self.doc.active_canvas_state
            self.setWindowTitle(f"DoodleLink — {self.doc.board.title}")

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

        # Bottom Page Panel
        self.page_panel = PagePanel(self)
        root_layout.addWidget(self.page_panel)

        # Status Bar
        self._setup_status_bar()

        # Connect Toolbar, Page Panel, Canvas, and Server Signals
        self._connect_signals()

        # Start WebSocket Host Server
        self.server.start(host="0.0.0.0", port=8765)

        # Setup Keyboard Shortcuts
        self._setup_shortcuts()

        # Apply Window Styling
        self._apply_styling()

        # Initial UI synchronization
        self._update_status_info()
        self._update_page_panel()

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
        hint_label = QLabel("P: Pen | E: Eraser | F11: Fullscreen | Ctrl+B: Boards | Ctrl+Z: Undo")
        hint_label.setStyleSheet("color: #6B7280; font-size: 10px;")
        self.status_bar.addPermanentWidget(hint_label)

    def _connect_signals(self) -> None:
        # Toolbar -> Canvas & Actions
        self.toolbar.tool_changed.connect(self._on_tool_changed)
        self.toolbar.color_changed.connect(self._on_color_changed)
        self.toolbar.thickness_changed.connect(self._on_thickness_changed)
        self.toolbar.undo_requested.connect(self.undo)
        self.toolbar.redo_requested.connect(self.redo)
        self.toolbar.clear_requested.connect(self.clear_canvas)
        self.toolbar.fullscreen_requested.connect(self.toggle_fullscreen)
        self.toolbar.pair_requested.connect(self._show_pairing_dialog)
        self.toolbar.boards_requested.connect(self.open_board_dialog)
        self.toolbar.export_requested.connect(self.show_export_menu)

        # Page Panel Signals
        self.page_panel.page_prev_requested.connect(self.prev_page)
        self.page_panel.page_next_requested.connect(self.next_page)
        self.page_panel.page_add_requested.connect(self.add_page)
        self.page_panel.page_duplicate_requested.connect(self.duplicate_page)
        self.page_panel.page_delete_requested.connect(self.delete_page)

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
        self.server.remote_page_switch.connect(self._handle_remote_page_switch)

        # Observe local canvas state to broadcast to phone
        self._bind_canvas_state_observers(self.canvas_state)

    def _bind_canvas_state_observers(self, state: CanvasState) -> None:
        """Bind network broadcast callbacks to a CanvasState."""
        state._on_stroke_started.append(self._on_local_stroke_started)
        state._on_point_added.append(self._on_local_point_added)
        state._on_stroke_committed.append(self._on_local_stroke_committed)
        state._on_stroke_cancelled.append(self._on_local_stroke_cancelled)

    def _unbind_canvas_state_observers(self, state: CanvasState) -> None:
        """Unbind network broadcast callbacks from a CanvasState."""
        if self._on_local_stroke_started in state._on_stroke_started:
            state._on_stroke_started.remove(self._on_local_stroke_started)
        if self._on_local_point_added in state._on_point_added:
            state._on_point_added.remove(self._on_local_point_added)
        if self._on_local_stroke_committed in state._on_stroke_committed:
            state._on_stroke_committed.remove(self._on_local_stroke_committed)
        if self._on_local_stroke_cancelled in state._on_stroke_cancelled:
            state._on_stroke_cancelled.remove(self._on_local_stroke_cancelled)

    def _set_active_canvas_state(self, new_state: CanvasState) -> None:
        """Switch active canvas state for the canvas widget and broadcast observers."""
        if self.canvas_state != new_state:
            self._unbind_canvas_state_observers(self.canvas_state)
            self.canvas_state = new_state
            self._bind_canvas_state_observers(self.canvas_state)
            self.canvas.set_canvas_state(new_state)
            self._update_status_info()

    def _update_page_panel(self) -> None:
        if self.doc:
            self.page_panel.update_page_info(self.doc.current_page_number, self.doc.page_count)
        else:
            self.page_panel.update_page_info(1, 1)

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

        # Manage Boards: Ctrl+B
        boards_action = QAction(self)
        boards_action.setShortcut(QKeySequence("Ctrl+B"))
        boards_action.triggered.connect(self.open_board_dialog)
        self.addAction(boards_action)

        # Export PNG: Ctrl+E
        export_png_action = QAction(self)
        export_png_action.setShortcut(QKeySequence("Ctrl+E"))
        export_png_action.triggered.connect(self.export_page_png)
        self.addAction(export_png_action)

        # Export PDF: Ctrl+Shift+E
        export_pdf_action = QAction(self)
        export_pdf_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_pdf_action.triggered.connect(self.export_board_pdf)
        self.addAction(export_pdf_action)

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
        # Authoritative state broadcast on connection
        self._broadcast_page_info()

    def _on_client_disconnected(self, client_addr: str) -> None:
        if self.server.paired_client_count == 0:
            self.toolbar.update_connection_status(False)
            if self.pairing_dialog and self.pairing_dialog.isVisible():
                self.pairing_dialog.update_disconnected()

    def _broadcast_page_info(self) -> None:
        """Broadcast authoritative page state and strokes to all paired devices."""
        if not self.server.paired_client_count or not self.doc:
            return
        msg = build_page_info(
            board_id=self.doc.board.id,
            page_id=self.doc.active_page_id,
            page_number=self.doc.current_page_number,
            total_pages=self.doc.page_count,
            strokes=self.doc.active_canvas_state.strokes,
            sequence=self._next_sequence(),
            session_id=self.pairing_manager.session_id,
        )
        self.server.broadcast_event(msg)

    # --- Multi-Page Navigation Operations ---

    def prev_page(self) -> None:
        if self.doc and self.doc.prev_page():
            self._set_active_canvas_state(self.doc.active_canvas_state)
            self._update_page_panel()
            self._broadcast_page_info()

    def next_page(self) -> None:
        if self.doc and self.doc.next_page():
            self._set_active_canvas_state(self.doc.active_canvas_state)
            self._update_page_panel()
            self._broadcast_page_info()

    def add_page(self) -> None:
        if self.doc:
            self.doc.add_page()
            self._set_active_canvas_state(self.doc.active_canvas_state)
            self._update_page_panel()
            self._broadcast_page_info()

    def duplicate_page(self) -> None:
        if self.doc:
            self.doc.duplicate_current_page()
            self._set_active_canvas_state(self.doc.active_canvas_state)
            self._update_page_panel()
            self._broadcast_page_info()

    def delete_page(self) -> None:
        if not self.doc or self.doc.page_count <= 1:
            return

        reply = QMessageBox.question(
            self,
            "Delete Page",
            f"Are you sure you want to delete Page {self.doc.current_page_number}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.doc.delete_current_page():
                self._set_active_canvas_state(self.doc.active_canvas_state)
                self._update_page_panel()
                self._broadcast_page_info()

    # --- Board Management ---

    def open_board_dialog(self) -> None:
        if not self.doc:
            return
        dlg = BoardManagementDialog(
            repository=self.doc.repository,
            current_board_id=self.doc.board.id,
            parent=self,
        )
        dlg.board_selected.connect(self._switch_board)
        dlg.exec()

    def _switch_board(self, board_id: str) -> None:
        if not self.doc or self.doc.board.id == board_id:
            return
        self.doc.save_current_page()
        board = self.doc.repository.get_board(board_id)
        if not board:
            return
        self.doc = MultiPageDocument(board=board, repository=self.doc.repository)
        self.setWindowTitle(f"DoodleLink — {self.doc.board.title}")
        self._set_active_canvas_state(self.doc.active_canvas_state)
        self._update_page_panel()
        self._broadcast_page_info()

    # --- Exporting ---

    def show_export_menu(self) -> None:
        menu = QMenu(self)
        act_png_white = menu.addAction("Export Page as PNG (White Background)")
        act_png_trans = menu.addAction("Export Page as PNG (Transparent Background)")
        menu.addSeparator()
        act_pdf = menu.addAction("Export Entire Board as PDF")

        action = menu.exec(self.toolbar.export_btn.mapToGlobal(self.toolbar.export_btn.rect().bottomLeft()))
        if action == act_png_white:
            self.export_page_png(transparent=False)
        elif action == act_png_trans:
            self.export_page_png(transparent=True)
        elif action == act_pdf:
            self.export_board_pdf()

    def export_page_png(self, transparent: bool = False) -> None:
        page_num = self.doc.current_page_number if self.doc else 1
        default_name = f"whiteboard_page_{page_num}.png"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Page as PNG",
            default_name,
            "PNG Images (*.png)",
        )
        if path:
            ok = export_page_to_png(self.canvas_state, path, transparent=transparent)
            if ok:
                QMessageBox.information(self, "Export Succeeded", f"Page exported successfully to:\n{path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Could not save PNG file.")

    def export_board_pdf(self) -> None:
        if not self.doc:
            return
        title_sanitized = "".join(c for c in self.doc.board.title if c.isalnum() or c in (" ", "-", "_")).strip()
        default_name = f"{title_sanitized or 'board'}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Board as PDF",
            default_name,
            "PDF Files (*.pdf)",
        )
        if path:
            ok = export_board_to_pdf(self.doc, path)
            if ok:
                QMessageBox.information(self, "Export Succeeded", f"Board exported successfully to:\n{path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Could not generate PDF file.")

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

    def _handle_remote_page_switch(self, data: dict) -> None:
        direction = data.get("direction")
        if direction == "next":
            self.next_page()
        elif direction == "prev":
            self.prev_page()
        elif direction == "add":
            self.add_page()
        elif direction == "goto":
            target_id = data.get("page_id")
            if target_id and self.doc and self.doc.switch_page(target_id):
                self._set_active_canvas_state(self.doc.active_canvas_state)
                self._update_page_panel()
                self._broadcast_page_info()

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
        if self.doc:
            self.doc.save_current_page()
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
