"""Tests for PairingDialog: Wi-Fi/Hotspot tabs, USB ADB Reverse interface, and diagnostics."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from doodlelink.network.adb_manager import AdbManager
from doodlelink.network.pairing import PairingManager
from doodlelink.ui.pairing_dialog import PairingDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_pairing_dialog_tabs_initialization(qapp):
    pm = PairingManager()
    mgr = AdbManager(adb_path=None, runner=lambda cmd: (0, "", ""))

    dialog = PairingDialog(pairing_manager=pm, port=8765, adb_manager=mgr)
    assert dialog.tabs.count() == 3
    assert "Wi-Fi" in dialog.tabs.tabText(0)
    assert "USB" in dialog.tabs.tabText(1)
    assert "Diagnostics" in dialog.tabs.tabText(2)
    assert dialog.port == 8765
    assert pm.current_code[:3] in dialog.code_label.text()

    dialog.close()


def test_pairing_dialog_usb_tab_enable_adb(qapp):
    calls: list[list[str]] = []

    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        if "version" in cmd:
            return 0, "Android Debug Bridge version 1.0.41", ""
        if "devices" in cmd:
            return 0, "TESTDEV001 device model:TestModel product:TestProduct\n", ""
        if "reverse" in cmd and "--list" in cmd:
            return 0, "(reverse) tcp:8765 tcp:8765\n", ""
        return 0, "", ""

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    pm = PairingManager()
    dialog = PairingDialog(pairing_manager=pm, port=8765, adb_manager=mgr)

    # Refresh ADB info
    dialog._refresh_adb_status()
    assert "TestModel" in dialog.adb_devices_label.text()
    assert dialog.enable_reverse_btn.isEnabled() is True

    # Click Enable USB Reverse
    dialog._enable_usb_reverse()
    assert "successfully" in dialog.usb_result_label.text().lower() or "8765" in dialog.usb_result_label.text()

    # Click Remove Mapping
    dialog._remove_usb_reverse()
    assert "removed" in dialog.usb_result_label.text().lower()

    dialog.close()


def test_pairing_dialog_diagnostics_refresh(qapp):
    pm = PairingManager()
    mgr = AdbManager(adb_path=None, runner=lambda cmd: (1, "", "no adb"))
    dialog = PairingDialog(pairing_manager=pm, port=8765, adb_manager=mgr)

    dialog._run_diagnostics()
    diag_text = dialog.diag_text.toPlainText()
    assert "DoodleLink Host Diagnostics" in diag_text
    assert "Server Status:" in diag_text
    assert "Network Interfaces" in diag_text
    dialog.close()
