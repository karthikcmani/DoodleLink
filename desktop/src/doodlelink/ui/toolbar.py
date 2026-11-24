"""Modern application toolbar for DoodleLink Whiteboard."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

from doodlelink.models.stroke import ToolType
from doodlelink.ui.color_palette import ColorPalette


class WhiteboardToolbar(QFrame):
    """Clean, modern toolbar hosting drawing tools, color swatches, thickness, and actions."""

    tool_changed = Signal(ToolType)
    color_changed = Signal(str)
    thickness_changed = Signal(float)
    undo_requested = Signal()
    redo_requested = Signal()
    clear_requested = Signal()
    fullscreen_requested = Signal()
    pair_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("whiteboardToolbar")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(12)

        # 1. Tool Selection (Pen vs Eraser)
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        self.pen_btn = QPushButton("✏️ Pen")
        self.pen_btn.setCheckable(True)
        self.pen_btn.setChecked(True)
        self.pen_btn.setToolTip("Pen Tool (P)")
        self.tool_group.addButton(self.pen_btn)
        main_layout.addWidget(self.pen_btn)

        self.eraser_btn = QPushButton("🧹 Eraser")
        self.eraser_btn.setCheckable(True)
        self.eraser_btn.setToolTip("Eraser Tool (E)")
        self.tool_group.addButton(self.eraser_btn)
        main_layout.addWidget(self.eraser_btn)

        self.pen_btn.clicked.connect(lambda: self.tool_changed.emit(ToolType.PEN))
        self.eraser_btn.clicked.connect(lambda: self.tool_changed.emit(ToolType.ERASER))

        main_layout.addWidget(self._create_separator())

        # 2. Color Palette
        self.color_palette = ColorPalette(initial_color="#111827", parent=self)
        self.color_palette.color_selected.connect(self.color_changed.emit)
        main_layout.addWidget(self.color_palette)

        main_layout.addWidget(self._create_separator())

        # 3. Brush Thickness Controls
        thickness_container = QWidget(self)
        thick_layout = QHBoxLayout(thickness_container)
        thick_layout.setContentsMargins(0, 0, 0, 0)
        thick_layout.setSpacing(6)

        thick_label = QLabel("Size:")
        thick_label.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 500;")
        thick_layout.addWidget(thick_label)

        # Preset chips
        self.preset_group = QButtonGroup(self)
        self.preset_group.setExclusive(True)
        self.presets = [
            ("2", 2.0, "Fine"),
            ("4", 4.0, "Medium"),
            ("8", 8.0, "Thick"),
            ("16", 16.0, "Marker"),
        ]
        self._preset_buttons: dict[float, QPushButton] = {}

        for label, val, tip in self.presets:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedSize(26, 26)
            btn.setToolTip(f"{tip} ({val}px)")
            if val == 4.0:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, v=val: self._on_preset_clicked(v))
            self.preset_group.addButton(btn)
            self._preset_buttons[val] = btn
            thick_layout.addWidget(btn)

        # Slider for fine-grained thickness
        self.thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.thickness_slider.setRange(1, 50)
        self.thickness_slider.setValue(4)
        self.thickness_slider.setFixedWidth(80)
        self.thickness_slider.setToolTip("Adjust brush thickness (1 - 50 px)")
        self.thickness_slider.valueChanged.connect(self._on_slider_changed)
        thick_layout.addWidget(self.thickness_slider)

        self.thickness_val_label = QLabel("4px")
        self.thickness_val_label.setFixedWidth(32)
        self.thickness_val_label.setStyleSheet("color: #E5E7EB; font-size: 11px; font-family: monospace;")
        thick_layout.addWidget(self.thickness_val_label)

        main_layout.addWidget(thickness_container)

        main_layout.addWidget(self._create_separator())

        # 4. Undo / Redo / Clear Actions
        self.undo_btn = QPushButton("↩ Undo")
        self.undo_btn.setToolTip("Undo last action (Ctrl+Z)")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo_requested.emit)
        main_layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("↪ Redo")
        self.redo_btn.setToolTip("Redo undone action (Ctrl+Y)")
        self.redo_btn.setEnabled(False)
        self.redo_btn.clicked.connect(self.redo_requested.emit)
        main_layout.addWidget(self.redo_btn)

        self.clear_btn = QPushButton("🗑 Clear")
        self.clear_btn.setToolTip("Clear whiteboard (Ctrl+L)")
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        main_layout.addWidget(self.clear_btn)

        main_layout.addStretch()

        # 5. Connect Phone Button
        self.pair_btn = QPushButton("📱 Connect Phone")
        self.pair_btn.setToolTip("Show host IP and pairing code to connect Android device")
        self.pair_btn.clicked.connect(self.pair_requested.emit)
        main_layout.addWidget(self.pair_btn)

        # 6. Fullscreen Toggle
        self.fullscreen_btn = QPushButton("⛶ Fullscreen")
        self.fullscreen_btn.setToolTip("Toggle distraction-free presentation mode (F11)")
        self.fullscreen_btn.clicked.connect(self.fullscreen_requested.emit)
        main_layout.addWidget(self.fullscreen_btn)

        # 7. Connection Status Badge (clickable)
        self.status_badge = QPushButton("● Wi-Fi: Ready")
        self.status_badge.setToolTip("Click to view pairing code and connection details")
        self.status_badge.clicked.connect(self.pair_requested.emit)
        main_layout.addWidget(self.status_badge)

        self._apply_toolbar_styling()

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #374151; max-width: 1px; margin: 4px 2px;")
        return sep

    def _on_preset_clicked(self, val: float) -> None:
        self.thickness_slider.blockSignals(True)
        self.thickness_slider.setValue(int(val))
        self.thickness_slider.blockSignals(False)
        self.thickness_val_label.setText(f"{int(val)}px")
        self.thickness_changed.emit(val)

    def _on_slider_changed(self, val: int) -> None:
        self.thickness_val_label.setText(f"{val}px")
        # Uncheck presets if slider doesn't match any preset
        matched = False
        for p_val, btn in self._preset_buttons.items():
            if int(p_val) == val:
                btn.setChecked(True)
                matched = True
                break
        if not matched:
            self.preset_group.setExclusive(False)
            for btn in self._preset_buttons.values():
                btn.setChecked(False)
            self.preset_group.setExclusive(True)

        self.thickness_changed.emit(float(val))

    def update_history_state(self, can_undo: bool, can_redo: bool) -> None:
        """Update enabled state of Undo and Redo buttons."""
        self.undo_btn.setEnabled(can_undo)
        self.redo_btn.setEnabled(can_redo)

    def update_connection_status(self, is_connected: bool, client_name: str = "") -> None:
        """Update the connection status badge."""
        if is_connected:
            name = client_name or "Android Phone"
            self.status_badge.setText(f"● Connected: {name}")
            self.status_badge.setStyleSheet("""
                QPushButton {
                    color: #10B981;
                    background-color: rgba(16, 185, 129, 0.15);
                    border: 1px solid rgba(16, 185, 129, 0.4);
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(16, 185, 129, 0.25);
                }
            """)
        else:
            self.status_badge.setText("● Wi-Fi: Ready")
            self.status_badge.setStyleSheet("""
                QPushButton {
                    color: #38BDF8;
                    background-color: rgba(56, 189, 248, 0.12);
                    border: 1px solid rgba(56, 189, 248, 0.35);
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.22);
                }
            """)

    def select_tool(self, tool: ToolType) -> None:
        """Select tool visually in toolbar."""
        if tool == ToolType.PEN:
            self.pen_btn.setChecked(True)
        else:
            self.eraser_btn.setChecked(True)

    def _apply_toolbar_styling(self) -> None:
        self.setStyleSheet("""
            #whiteboardToolbar {
                background-color: #111827;
                border-bottom: 1px solid #1F2937;
            }
            QPushButton {
                background-color: #1F2937;
                color: #E5E7EB;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #374151;
                border-color: #4B5563;
            }
            QPushButton:checked {
                background-color: #2563EB;
                color: #FFFFFF;
                border-color: #3B82F6;
            }
            QPushButton:disabled {
                background-color: #111827;
                color: #4B5563;
                border-color: #1F2937;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #374151;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #3B82F6;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #F9FAFB;
                border: 1px solid #6B7280;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
        """)
