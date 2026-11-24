"""ADB reverse port forwarding and USB device management for DoodleLink."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class AdbDevice:
    """Represents an Android device discovered by ADB."""

    serial: str
    state: str  # "device", "unauthorized", "offline", "unknown"
    model: str = "Unknown"
    product: str = "Unknown"

    @property
    def is_authorized(self) -> bool:
        return self.state.lower() == "device"


class AdbManager:
    """Manages ADB discovery, device authorization checks, and reverse port mapping."""

    def __init__(
        self,
        adb_path: str | None = None,
        runner: Callable[[list[str]], tuple[int, str, str]] | None = None,
    ) -> None:
        self._adb_path = adb_path or self._locate_adb()
        self._runner = runner or self._default_runner

    @staticmethod
    def _locate_adb() -> str | None:
        """Locate adb executable on system PATH or Android SDK platform-tools."""
        found = shutil.which("adb")
        if found:
            return found

        # Check ANDROID_HOME or ANDROID_SDK_ROOT
        for env_var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
            sdk_dir = os.environ.get(env_var)
            if sdk_dir:
                candidate = Path(sdk_dir) / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
                if candidate.exists() and candidate.is_file():
                    return str(candidate)

        # Standard Windows default path
        win_default = Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
        if win_default.exists() and win_default.is_file():
            return str(win_default)

        return None

    @staticmethod
    def _default_runner(cmd: list[str]) -> tuple[int, str, str]:
        """Execute command safely with a strict timeout."""
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            return res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out after 5 seconds"
        except Exception as e:
            return -1, "", str(e)

    @property
    def is_available(self) -> bool:
        """Return True if ADB executable is found and runnable."""
        if not self._adb_path:
            return False
        ret, stdout, _ = self._runner([self._adb_path, "version"])
        return ret == 0 and "Android Debug Bridge" in stdout

    def get_adb_version(self) -> str | None:
        if not self._adb_path:
            return None
        ret, stdout, _ = self._runner([self._adb_path, "version"])
        if ret == 0:
            first_line = stdout.splitlines()[0] if stdout.splitlines() else stdout
            return first_line.strip()
        return None

    def get_connected_devices(self) -> list[AdbDevice]:
        """Return list of connected Android devices via 'adb devices -l'."""
        if not self._adb_path:
            return []

        ret, stdout, _ = self._runner([self._adb_path, "devices", "-l"])
        if ret != 0:
            return []

        devices: list[AdbDevice] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue

            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]

                model = "Unknown"
                product = "Unknown"
                for item in parts[2:]:
                    if item.startswith("model:"):
                        model = item.split(":", 1)[1]
                    elif item.startswith("product:"):
                        product = item.split(":", 1)[1]

                devices.append(AdbDevice(serial=serial, state=state, model=model, product=product))

        return devices

    def setup_reverse_port(
        self,
        port: int = 8765,
        serial: str | None = None,
    ) -> tuple[bool, str]:
        """Set up reverse port forwarding (phone localhost:port -> PC localhost:port).

        Returns (success: bool, message: str).
        """
        if not self._adb_path:
            return False, "ADB is not installed or not found in system PATH."

        devices = self.get_connected_devices()
        if not devices:
            return (
                False,
                "No Android device detected over USB.\n\n"
                "Please connect your phone via USB cable and ensure 'USB Debugging' is enabled in Developer Options.",
            )

        # Select target device
        target: AdbDevice
        if serial:
            matched = next((d for d in devices if d.serial == serial), None)
            if not matched:
                return False, f"Selected device '{serial}' is not connected."
            target = matched
        else:
            target = devices[0]

        # Verify device authorization
        if target.state == "unauthorized":
            return (
                False,
                f"Device '{target.serial}' is unauthorized.\n\n"
                "Please check your phone screen and tap 'Allow USB debugging'.",
            )
        elif target.state == "offline":
            return (
                False,
                f"Device '{target.serial}' is offline.\n\n"
                "Please unplug and reconnect your USB cable.",
            )
        elif target.state != "device":
            return False, f"Device '{target.serial}' has unexpected state: {target.state}"

        # Construct adb reverse command: adb -s <serial> reverse tcp:<port> tcp:<port>
        cmd = [self._adb_path, "-s", target.serial, "reverse", f"tcp:{port}", f"tcp:{port}"]
        ret, stdout, stderr = self._runner(cmd)
        if ret != 0:
            err_msg = stderr.strip() or stdout.strip() or "Unknown ADB error"
            return False, f"Failed to set up reverse port: {err_msg}"

        # Verify mapping was registered
        active_mappings = self.get_active_reverse_mappings(serial=target.serial)
        target_mapping = f"tcp:{port}"
        if any(target_mapping in m for m in active_mappings):
            return (
                True,
                f"USB reverse port forwarding enabled successfully on {target.model} ({target.serial}).\n"
                f"Your phone can now connect to 127.0.0.1:{port}.",
            )

        return True, f"ADB reverse executed successfully for port {port}."

    def remove_reverse_port(
        self,
        port: int = 8765,
        serial: str | None = None,
    ) -> tuple[bool, str]:
        """Remove reverse port mapping."""
        if not self._adb_path:
            return False, "ADB not found."

        cmd = [self._adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(["reverse", "--remove", f"tcp:{port}"])

        ret, stdout, stderr = self._runner(cmd)
        if ret == 0:
            return True, f"USB reverse port forwarding for tcp:{port} removed."
        return False, stderr.strip() or stdout.strip() or "Failed to remove reverse port."

    def remove_all_reverse_ports(self, serial: str | None = None) -> tuple[bool, str]:
        """Remove all reverse port mappings."""
        if not self._adb_path:
            return False, "ADB not found."

        cmd = [self._adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(["reverse", "--remove-all"])

        ret, stdout, stderr = self._runner(cmd)
        if ret == 0:
            return True, "All USB reverse port mappings removed."
        return False, stderr.strip() or stdout.strip() or "Failed to clear reverse ports."

    def get_active_reverse_mappings(self, serial: str | None = None) -> list[str]:
        """List active reverse port mappings via 'adb reverse --list'."""
        if not self._adb_path:
            return []

        cmd = [self._adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(["reverse", "--list"])

        ret, stdout, _ = self._runner(cmd)
        if ret != 0:
            return []

        return [line.strip() for line in stdout.splitlines() if line.strip()]
