"""Pairing and connection dialog supporting Wi-Fi, Phone Hotspot, and USB ADB Reverse modes."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from doodlelink.network.adb_manager import AdbManager
from doodlelink.network.network_diagnostics import NetworkDiagnostics
from doodlelink.network.pairing import PairingManager


class PairingDialog(QDialog):
    """Dialog providing connection parameters, Wi-Fi/Hotspot interface selection, and USB ADB Reverse setup."""

    def __init__(
        self,
        pairing_manager: PairingManager,
        port: int = 8765,
        adb_manager: AdbManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.pairing_manager = pairing_manager
        self.port = port
        self.adb_manager = adb_manager or AdbManager()

        self.setWindowTitle("Connect Android Device — DoodleLink")
        self.setFixedSize(540, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(14)

        # Header Title
        title_label = QLabel("Connect Android Phone / Tablet")
        title_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #F9FAFB;")
        root_layout.addWidget(title_label)

        # Tab Widget
        self.tabs = QTabWidget(self)
        root_layout.addWidget(self.tabs, 1)

        # Build Tabs
        self.tabs.addTab(self._create_wifi_tab(), "📶 Wi-Fi / Hotspot")
        self.tabs.addTab(self._create_usb_tab(), "🔌 USB Cable (ADB)")
        self.tabs.addTab(self._create_diag_tab(), "🔍 Diagnostics")

        # Bottom row: Connection Status & Done Button
        bottom_layout = QHBoxLayout()
        self.status_label = QLabel("Waiting for phone to connect...")
        self.status_label.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: 500;")
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()

        done_btn = QPushButton("Done")
        done_btn.setFixedSize(90, 32)
        done_btn.setStyleSheet("""
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
        done_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(done_btn)
        root_layout.addLayout(bottom_layout)

        self._apply_dialog_styling()

    # --- TAB 1: Wi-Fi & Hotspot ---

    def _create_wifi_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        desc = QLabel(
            "Phone and PC must be on the same local network. If external Wi-Fi is unavailable, "
            "turn on Portable Hotspot on your phone and connect your PC to it."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout.addWidget(desc)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 14px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        # IP Selection Dropdown
        ip_row = QHBoxLayout()
        ip_label = QLabel("Host IP Address:")
        ip_label.setStyleSheet("color: #D1D5DB; font-size: 12px; font-weight: 500;")
        ip_row.addWidget(ip_label)

        self.ip_combo = QComboBox()
        self.ip_combo.setStyleSheet("""
            QComboBox {
                background-color: #111827;
                color: #60A5FA;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 4px 8px;
                font-family: monospace;
                font-weight: bold;
                min-width: 220px;
            }
        """)
        self._populate_ip_combo()
        ip_row.addWidget(self.ip_combo)
        ip_row.addStretch()
        card_layout.addLayout(ip_row)

        # Port
        port_row = QHBoxLayout()
        port_title = QLabel("Port:")
        port_title.setStyleSheet("color: #D1D5DB; font-size: 12px; font-weight: 500;")
        port_row.addWidget(port_title)

        port_val = QLabel(str(self.port))
        port_val.setStyleSheet("color: #E5E7EB; font-size: 13px; font-family: monospace;")
        port_row.addWidget(port_val)
        port_row.addStretch()
        card_layout.addLayout(port_row)

        card_layout.addWidget(self._create_divider())

        # Pairing Code
        code_title = QLabel("6-DIGIT PAIRING CODE")
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
        """)
        card_layout.addWidget(self.code_label)

        new_code_btn = QPushButton("Generate New Code")
        new_code_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #4B5563; }
        """)
        new_code_btn.clicked.connect(self._regenerate_code)
        card_layout.addWidget(new_code_btn)

        layout.addWidget(card)
        layout.addStretch()
        return widget

    # --- TAB 2: USB Cable (ADB Reverse) ---

    def _create_usb_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        desc = QLabel(
            "Wired USB mode routes drawing events through the USB cable via ADB reverse port forwarding. "
            "Provides ultra-low latency with zero Wi-Fi dependencies."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout.addWidget(desc)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 14px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        # ADB Status
        self.adb_status_label = QLabel("Detecting ADB...")
        self.adb_status_label.setStyleSheet("color: #E5E7EB; font-size: 12px;")
        card_layout.addWidget(self.adb_status_label)

        # Connected Devices List
        self.adb_devices_label = QLabel("No devices detected.")
        self.adb_devices_label.setStyleSheet("color: #9CA3AF; font-size: 12px; font-family: monospace;")
        card_layout.addWidget(self.adb_devices_label)

        # ADB Action Buttons
        btn_row = QHBoxLayout()
        self.enable_reverse_btn = QPushButton("Enable USB Port Forwarding")
        self.enable_reverse_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.enable_reverse_btn.clicked.connect(self._enable_usb_reverse)
        btn_row.addWidget(self.enable_reverse_btn)

        self.remove_reverse_btn = QPushButton("Remove Mapping")
        self.remove_reverse_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #4B5563; }
        """)
        self.remove_reverse_btn.clicked.connect(self._remove_usb_reverse)
        btn_row.addWidget(self.remove_reverse_btn)

        card_layout.addLayout(btn_row)

        # Status output
        self.usb_result_label = QLabel("")
        self.usb_result_label.setWordWrap(True)
        self.usb_result_label.setStyleSheet("color: #38BDF8; font-size: 11px;")
        card_layout.addWidget(self.usb_result_label)

        layout.addWidget(card)

        # Instructions
        usb_guide = QLabel(
            "How to use USB mode:\n"
            "1. Connect Android phone to PC with a USB cable.\n"
            "2. Enable Developer Options -> 'USB Debugging' on your phone.\n"
            "3. Tap 'Enable USB Port Forwarding' above.\n"
            "4. On Android, select 'USB Cable Mode' and tap Connect (connects to 127.0.0.1:8765)."
        )
        usb_guide.setWordWrap(True)
        usb_guide.setStyleSheet("color: #6B7280; font-size: 11px; line-height: 1.4;")
        layout.addWidget(usb_guide)

        layout.addStretch()

        # Refresh ADB info on tab open
        self._refresh_adb_status()
        return widget

    # --- TAB 3: Diagnostics ---

    def _create_diag_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        diag_title = QLabel("Network Adapters & Reachability")
        diag_title.setStyleSheet("color: #E5E7EB; font-size: 13px; font-weight: bold;")
        layout.addWidget(diag_title)

        self.diag_text = QTextEdit()
        self.diag_text.setReadOnly(True)
        self.diag_text.setStyleSheet("""
            QTextEdit {
                background-color: #1F2937;
                color: #D1D5DB;
                border: 1px solid #374151;
                border-radius: 8px;
                font-family: monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.diag_text, 1)

        refresh_diag_btn = QPushButton("Refresh Diagnostics")
        refresh_diag_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #4B5563; }
        """)
        refresh_diag_btn.clicked.connect(self._run_diagnostics)
        layout.addWidget(refresh_diag_btn)

        self._run_diagnostics()
        return widget

    # --- Actions & Helpers ---

    def _populate_ip_combo(self) -> None:
        self.ip_combo.clear()
        interfaces = NetworkDiagnostics.get_detailed_interfaces()
        for iface in interfaces:
            if iface.ip != "127.0.0.1":
                self.ip_combo.addItem(f"{iface.ip} ({iface.network_type.value})", iface.ip)

    def _refresh_adb_status(self) -> None:
        if not self.adb_manager.is_available:
            self.adb_status_label.setText("⚠ ADB is not installed or not found on PATH.")
            self.adb_status_label.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold;")
            self.adb_devices_label.setText("Install Android SDK platform-tools or add adb.exe to PATH.")
            self.enable_reverse_btn.setEnabled(False)
            return

        ver = self.adb_manager.get_adb_version() or "ADB Available"
        self.adb_status_label.setText(f"✓ {ver}")
        self.adb_status_label.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 500;")

        devices = self.adb_manager.get_connected_devices()
        if devices:
            dev_text = ", ".join(f"{d.model} ({d.serial}) [{d.state}]" for d in devices)
            self.adb_devices_label.setText(f"Connected devices: {dev_text}")
            self.adb_devices_label.setStyleSheet("color: #38BDF8; font-size: 12px; font-family: monospace;")
            self.enable_reverse_btn.setEnabled(True)
        else:
            self.adb_devices_label.setText("No Android device detected over USB.")
            self.adb_devices_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
            self.enable_reverse_btn.setEnabled(True)

    def _enable_usb_reverse(self) -> None:
        success, msg = self.adb_manager.setup_reverse_port(port=self.port)
        self.usb_result_label.setText(msg)
        if success:
            self.usb_result_label.setStyleSheet("color: #10B981; font-size: 12px; font-weight: bold;")
        else:
            self.usb_result_label.setStyleSheet("color: #EF4444; font-size: 12px;")

    def _remove_usb_reverse(self) -> None:
        success, msg = self.adb_manager.remove_reverse_port(port=self.port)
        self.usb_result_label.setText(msg)
        self.usb_result_label.setStyleSheet("color: #9CA3AF; font-size: 11px;")

    def _run_diagnostics(self) -> None:
        devices = self.adb_manager.get_connected_devices() if self.adb_manager.is_available else []
        report = NetworkDiagnostics.run_diagnostics(
            port=self.port,
            adb_available=self.adb_manager.is_available,
            adb_devices_count=len(devices),
        )

        lines = [
            "=== DoodleLink Host Diagnostics ===",
            f"Server Status: {'LISTENING' if report.is_server_listening else 'NOT LISTENING'} on port {report.port}",
            f"Recommended IP: {report.primary_ip}",
            f"ADB Status: {'Installed & Ready' if report.is_adb_available else 'Not found'}",
            f"Connected ADB Devices: {report.connected_adb_devices}",
            "",
            "--- Network Interfaces Detected ---",
        ]
        for iface in report.interfaces:
            rec = " [RECOMMENDED]" if iface.is_recommended else ""
            lines.append(f" • {iface.ip:<16} | {iface.network_type.value:<26} | {iface.description}{rec}")

        lines.append("")
        lines.append("--- Troubleshooting Recommendations ---")
        for rec in report.recommendations:
            lines.append(f" ✔ {rec}")

        self.diag_text.setPlainText("\n".join(lines))

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
            QTabWidget::pane {
                border: 1px solid #374151;
                border-radius: 8px;
                background-color: #111827;
            }
            QTabBar::tab {
                background-color: #1F2937;
                color: #9CA3AF;
                padding: 8px 14px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
                font-size: 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: #374151;
            }
        """)
