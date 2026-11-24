"""Database repository implementing transactional CRUD for boards, pages, strokes, and undo/redo stacks."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass

from doodlelink.models.canvas_state import AddStrokeAction, CanvasAction, ClearCanvasAction
from doodlelink.models.stroke import Point, Stroke, ToolType
from doodlelink.storage.database import DatabaseManager


@dataclass(frozen=True)
class BoardMetadata:
    id: str
    title: str
    created_at: float
    updated_at: float
    page_count: int = 1


@dataclass(frozen=True)
class PageMetadata:
    id: str
    board_id: str
    page_number: int
    title: str
    created_at: float
    updated_at: float
    stroke_count: int = 0


class BoardRepository:
    """Provides high-level transactional storage operations for multi-page boards."""

    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        self.db = db_manager or DatabaseManager()

    # --- Board CRUD ---

    def create_board(self, title: str = "Untitled Board") -> BoardMetadata:
        """Create a new board and automatically initialize it with Page 1."""
        board_id = str(uuid.uuid4())
        page_id = str(uuid.uuid4())
        now = time.time()

        conn = self.db.connect()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO boards (id, title, created_at, updated_at) VALUES (?, ?, ?, ?);",
                    (board_id, title, now, now),
                )
                conn.execute(
                    "INSERT INTO pages (id, board_id, page_number, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?);",
                    (page_id, board_id, 1, "Page 1", now, now),
                )
            return BoardMetadata(
                id=board_id,
                title=title,
                created_at=now,
                updated_at=now,
                page_count=1,
            )
        finally:
            if not self.db._is_memory:
                conn.close()

    def get_board(self, board_id: str) -> BoardMetadata | None:
        conn = self.db.connect()
        try:
            cur = conn.execute(
                """
                SELECT b.id, b.title, b.created_at, b.updated_at, COUNT(p.id) as page_count
                FROM boards b
                LEFT JOIN pages p ON b.id = p.board_id
                WHERE b.id = ? AND b.is_deleted = 0
                GROUP BY b.id;
                """,
                (board_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return BoardMetadata(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                page_count=row["page_count"],
            )
        finally:
            if not self.db._is_memory:
                conn.close()

    def list_boards(self) -> list[BoardMetadata]:
        """List all non-deleted boards ordered by last updated timestamp descending."""
        conn = self.db.connect()
        try:
            cur = conn.execute(
                """
                SELECT b.id, b.title, b.created_at, b.updated_at, COUNT(p.id) as page_count
                FROM boards b
                LEFT JOIN pages p ON b.id = p.board_id
                WHERE b.is_deleted = 0
                GROUP BY b.id
                ORDER BY b.updated_at DESC;
                """
            )
            boards: list[BoardMetadata] = []
            for row in cur.fetchall():
                boards.append(
                    BoardMetadata(
                        id=row["id"],
                        title=row["title"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        page_count=row["page_count"],
                    )
                )
            return boards
        finally:
            if not self.db._is_memory:
                conn.close()

    def rename_board(self, board_id: str, new_title: str) -> bool:
        conn = self.db.connect()
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE boards SET title = ?, updated_at = ? WHERE id = ? AND is_deleted = 0;",
                    (new_title.strip(), time.time(), board_id),
                )
                return cur.rowcount > 0
        finally:
            if not self.db._is_memory:
                conn.close()

    def delete_board(self, board_id: str) -> bool:
        """Permanently delete a board and cascade delete its pages and strokes."""
        conn = self.db.connect()
        try:
            with conn:
                cur = conn.execute("DELETE FROM boards WHERE id = ?;", (board_id,))
                return cur.rowcount > 0
        finally:
            if not self.db._is_memory:
                conn.close()

    # --- Page CRUD ---

    def get_pages_for_board(self, board_id: str) -> list[PageMetadata]:
        """Return all pages belonging to board, ordered by page_number ASC."""
        conn = self.db.connect()
        try:
            cur = conn.execute(
                """
                SELECT p.id, p.board_id, p.page_number, p.title, p.created_at, p.updated_at,
                       COUNT(s.id) as stroke_count
                FROM pages p
                LEFT JOIN strokes s ON p.id = s.page_id AND s.is_visible = 1
                WHERE p.board_id = ?
                GROUP BY p.id
                ORDER BY p.page_number ASC;
                """,
                (board_id,),
            )
            pages: list[PageMetadata] = []
            for row in cur.fetchall():
                pages.append(
                    PageMetadata(
                        id=row["id"],
                        board_id=row["board_id"],
                        page_number=row["page_number"],
                        title=row["title"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        stroke_count=row["stroke_count"],
                    )
                )
            return pages
        finally:
            if not self.db._is_memory:
                conn.close()

    def get_page(self, page_id: str) -> PageMetadata | None:
        conn = self.db.connect()
        try:
            cur = conn.execute(
                """
                SELECT p.id, p.board_id, p.page_number, p.title, p.created_at, p.updated_at,
                       COUNT(s.id) as stroke_count
                FROM pages p
                LEFT JOIN strokes s ON p.id = s.page_id AND s.is_visible = 1
                WHERE p.id = ?
                GROUP BY p.id;
                """,
                (page_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return PageMetadata(
                id=row["id"],
                board_id=row["board_id"],
                page_number=row["page_number"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                stroke_count=row["stroke_count"],
            )
        finally:
            if not self.db._is_memory:
                conn.close()

    def create_page(self, board_id: str, title: str = "") -> PageMetadata:
        """Create a new page appended at the end of the board."""
        now = time.time()
        page_id = str(uuid.uuid4())
        conn = self.db.connect()
        try:
            with conn:
                cur = conn.execute(
                    "SELECT COALESCE(MAX(page_number), 0) FROM pages WHERE board_id = ?;",
                    (board_id,),
                )
                max_num = cur.fetchone()[0]
                next_num = max_num + 1
                page_title = title if title.strip() else f"Page {next_num}"

                conn.execute(
                    "INSERT INTO pages (id, board_id, page_number, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?);",
                    (page_id, board_id, next_num, page_title, now, now),
                )
                conn.execute("UPDATE boards SET updated_at = ? WHERE id = ?;", (now, board_id))

            return PageMetadata(
                id=page_id,
                board_id=board_id,
                page_number=next_num,
                title=page_title,
                created_at=now,
                updated_at=now,
                stroke_count=0,
            )
        finally:
            if not self.db._is_memory:
                conn.close()

    def duplicate_page(self, page_id: str) -> PageMetadata:
        """Duplicate an existing page along with its visible strokes and history."""
        target_page = self.get_page(page_id)
        if not target_page:
            raise ValueError(f"Page '{page_id}' does not exist.")

        # Load target page strokes & actions
        strokes, undo_stack, redo_stack = self.load_page_canvas_state(page_id)

        # Create new page in same board
        new_page = self.create_page(
            board_id=target_page.board_id,
            title=f"{target_page.title} (Copy)",
        )

        # Clone strokes with new IDs
        id_map: dict[str, str] = {}
        cloned_strokes: list[Stroke] = []
        for s in strokes:
            new_s_id = str(uuid.uuid4())
            id_map[s.id] = new_s_id
            cloned_strokes.append(
                Stroke(
                    id=new_s_id,
                    tool=s.tool,
                    color=s.color,
                    width=s.width,
                    points=[Point(p.x, p.y, p.timestamp, p.pressure) for p in s.points],
                )
            )

        # Clone undo stack actions
        cloned_undo: list[CanvasAction] = []
        for act in undo_stack:
            if isinstance(act, AddStrokeAction):
                mapped_id = id_map.get(act.stroke.id)
                stroke_match = next((cs for cs in cloned_strokes if cs.id == mapped_id), None)
                if stroke_match:
                    cloned_undo.append(AddStrokeAction(stroke_match))
            elif isinstance(act, ClearCanvasAction):
                mapped_cleared: list[Stroke] = []
                for cs in act.cleared_strokes:
                    m_id = id_map.get(cs.id)
                    if m_id:
                        mapped_cleared.append(
                            Stroke(
                                id=m_id,
                                tool=cs.tool,
                                color=cs.color,
                                width=cs.width,
                                points=[Point(p.x, p.y, p.timestamp, p.pressure) for p in cs.points],
                            )
                        )
                cloned_undo.append(ClearCanvasAction(mapped_cleared))

        self.save_page_canvas_state(new_page.id, cloned_strokes, cloned_undo, [])
        return self.get_page(new_page.id) or new_page

    def delete_page(self, page_id: str) -> bool:
        """Delete page and reorder remaining pages. Raises ValueError if only 1 page remains."""
        page = self.get_page(page_id)
        if not page:
            return False

        conn = self.db.connect()
        try:
            with conn:
                cur = conn.execute("SELECT COUNT(*) FROM pages WHERE board_id = ?;", (page.board_id,))
                total = cur.fetchone()[0]
                if total <= 1:
                    raise ValueError("Cannot delete the only page of a whiteboard.")

                # Delete page (cascades to strokes & history)
                conn.execute("DELETE FROM pages WHERE id = ?;", (page_id,))

                # Re-number remaining pages sequentially: 1..N
                cur = conn.execute(
                    "SELECT id FROM pages WHERE board_id = ? ORDER BY page_number ASC;",
                    (page.board_id,),
                )
                remaining_ids = [r["id"] for r in cur.fetchall()]
                for idx, r_id in enumerate(remaining_ids, start=1):
                    conn.execute(
                        "UPDATE pages SET page_number = ?, updated_at = ? WHERE id = ?;",
                        (idx, time.time(), r_id),
                    )

                conn.execute("UPDATE boards SET updated_at = ? WHERE id = ?;", (time.time(), page.board_id))
            return True
        finally:
            if not self.db._is_memory:
                conn.close()

    # --- Canvas State Persistence (Strokes & Undo/Redo) ---

    def load_page_strokes(self, page_id: str) -> list[Stroke]:
        """Load and return all currently visible strokes for a page."""
        visible_strokes, _, _ = self.load_page_canvas_state(page_id)
        return visible_strokes

    def load_page_canvas_state(
        self, page_id: str
    ) -> tuple[list[Stroke], list[CanvasAction], list[CanvasAction]]:
        """Load visible strokes, undo history, and redo history for a page."""
        conn = self.db.connect()
        try:
            # 1. Load all strokes for this page
            cur = conn.execute(
                """
                SELECT id, sequence_order, tool, color, width, created_at, points_json, is_visible
                FROM strokes
                WHERE page_id = ?
                ORDER BY sequence_order ASC;
                """,
                (page_id,),
            )
            strokes_by_id: dict[str, Stroke] = {}
            visible_strokes: list[Stroke] = []

            for row in cur.fetchall():
                pts_data = json.loads(row["points_json"])
                pts = [Point(p["x"], p["y"], p.get("t", 0.0), p.get("p", 1.0)) for p in pts_data]
                stroke = Stroke(
                    id=row["id"],
                    tool=ToolType(row["tool"]),
                    color=row["color"],
                    width=row["width"],
                    points=pts,
                )
                strokes_by_id[row["id"]] = stroke
                if row["is_visible"] == 1:
                    visible_strokes.append(stroke)

            # 2. Load undo and redo stacks
            cur = conn.execute(
                """
                SELECT stack_type, action_order, action_type, stroke_id, cleared_stroke_ids
                FROM page_history
                WHERE page_id = ?
                ORDER BY stack_type ASC, action_order ASC;
                """,
                (page_id,),
            )

            undo_stack: list[CanvasAction] = []
            redo_stack: list[CanvasAction] = []

            for row in cur.fetchall():
                stack_type = row["stack_type"]
                action_type = row["action_type"]

                action: CanvasAction | None = None
                if action_type == "add_stroke":
                    s = strokes_by_id.get(row["stroke_id"])
                    if s:
                        action = AddStrokeAction(s)
                elif action_type == "clear_canvas":
                    c_ids = json.loads(row["cleared_stroke_ids"] or "[]")
                    cleared = [strokes_by_id[c_id] for c_id in c_ids if c_id in strokes_by_id]
                    action = ClearCanvasAction(cleared)

                if action:
                    if stack_type == "undo":
                        undo_stack.append(action)
                    else:
                        redo_stack.append(action)

            return visible_strokes, undo_stack, redo_stack
        finally:
            if not self.db._is_memory:
                conn.close()

    def save_page_canvas_state(
        self,
        page_id: str,
        strokes: list[Stroke],
        undo_stack: list[CanvasAction],
        redo_stack: list[CanvasAction],
    ) -> None:
        """Atomically persist current page canvas state: visible strokes, undo stack, and redo stack."""
        now = time.time()

        # Collect all referenced strokes across visible strokes, undo stack, and redo stack
        all_strokes_map: dict[str, Stroke] = {}
        for s in strokes:
            all_strokes_map[s.id] = s

        for act in undo_stack + redo_stack:
            if isinstance(act, AddStrokeAction):
                all_strokes_map[act.stroke.id] = act.stroke
            elif isinstance(act, ClearCanvasAction):
                for s in act.cleared_strokes:
                    all_strokes_map[s.id] = s

        visible_ids = {s.id for s in strokes}

        conn = self.db.connect()
        try:
            with conn:
                # 1. Clear existing strokes and history for this page
                conn.execute("DELETE FROM strokes WHERE page_id = ?;", (page_id,))
                conn.execute("DELETE FROM page_history WHERE page_id = ?;", (page_id,))

                # 2. Insert all strokes
                seq = 1
                for s_id, s in all_strokes_map.items():
                    pts_json = json.dumps(
                        [{"x": p.x, "y": p.y, "t": p.timestamp, "p": p.pressure} for p in s.points]
                    )
                    is_vis = 1 if s_id in visible_ids else 0
                    conn.execute(
                        """
                        INSERT INTO strokes (id, page_id, sequence_order, tool, color, width, created_at, points_json, is_visible)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (s.id, page_id, seq, s.tool.value, s.color, s.width, now, pts_json, is_vis),
                    )
                    seq += 1

                # 3. Insert undo stack actions
                for idx, act in enumerate(undo_stack):
                    if isinstance(act, AddStrokeAction):
                        conn.execute(
                            """
                            INSERT INTO page_history (page_id, stack_type, action_order, action_type, stroke_id)
                            VALUES (?, 'undo', ?, 'add_stroke', ?);
                            """,
                            (page_id, idx, act.stroke.id),
                        )
                    elif isinstance(act, ClearCanvasAction):
                        c_ids_json = json.dumps([cs.id for cs in act.cleared_strokes])
                        conn.execute(
                            """
                            INSERT INTO page_history (page_id, stack_type, action_order, action_type, cleared_stroke_ids)
                            VALUES (?, 'undo', ?, 'clear_canvas', ?);
                            """,
                            (page_id, idx, c_ids_json),
                        )

                # 4. Insert redo stack actions
                for idx, act in enumerate(redo_stack):
                    if isinstance(act, AddStrokeAction):
                        conn.execute(
                            """
                            INSERT INTO page_history (page_id, stack_type, action_order, action_type, stroke_id)
                            VALUES (?, 'redo', ?, 'add_stroke', ?);
                            """,
                            (page_id, idx, act.stroke.id),
                        )
                    elif isinstance(act, ClearCanvasAction):
                        c_ids_json = json.dumps([cs.id for cs in act.cleared_strokes])
                        conn.execute(
                            """
                            INSERT INTO page_history (page_id, stack_type, action_order, action_type, cleared_stroke_ids)
                            VALUES (?, 'redo', ?, 'clear_canvas', ?);
                            """,
                            (page_id, idx, c_ids_json),
                        )

                # 5. Touch page and board updated_at
                conn.execute("UPDATE pages SET updated_at = ? WHERE id = ?;", (now, page_id))
                cur = conn.execute("SELECT board_id FROM pages WHERE id = ?;", (page_id,))
                r = cur.fetchone()
                if r:
                    conn.execute("UPDATE boards SET updated_at = ? WHERE id = ?;", (now, r["board_id"]))
        finally:
            if not self.db._is_memory:
                conn.close()

    # --- App State / Session Recovery ---

    def get_app_state(self, key: str) -> str | None:
        conn = self.db.connect()
        try:
            cur = conn.execute("SELECT value FROM app_state WHERE key = ?;", (key,))
            r = cur.fetchone()
            return r["value"] if r else None
        finally:
            if not self.db._is_memory:
                conn.close()

    def set_app_state(self, key: str, value: str) -> None:
        conn = self.db.connect()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO app_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                    (key, value),
                )
        finally:
            if not self.db._is_memory:
                conn.close()

    def get_last_active_board_and_page(self) -> tuple[str | None, str | None]:
        board_id = self.get_app_state("last_active_board_id")
        page_id = self.get_app_state("last_active_page_id")
        return board_id, page_id

    def set_last_active_board_and_page(self, board_id: str, page_id: str) -> None:
        self.set_app_state("last_active_board_id", board_id)
        self.set_app_state("last_active_page_id", page_id)
