"""Board management dialog for creating, opening, renaming, and deleting whiteboard boards."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from doodlelink.storage.board_repository import BoardMetadata, BoardRepository


class BoardManagementDialog(QDialog):
    """Dialog allowing users to manage boards: view recent boards, switch, rename, or delete."""

    board_selected = Signal(str)  # Emits board_id to open

    def __init__(self, repository: BoardRepository, current_board_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repository = repository
        self.current_board_id = current_board_id
        self._boards: list[BoardMetadata] = []

        self.setWindowTitle("Manage Whiteboard Boards — DoodleLink")
        self.setMinimumSize(600, 380)
        self.setModal(True)

        self._init_ui()
        self._load_boards()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Table of boards
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Title", "Pages", "Last Modified", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._on_open_clicked)
        layout.addWidget(self.table)

        # Buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_new = QPushButton("+ New Board")
        self.btn_new.clicked.connect(self._on_new_board)
        btn_layout.addWidget(self.btn_new)

        self.btn_rename = QPushButton("Rename")
        self.btn_rename.clicked.connect(self._on_rename_board)
        btn_layout.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet("QPushButton:hover { background-color: #BF616A; color: white; }")
        self.btn_delete.clicked.connect(self._on_delete_board)
        btn_layout.addWidget(self.btn_delete)

        btn_layout.addStretch()

        self.btn_open = QPushButton("Open Board")
        self.btn_open.setDefault(True)
        self.btn_open.setStyleSheet("background-color: #88C0D0; color: #2E3440; font-weight: bold;")
        self.btn_open.clicked.connect(self._on_open_clicked)
        btn_layout.addWidget(self.btn_open)

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        self.setStyleSheet("""
            QDialog {
                background-color: #2E3440;
                color: #ECEFF4;
            }
            QTableWidget {
                background-color: #3B4252;
                color: #ECEFF4;
                gridline-color: #4C566A;
                border: 1px solid #4C566A;
                border-radius: 4px;
                selection-background-color: #434C5E;
                selection-color: #88C0D0;
            }
            QHeaderView::section {
                background-color: #2E3440;
                color: #D8DEE9;
                padding: 6px;
                border: 1px solid #4C566A;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3B4252;
                color: #ECEFF4;
                border: 1px solid #4C566A;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #434C5E;
                border-color: #88C0D0;
            }
        """)

    def _load_boards(self) -> None:
        self._boards = self.repository.list_boards()
        self.table.setRowCount(len(self._boards))

        current_row = -1
        for idx, b in enumerate(self._boards):
            item_title = QTableWidgetItem(b.title)
            item_pages = QTableWidgetItem(str(b.page_count))
            item_pages.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            dt = datetime.datetime.fromtimestamp(b.updated_at)
            item_date = QTableWidgetItem(dt.strftime("%Y-%m-%d %H:%M"))
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            is_curr = b.id == self.current_board_id
            status_text = "● Active" if is_curr else ""
            item_status = QTableWidgetItem(status_text)
            if is_curr:
                item_status.setForeground(Qt.GlobalColor.green)
                current_row = idx

            self.table.setItem(idx, 0, item_title)
            self.table.setItem(idx, 1, item_pages)
            self.table.setItem(idx, 2, item_date)
            self.table.setItem(idx, 3, item_status)

        if current_row >= 0:
            self.table.selectRow(current_row)
        elif len(self._boards) > 0:
            self.table.selectRow(0)

    def _get_selected_board(self) -> BoardMetadata | None:
        row = self.table.currentRow()
        if 0 <= row < len(self._boards):
            return self._boards[row]
        return None

    def _on_new_board(self) -> None:
        title, ok = QInputDialog.getText(
            self,
            "Create New Board",
            "Enter board title:",
            text=f"Board {len(self._boards) + 1}",
        )
        if ok and title.strip():
            new_board = self.repository.create_board(title=title.strip())
            self.current_board_id = new_board.id
            self._load_boards()
            self.board_selected.emit(new_board.id)
            self.accept()

    def _on_rename_board(self) -> None:
        board = self._get_selected_board()
        if not board:
            return
        new_title, ok = QInputDialog.getText(
            self,
            "Rename Board",
            "Enter new board title:",
            text=board.title,
        )
        if ok and new_title.strip():
            self.repository.rename_board(board.id, new_title.strip())
            self._load_boards()

    def _on_delete_board(self) -> None:
        board = self._get_selected_board()
        if not board:
            return

        if len(self._boards) <= 1:
            QMessageBox.warning(
                self,
                "Cannot Delete Board",
                "You cannot delete the only existing board. Create another board first.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to permanently delete board '{board.title}' and all its {board.page_count} page(s)?\n\nThis operation cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.repository.delete_board(board.id)
            if self.current_board_id == board.id:
                # Switch to first remaining board
                remaining = self.repository.list_boards()
                if remaining:
                    self.current_board_id = remaining[0].id
                    self.board_selected.emit(remaining[0].id)
            self._load_boards()

    def _on_open_clicked(self) -> None:
        board = self._get_selected_board()
        if board:
            self.board_selected.emit(board.id)
            self.accept()
