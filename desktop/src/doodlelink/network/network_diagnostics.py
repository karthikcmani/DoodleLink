"""Network interface classification, connectivity diagnostics, and server port testing."""

from __future__ import annotations

import socket
from dataclasses import dataclass
from enum import Enum

from doodlelink.network.pairing import PairingManager


class NetworkType(str, Enum):
    WIFI_LAN = "Wi-Fi / Local LAN"
    PHONE_HOTSPOT = "Android Phone Hotspot"
    USB_TETHERING = "USB Tethering (RNDIS)"
    PRIVATE_LAN = "Private Network (10.x / 172.x)"
    VIRTUAL = "Virtual Adapter (WSL / VM)"
    LOOPBACK = "Loopback (localhost)"
    UNKNOWN = "Other Interface"


@dataclass(frozen=True)
class InterfaceDetail:
    ip: str
    network_type: NetworkType
    description: str
    is_recommended: bool


@dataclass
class DiagnosticReport:
    is_server_listening: bool
    port: int
    interfaces: list[InterfaceDetail]
    primary_ip: str
    is_adb_available: bool
    connected_adb_devices: int
    recommendations: list[str]


class NetworkDiagnostics:
    """Diagnoses host network reachability, categorizes subnets, and tests port availability."""

    @staticmethod
    def classify_ip(ip: str) -> tuple[NetworkType, str, bool]:
        """Classify an IPv4 address to determine its likely connection role."""
        if ip.startswith("127."):
            return NetworkType.LOOPBACK, "Localhost only (used with USB ADB Reverse)", False

        # Android USB Tethering standard subnet: 192.168.42.x
        if ip.startswith("192.168.42."):
            return NetworkType.USB_TETHERING, "Android USB Tethering (RNDIS)", True

        # Android Phone Hotspot standard subnet: 192.168.43.x
        if ip.startswith("192.168.43."):
            return NetworkType.PHONE_HOTSPOT, "Connected to Android Hotspot", True

        # Common VirtualBox host-only adapter: 192.168.56.x
        if ip.startswith("192.168.56."):
            return NetworkType.VIRTUAL, "VirtualBox Host-Only Adapter", False

        # WSL vEthernet adapter: often 172.17.x to 172.31.x with specific masks
        if ip.startswith("172.26.") or ip.startswith("172.17.") or ip.startswith("172.28."):
            return NetworkType.VIRTUAL, "Virtual / WSL Adapter", False

        # General Home/Office Wi-Fi: 192.168.0.x, 192.168.1.x, etc.
        if ip.startswith("192.168."):
            return NetworkType.WIFI_LAN, "Standard Home/Office Wi-Fi or LAN", True

        # Hotspot alternative (e.g. 172.20.10.x)
        if ip.startswith("172.20.10."):
            return NetworkType.PHONE_HOTSPOT, "Personal Hotspot Network", True

        # Private corporate or university subnets (10.x.x.x, 172.16-31.x.x)
        if ip.startswith("10.") or any(ip.startswith(f"172.{i}.") for i in range(16, 32)):
            return NetworkType.PRIVATE_LAN, "Private / Campus Network", True

        return NetworkType.UNKNOWN, "Generic Network Interface", False

    @classmethod
    def get_detailed_interfaces(cls) -> list[InterfaceDetail]:
        """Discover and classify all available IPv4 network interfaces."""
        ips = PairingManager.get_local_ip_addresses()
        details: list[InterfaceDetail] = []

        for ip in ips:
            net_type, desc, recommended = cls.classify_ip(ip)
            details.append(
                InterfaceDetail(
                    ip=ip,
                    network_type=net_type,
                    description=desc,
                    is_recommended=recommended,
                )
            )

        # Always include loopback for USB ADB mode
        details.append(
            InterfaceDetail(
                ip="127.0.0.1",
                network_type=NetworkType.LOOPBACK,
                description="Localhost for USB ADB Reverse",
                is_recommended=False,
            )
        )

        return details

    @staticmethod
    def is_port_listening(host: str = "127.0.0.1", port: int = 8765) -> bool:
        """Check whether local server is actively listening on target TCP port."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                res = s.connect_ex((host, port))
                return res == 0
        except Exception:
            return False

    @classmethod
    def run_diagnostics(
        cls,
        port: int = 8765,
        adb_available: bool = False,
        adb_devices_count: int = 0,
    ) -> DiagnosticReport:
        """Generate a complete diagnostic snapshot for user-facing troubleshooting."""
        listening = cls.is_port_listening("127.0.0.1", port)
        interfaces = cls.get_detailed_interfaces()

        # Find best recommended IP
        recommended = [i.ip for i in interfaces if i.is_recommended and i.network_type != NetworkType.LOOPBACK]
        primary = recommended[0] if recommended else "127.0.0.1"

        advice: list[str] = []
        if not listening:
            advice.append("Server is not listening. Ensure the DoodleLink host server is running.")

        # Check hotspot presence
        has_hotspot = any(i.network_type == NetworkType.PHONE_HOTSPOT for i in interfaces)
        if has_hotspot:
            advice.append("Active phone hotspot detected. Ensure your Android phone has Wi-Fi hotspot enabled.")

        # Check USB tethering presence
        has_tethering = any(i.network_type == NetworkType.USB_TETHERING for i in interfaces)
        if has_tethering:
            advice.append("USB Tethering interface detected (192.168.42.x).")

        if adb_available:
            if adb_devices_count > 0:
                advice.append(f"ADB detected {adb_devices_count} connected device(s). USB reverse mode is ready.")
            else:
                advice.append("ADB is installed, but no device is detected via USB cable.")

        return DiagnosticReport(
            is_server_listening=listening,
            port=port,
            interfaces=interfaces,
            primary_ip=primary,
            is_adb_available=adb_available,
            connected_adb_devices=adb_devices_count,
            recommendations=advice,
        )
