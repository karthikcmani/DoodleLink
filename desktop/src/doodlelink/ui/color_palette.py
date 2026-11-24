"""Color selection palette and custom color dialog integration."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QPushButton,
    QWidget,
)


class ColorPalette(QWidget):
    """Horizontal color swatch bar for quick palette selection and custom color picking."""

    color_selected = Signal(str)

    DEFAULT_COLORS = [
        ("#111827", "Black"),
        ("#4B5563", "Slate"),
        ("#DC2626", "Red"),
        ("#2563EB", "Blue"),
        ("#16A34A", "Green"),
        ("#D97706", "Amber"),
        ("#EA580C", "Orange"),
        ("#9333EA", "Purple"),
        ("#0891B2", "Cyan"),
        ("#DB2777", "Pink"),
    ]

    def __init__(self, initial_color: str = "#111827", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.selected_color = initial_color
        self._buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for hex_code, name in self.DEFAULT_COLORS:
            btn = QPushButton()
            btn.setFixedSize(QSize(24, 24))
            btn.setToolTip(f"{name} ({hex_code})")
            btn.setCursor(btn.cursor())
            btn.clicked.connect(lambda _, c=hex_code: self.select_color(c))
            self._buttons[hex_code.upper()] = btn
            layout.addWidget(btn)

        # Custom color picker button
        self.custom_btn = QPushButton("🎨")
        self.custom_btn.setFixedSize(QSize(28, 24))
        self.custom_btn.setToolTip("Pick custom color...")
        self.custom_btn.clicked.connect(self._open_color_dialog)
        layout.addWidget(self.custom_btn)

        self._refresh_styles()

    def select_color(self, hex_code: str) -> None:
        """Select a color and notify subscribers."""
        self.selected_color = hex_code.upper()
        self._refresh_styles()
        self.color_selected.emit(self.selected_color)

    def _open_color_dialog(self) -> None:
        initial = QColor(self.selected_color)
        chosen = QColorDialog.getColor(initial, self, "Select Stroke Color")
        if chosen.isValid():
            self.select_color(chosen.name().upper())

    def _refresh_styles(self) -> None:
        """Apply active border styling to the currently selected color."""
        for hex_code, btn in self._buttons.items():
            is_active = (hex_code == self.selected_color)
            border = "3px solid #38BDF8" if is_active else "1px solid rgba(255,255,255,0.25)"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_code};
                    border: {border};
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border: 2px solid #FFFFFF;
                }}
            """)

        custom_border = "2px solid #38BDF8" if self.selected_color not in self._buttons else "1px solid #4B5563"
        self.custom_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #374151;
                color: #F9FAFB;
                border: {custom_border};
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #4B5563;
                border: 2px solid #38BDF8;
            }}
        """)
