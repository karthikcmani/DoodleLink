"""Thread-safe SQLite connection management with WAL mode and foreign key enforcement."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from doodlelink.storage.schema import apply_migrations


class DatabaseManager:
    """Manages SQLite connection lifecycle, automated migrations, and transactions."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            local_app_data = os.environ.get("LOCALAPPDATA", str(Path.home()))
            app_dir = Path(local_app_data) / "DoodleLink"
            app_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(app_dir / "doodlelink.db")
        else:
            self.db_path = str(db_path)

        self._is_memory = self.db_path == ":memory:"
        self._memory_conn: sqlite3.Connection | None = None

        # Verify migrations on startup
        with self.connect() as conn:
            apply_migrations(conn)

    def connect(self) -> sqlite3.Connection:
        """Create and configure a connection with foreign keys and WAL enabled."""
        if self._is_memory:
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._configure_connection(self._memory_conn)
            return self._memory_conn

        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        self._configure_connection(conn)
        return conn

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA foreign_keys = ON;")
        if not self._is_memory:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None
