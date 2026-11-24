"""SQLite persistent storage layer for DoodleLink."""

from doodlelink.storage.board_repository import (
    BoardMetadata,
    BoardRepository,
    PageMetadata,
)
from doodlelink.storage.database import DatabaseManager
from doodlelink.storage.schema import CURRENT_SCHEMA_VERSION, apply_migrations

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "BoardMetadata",
    "BoardRepository",
    "DatabaseManager",
    "PageMetadata",
    "apply_migrations",
]
