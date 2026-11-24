"""Database schema definitions and sequential migrations for DoodleLink SQLite persistence."""

from __future__ import annotations

import sqlite3
import time

CURRENT_SCHEMA_VERSION = 1

MIGRATION_1_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS boards (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_boards_updated ON boards(updated_at DESC);

CREATE TABLE IF NOT EXISTS pages (
    id TEXT PRIMARY KEY,
    board_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
    UNIQUE(board_id, page_number)
);
CREATE INDEX IF NOT EXISTS idx_pages_board ON pages(board_id, page_number);

CREATE TABLE IF NOT EXISTS strokes (
    id TEXT PRIMARY KEY,
    page_id TEXT NOT NULL,
    sequence_order INTEGER NOT NULL,
    tool TEXT NOT NULL,
    color TEXT NOT NULL,
    width REAL NOT NULL,
    created_at REAL NOT NULL,
    points_json TEXT NOT NULL,
    is_visible INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE,
    UNIQUE(page_id, sequence_order)
);
CREATE INDEX IF NOT EXISTS idx_strokes_page ON strokes(page_id, sequence_order);

CREATE TABLE IF NOT EXISTS page_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id TEXT NOT NULL,
    stack_type TEXT NOT NULL,
    action_order INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    stroke_id TEXT,
    cleared_stroke_ids TEXT,
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_history_page ON page_history(page_id, stack_type, action_order);

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

MIGRATIONS: dict[int, str] = {
    1: MIGRATION_1_SQL,
}


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply any pending database migrations sequentially within a transaction."""
    conn.execute("PRAGMA foreign_keys = ON;")

    # Ensure schema_version table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at REAL NOT NULL
        );
    """)

    cursor = conn.execute("SELECT MAX(version) FROM schema_version;")
    row = cursor.fetchone()
    current_version = row[0] if (row and row[0] is not None) else 0

    if current_version < CURRENT_SCHEMA_VERSION:
        for v in range(current_version + 1, CURRENT_SCHEMA_VERSION + 1):
            if v in MIGRATIONS:
                script = MIGRATIONS[v]
                with conn:
                    conn.executescript(script)
                    conn.execute(
                        "INSERT INTO schema_version (version, applied_at) VALUES (?, ?);",
                        (v, time.time()),
                    )
        return CURRENT_SCHEMA_VERSION

    return current_version
