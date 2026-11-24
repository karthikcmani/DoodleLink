"""Convenience launcher for DoodleLink desktop application."""

import sys
from pathlib import Path

# Add src to sys.path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from doodlelink.main import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run())
