"""Tests for NetworkDiagnostics: classification of subnets, reachability, and reports."""

from __future__ import annotations

import socket

from doodlelink.network.network_diagnostics import NetworkDiagnostics, NetworkType


def test_classify_ip_subnets():
    # Loopback
    net_type, _, rec = NetworkDiagnostics.classify_ip("127.0.0.1")
    assert net_type == NetworkType.LOOPBACK
    assert rec is False

    # Android Phone Hotspot
    net_type, desc, rec = NetworkDiagnostics.classify_ip("192.168.43.10")
    assert net_type == NetworkType.PHONE_HOTSPOT
    assert "Hotspot" in desc
    assert rec is True

    # Android USB Tethering (RNDIS)
    net_type, desc, rec = NetworkDiagnostics.classify_ip("192.168.42.50")
    assert net_type == NetworkType.USB_TETHERING
    assert "Tethering" in desc
    assert rec is True

    # Standard Wi-Fi
    net_type, desc, rec = NetworkDiagnostics.classify_ip("192.168.1.100")
    assert net_type == NetworkType.WIFI_LAN
    assert rec is True

    # Virtual adapters (WSL / VirtualBox)
    net_type, _, rec = NetworkDiagnostics.classify_ip("172.26.128.1")
    assert net_type == NetworkType.VIRTUAL
    assert rec is False

    net_type, _, rec = NetworkDiagnostics.classify_ip("192.168.56.1")
    assert net_type == NetworkType.VIRTUAL
    assert rec is False

    # Private corporate / campus subnets
    net_type, _, rec = NetworkDiagnostics.classify_ip("10.50.1.20")
    assert net_type == NetworkType.PRIVATE_LAN
    assert rec is True


def test_get_detailed_interfaces():
    interfaces = NetworkDiagnostics.get_detailed_interfaces()
    assert len(interfaces) >= 1
    # Check loopback is always present
    loopback = next((i for i in interfaces if i.ip == "127.0.0.1"), None)
    assert loopback is not None
    assert loopback.network_type == NetworkType.LOOPBACK


def test_is_port_listening_with_live_socket():
    # Bind a temporary TCP listener on an ephemeral port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]

        # Should be listening
        assert NetworkDiagnostics.is_port_listening("127.0.0.1", port) is True

    # After close, should not be listening
    assert NetworkDiagnostics.is_port_listening("127.0.0.1", port) is False


def test_run_diagnostics():
    report = NetworkDiagnostics.run_diagnostics(port=8765, adb_available=True, adb_devices_count=1)
    assert isinstance(report.is_server_listening, bool)
    assert report.port == 8765
    assert len(report.interfaces) >= 1
    assert report.is_adb_available is True
    assert report.connected_adb_devices == 1
    assert len(report.recommendations) >= 1
