"""Test configuration for DoodleLink test suite."""

import os
import sys
from pathlib import Path

# Ensure offscreen QPA platform for headless CI / CLI testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Add desktop/src to sys.path
src_dir = Path(__file__).resolve().parent.parent / "desktop" / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
