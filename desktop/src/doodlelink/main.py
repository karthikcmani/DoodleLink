"""DoodleLink Whiteboard application entry point."""

from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from doodlelink.ui.main_window import MainWindow


def run() -> int:
    """Launch the DoodleLink Desktop Whiteboard application."""
    # Enable High-DPI scaling attributes if needed
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("DoodleLink")
    app.setOrganizationName("DoodleLink")

    # Set clean system font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
