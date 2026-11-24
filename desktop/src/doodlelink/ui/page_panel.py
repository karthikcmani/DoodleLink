"""Page navigation and management panel for multi-page whiteboard."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class PagePanel(QWidget):
    """Bottom navigation strip for multi-page whiteboard navigation and operations."""

    page_prev_requested = Signal()
    page_next_requested = Signal()
    page_add_requested = Signal()
    page_duplicate_requested = Signal()
    page_delete_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # 1. Navigation controls (left / center)
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setToolTip("Previous Page (Left Arrow)")
        self.btn_prev.setFixedWidth(36)
        self.btn_prev.clicked.connect(self.page_prev_requested.emit)
        layout.addWidget(self.btn_prev)

        self.lbl_page_info = QLabel("Page 1 of 1")
        self.lbl_page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page_info.setStyleSheet("font-weight: bold; font-size: 13px; color: #ECEFF4; min-width: 100px;")
        layout.addWidget(self.lbl_page_info)

        self.btn_next = QPushButton("▶")
        self.btn_next.setToolTip("Next Page (Right Arrow)")
        self.btn_next.setFixedWidth(36)
        self.btn_next.clicked.connect(self.page_next_requested.emit)
        layout.addWidget(self.btn_next)

        layout.addSpacing(16)

        # 2. Page Action buttons
        self.btn_add = QPushButton("+ Add Page")
        self.btn_add.setToolTip("Create a new blank page at the end")
        self.btn_add.clicked.connect(self.page_add_requested.emit)
        layout.addWidget(self.btn_add)

        self.btn_duplicate = QPushButton("❐ Duplicate")
        self.btn_duplicate.setToolTip("Duplicate current page with all strokes")
        self.btn_duplicate.clicked.connect(self.page_duplicate_requested.emit)
        layout.addWidget(self.btn_duplicate)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setToolTip("Delete current page")
        self.btn_delete.setStyleSheet("QPushButton:hover { background-color: #BF616A; color: #FFFFFF; }")
        self.btn_delete.clicked.connect(self.page_delete_requested.emit)
        layout.addWidget(self.btn_delete)

        layout.addStretch()

        self.setStyleSheet("""
            QWidget {
                background-color: #2E3440;
                border-top: 1px solid #3B4252;
            }
            QPushButton {
                background-color: #3B4252;
                color: #ECEFF4;
                border: 1px solid #4C566A;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #434C5E;
                border-color: #88C0D0;
            }
            QPushButton:pressed {
                background-color: #4C566A;
            }
            QPushButton:disabled {
                background-color: #2E3440;
                color: #4C566A;
                border-color: #3B4252;
            }
        """)

    def update_page_info(self, current_page: int, total_pages: int) -> None:
        """Update navigation button enabled states and page label text."""
        self.lbl_page_info.setText(f"Page {current_page} of {total_pages}")
        self.btn_prev.setEnabled(current_page > 1)
        self.btn_next.setEnabled(current_page < total_pages)
        self.btn_delete.setEnabled(total_pages > 1)
