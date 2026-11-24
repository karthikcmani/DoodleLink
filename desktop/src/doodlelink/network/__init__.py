"""Networking and synchronization layer for DoodleLink."""

from doodlelink.network.protocol import PROTOCOL_VERSION, validate_message
from doodlelink.network.pairing import PairingManager
from doodlelink.network.server import WhiteboardServer

__all__ = [
    "PROTOCOL_VERSION",
    "validate_message",
    "PairingManager",
    "WhiteboardServer",
]
