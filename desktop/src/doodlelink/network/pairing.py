"""Pairing code generation, validation, and local network interface discovery."""

from __future__ import annotations

import secrets
import socket
import time
import uuid


class PairingManager:
    """Manages short-lived pairing tokens and discovers active host network interfaces."""

    def __init__(self, code_ttl_seconds: float = 600.0) -> None:
        self.code_ttl_seconds = code_ttl_seconds
        self.session_id: str = str(uuid.uuid4())
        self.current_code: str = ""
        self.code_generated_at: float = 0.0
        self.generate_new_code()

    def generate_new_code(self) -> str:
        """Generate a new 6-digit cryptographically random pairing code."""
        code_int = secrets.randbelow(1_000_000)
        self.current_code = f"{code_int:06d}"
        self.code_generated_at = time.time()
        self.session_id = str(uuid.uuid4())
        return self.current_code

    @property
    def is_code_expired(self) -> bool:
        return (time.time() - self.code_generated_at) > self.code_ttl_seconds

    def verify_code(self, candidate_code: str) -> bool:
        """Verify candidate pairing code using constant-time string comparison."""
        if not candidate_code or self.is_code_expired:
            return False
        clean_candidate = candidate_code.strip()
        return secrets.compare_digest(self.current_code, clean_candidate)

    @staticmethod
    def get_local_ip_addresses() -> list[str]:
        """Discover active local IPv4 addresses sorted by likelihood of Wi-Fi / hotspot relevance."""
        ips: list[str] = []
        try:
            hostname = socket.gethostname()
            _, _, host_ips = socket.gethostbyname_ex(hostname)
            ips.extend(host_ips)
        except Exception:
            pass

        # Try connecting a dummy UDP socket to find default route IP
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                default_ip = s.getsockname()[0]
                if default_ip not in ips and not default_ip.startswith("127."):
                    ips.insert(0, default_ip)
        except Exception:
            pass

        # Deduplicate while preserving order
        unique_ips: list[str] = []
        for ip in ips:
            if ip not in unique_ips and not ip.startswith("127."):
                unique_ips.append(ip)

        # Sort: prefer 192.168.x.x, then 172.x.x.x, then 10.x.x.x
        def sort_priority(ip_str: str) -> int:
            if ip_str.startswith("192.168."):
                return 0
            if any(ip_str.startswith(f"172.{i}.") for i in range(16, 32)):
                return 1
            if ip_str.startswith("10."):
                return 2
            return 3

        unique_ips.sort(key=sort_priority)
        if not unique_ips:
            unique_ips.append("127.0.0.1")

        return unique_ips

    def get_primary_ip(self) -> str:
        ips = self.get_local_ip_addresses()
        return ips[0] if ips else "127.0.0.1"

    def get_pairing_uri(self, host: str, port: int) -> str:
        """URI scheme for quick QR code pairing."""
        return f"doodlelink://connect?host={host}&port={port}&code={self.current_code}"
