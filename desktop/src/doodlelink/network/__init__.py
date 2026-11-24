"""Networking and synchronization layer for DoodleLink."""

from doodlelink.network.adb_manager import AdbDevice, AdbManager
from doodlelink.network.network_diagnostics import InterfaceDetail, NetworkDiagnostics, NetworkType
from doodlelink.network.pairing import PairingManager
from doodlelink.network.protocol import PROTOCOL_VERSION, validate_message
from doodlelink.network.server import WhiteboardServer

__all__ = [
    "PROTOCOL_VERSION",
    "validate_message",
    "PairingManager",
    "WhiteboardServer",
    "AdbManager",
    "AdbDevice",
    "NetworkDiagnostics",
    "NetworkType",
    "InterfaceDetail",
]
