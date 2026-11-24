"""Tests for AdbManager: device discovery, authorization checks, and reverse port mapping."""

from __future__ import annotations


from doodlelink.network.adb_manager import AdbDevice, AdbManager


def test_adb_device_authorized_property():
    dev_authorized = AdbDevice(serial="abc123", state="device", model="Nothing_Phone_3a")
    assert dev_authorized.is_authorized is True

    dev_unauth = AdbDevice(serial="abc123", state="unauthorized")
    assert dev_unauth.is_authorized is False

    dev_offline = AdbDevice(serial="abc123", state="offline")
    assert dev_offline.is_authorized is False


def test_adb_available_true():
    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        if "version" in cmd:
            return 0, "Android Debug Bridge version 1.0.41\nVersion 35.0.0", ""
        return 1, "", "Unknown command"

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    assert mgr.is_available is True
    assert "1.0.41" in (mgr.get_adb_version() or "")


def test_adb_available_false_on_missing_executable():
    mgr = AdbManager(adb_path=None, runner=lambda cmd: (0, "", ""))
    mgr._adb_path = None
    assert mgr.is_available is False
    assert mgr.get_adb_version() is None


def test_adb_available_false_on_failure():
    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        return 1, "", "Error executing adb"

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    assert mgr.is_available is False


def test_get_connected_devices_parsing():
    sample_output = """List of devices attached
emulator-5554          device product:sdk_gphone64_arm64 model:sdk_gphone64_arm64 device:emulator64_arm64
1234567890             unauthorized usb:1-1
fedcba0987             offline
N3A987654321           device product:Nothing model:A065 device:Nothing_Phone_3a

"""

    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        if "devices" in cmd:
            return 0, sample_output, ""
        return 1, "", ""

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    devices = mgr.get_connected_devices()

    assert len(devices) == 4
    assert devices[0].serial == "emulator-5554"
    assert devices[0].state == "device"
    assert devices[0].model == "sdk_gphone64_arm64"
    assert devices[0].is_authorized is True

    assert devices[1].serial == "1234567890"
    assert devices[1].state == "unauthorized"
    assert devices[1].is_authorized is False

    assert devices[2].serial == "fedcba0987"
    assert devices[2].state == "offline"
    assert devices[2].is_authorized is False

    assert devices[3].serial == "N3A987654321"
    assert devices[3].model == "A065"
    assert devices[3].is_authorized is True


def test_setup_reverse_port_success():
    calls: list[list[str]] = []

    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        if "devices" in cmd:
            return 0, "N3A123 device model:Nothing_Phone_3a product:A065\n", ""
        if "reverse" in cmd and "tcp:8765" in cmd:
            return 0, "", ""
        if "reverse" in cmd and "--list" in cmd:
            return 0, "(reverse) tcp:8765 tcp:8765\n", ""
        return 0, "", ""

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    ok, msg = mgr.setup_reverse_port(port=8765)

    assert ok is True
    assert "Nothing_Phone_3a" in msg or "8765" in msg
    # Verify exact adb reverse command was executed
    reverse_cmd = next((c for c in calls if "reverse" in c and "tcp:8765" in c), None)
    assert reverse_cmd is not None
    assert reverse_cmd == ["/fake/adb", "-s", "N3A123", "reverse", "tcp:8765", "tcp:8765"]


def test_setup_reverse_port_no_devices():
    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        if "devices" in cmd:
            return 0, "List of devices attached\n\n", ""
        return 0, "", ""

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    ok, msg = mgr.setup_reverse_port(port=8765)
    assert ok is False
    assert "No Android device detected" in msg


def test_setup_reverse_port_unauthorized_device():
    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        if "devices" in cmd:
            return 0, "DEV001 unauthorized\n", ""
        return 0, "", ""

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    ok, msg = mgr.setup_reverse_port(port=8765)
    assert ok is False
    assert "unauthorized" in msg
    assert "Allow USB debugging" in msg


def test_setup_reverse_port_offline_device():
    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        if "devices" in cmd:
            return 0, "DEV001 offline\n", ""
        return 0, "", ""

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    ok, msg = mgr.setup_reverse_port(port=8765)
    assert ok is False
    assert "offline" in msg


def test_setup_reverse_port_runner_failure():
    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        if "devices" in cmd:
            return 0, "DEV001 device model:Test\n", ""
        if "reverse" in cmd:
            return 1, "", "cannot bind listener: permission denied"
        return 0, "", ""

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    ok, msg = mgr.setup_reverse_port(port=8765)
    assert ok is False
    assert "cannot bind listener" in msg


def test_remove_reverse_port():
    calls: list[list[str]] = []

    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        return 0, "", ""

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    ok, msg = mgr.remove_reverse_port(port=8765, serial="DEV001")
    assert ok is True
    assert "removed" in msg
    assert ["/fake/adb", "-s", "DEV001", "reverse", "--remove", "tcp:8765"] in calls


def test_remove_all_reverse_ports():
    calls: list[list[str]] = []

    def mock_runner(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        return 0, "", ""

    mgr = AdbManager(adb_path="/fake/adb", runner=mock_runner)
    ok, msg = mgr.remove_all_reverse_ports()
    assert ok is True
    assert ["/fake/adb", "reverse", "--remove-all"] in calls
