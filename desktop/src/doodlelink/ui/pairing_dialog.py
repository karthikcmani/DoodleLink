"""Pairing and connection dialog for DoodleLink Desktop Host."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from doodlelink.network.pairing import PairingManager


class PairingDialog(QDialog):
    """Dialog displaying host connection IP, port, and 6-digit pairing code."""

    def __init__(self, pairing_manager: PairingManager, port: int = 8765, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pairing_manager = pairing_manager
        self.port = port

        self.setWindowTitle("Connect Android Phone — DoodleLink")
        self.setFixedSize(460, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title_label = QLabel("Connect Android Tablet / Phone")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #F9FAFB;")
        layout.addWidget(title_label)

        sub_label = QLabel(
            "Open DoodleLink on your Android phone, tap 'Connect', and enter the IP and 6-digit pairing code below."
        )
        sub_label.setWordWrap(True)
        sub_label.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        layout.addWidget(sub_label)

        # Info Box Card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        # Host IP
        ip_row = QHBoxLayout()
        ip_title = QLabel("Host IP Address:")
        ip_title.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 500;")
        ip_row.addWidget(ip_title)

        primary_ip = self.pairing_manager.get_primary_ip()
        self.ip_value = QLabel(primary_ip)
        self.ip_value.setStyleSheet("color: #60A5FA; font-size: 14px; font-family: monospace; font-weight: bold;")
        ip_row.addWidget(self.ip_value)
        ip_row.addStretch()
        card_layout.addLayout(ip_row)

        # Port
        port_row = QHBoxLayout()
        port_title = QLabel("Port:")
        port_title.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 500;")
        port_row.addWidget(port_title)

        port_val = QLabel(str(self.port))
        port_val.setStyleSheet("color: #E5E7EB; font-size: 14px; font-family: monospace;")
        port_row.addWidget(port_val)
        port_row.addStretch()
        card_layout.addLayout(port_row)

        card_layout.addWidget(self._create_divider())

        # Pairing Code
        code_title = QLabel("PAIRING CODE")
        code_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_title.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: 600; letter-spacing: 1px;")
        card_layout.addWidget(code_title)

        self.code_label = QLabel(self._format_code(self.pairing_manager.current_code))
        self.code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_label.setStyleSheet("""
            color: #38BDF8;
            font-size: 32px;
            font-family: monospace;
            font-weight: bold;
            letter-spacing: 4px;
            padding: 4px;
        """)
        card_layout.addWidget(self.code_label)

        # New Code Button
        new_code_btn = QPushButton("Generate New Code")
        new_code_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_code_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        new_code_btn.clicked.connect(self._regenerate_code)
        card_layout.addWidget(new_code_btn)

        layout.addWidget(card)

        # Connected Device Status
        self.status_label = QLabel("Waiting for phone to connect...")
        self.status_label.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Done")
        close_btn.setFixedSize(100, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._apply_dialog_styling()

    def _create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #374151; max-height: 1px;")
        return line

    def _format_code(self, code: str) -> str:
        if len(code) == 6:
            return f"{code[:3]} {code[3:]}"
        return code

    def _regenerate_code(self) -> None:
        new_code = self.pairing_manager.generate_new_code()
        self.code_label.setText(self._format_code(new_code))

    def update_connected_client(self, client_name: str, client_ip: str) -> None:
        self.status_label.setText(f"✓ Connected: {client_name} ({client_ip})")
        self.status_label.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")

    def update_disconnected(self) -> None:
        self.status_label.setText("Waiting for phone to connect...")
        self.status_label.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: 500;")

    def _apply_dialog_styling(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #111827;
            }
        """)
