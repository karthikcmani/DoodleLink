"""Multi-page whiteboard document state managing pages, autosave, and CanvasState synchronization."""

from __future__ import annotations

from typing import Callable

from doodlelink.models.canvas_state import CanvasState
from doodlelink.storage.board_repository import BoardMetadata, BoardRepository, PageMetadata


class MultiPageDocument:
    """Coordinates multiple whiteboard pages, autosave persistence, and active canvas state."""

    def __init__(
        self,
        board: BoardMetadata,
        repository: BoardRepository | None = None,
    ) -> None:
        self.repository = repository or BoardRepository()
        self.board = board
        self.pages: list[PageMetadata] = self.repository.get_pages_for_board(self.board.id)
        if not self.pages:
            p = self.repository.create_page(self.board.id, "Page 1")
            self.pages = [p]

        self.active_page_id: str = self.pages[0].id
        self.active_canvas_state: CanvasState = CanvasState()

        # Observers
        self._on_page_changed: list[Callable[[PageMetadata], None]] = []
        self._on_board_changed: list[Callable[[BoardMetadata], None]] = []
        self._on_pages_list_updated: list[Callable[[list[PageMetadata]], None]] = []

        # Load active page state
        self._load_active_page_canvas()
        self._attach_autosave_listeners()

    # --- Properties ---

    @property
    def active_page(self) -> PageMetadata:
        for p in self.pages:
            if p.id == self.active_page_id:
                return p
        return self.pages[0]

    @property
    def current_page_number(self) -> int:
        return self.active_page.page_number

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def has_next_page(self) -> bool:
        return self.current_page_number < self.page_count

    @property
    def has_prev_page(self) -> bool:
        return self.current_page_number > 1

    # --- Event Subscriptions ---

    def add_page_change_listener(self, callback: Callable[[PageMetadata], None]) -> None:
        if callback not in self._on_page_changed:
            self._on_page_changed.append(callback)

    def add_board_change_listener(self, callback: Callable[[BoardMetadata], None]) -> None:
        if callback not in self._on_board_changed:
            self._on_board_changed.append(callback)

    def add_pages_list_listener(self, callback: Callable[[list[PageMetadata]], None]) -> None:
        if callback not in self._on_pages_list_updated:
            self._on_pages_list_updated.append(callback)

    # --- Autosave ---

    def _attach_autosave_listeners(self) -> None:
        # Trigger autosave only on discrete mutations (commit, undo, redo, clear)
        # Avoid writes during continuous pointer moves
        self.active_canvas_state.add_change_listener(self.save_current_page)

    def save_current_page(self) -> None:
        """Persist visible strokes, undo history, and redo history of the active page."""
        try:
            self.repository.save_page_canvas_state(
                page_id=self.active_page_id,
                strokes=self.active_canvas_state.strokes,
                undo_stack=self.active_canvas_state._undo_stack,
                redo_stack=self.active_canvas_state._redo_stack,
            )
            self.repository.set_last_active_board_and_page(self.board.id, self.active_page_id)
        except Exception:
            # Handle failed writes safely without crashing drawing UI
            pass

    def _load_active_page_canvas(self) -> None:
        strokes, undo_stack, redo_stack = self.repository.load_page_canvas_state(self.active_page_id)
        self.active_canvas_state.strokes = list(strokes)
        self.active_canvas_state._undo_stack = list(undo_stack)
        self.active_canvas_state._redo_stack = list(redo_stack)

    # --- Page Operations ---

    def switch_page(self, page_id: str | None = None, page_number: int | None = None) -> bool:
        """Switch to target page by UUID or page number after saving current page."""
        target: PageMetadata | None = None
        if page_id is not None:
            target = next((p for p in self.pages if p.id == page_id), None)
        elif page_number is not None:
            target = next((p for p in self.pages if p.page_number == page_number), None)

        if not target or target.id == self.active_page_id:
            return False

        # 1. Autosave current page
        self.save_current_page()

        # 2. Switch to new page
        self.active_page_id = target.id
        self._load_active_page_canvas()
        self.repository.set_last_active_board_and_page(self.board.id, self.active_page_id)

        # 3. Notify listeners
        for cb in self._on_page_changed:
            cb(target)
        return True

    def next_page(self) -> bool:
        if self.has_next_page:
            return self.switch_page(page_number=self.current_page_number + 1)
        return False

    def prev_page(self) -> bool:
        if self.has_prev_page:
            return self.switch_page(page_number=self.current_page_number - 1)
        return False

    def add_page(self, title: str = "") -> PageMetadata:
        """Create and switch to a new blank page at the end of the board."""
        self.save_current_page()
        new_page = self.repository.create_page(self.board.id, title)
        self.pages = self.repository.get_pages_for_board(self.board.id)

        for cb in self._on_pages_list_updated:
            cb(self.pages)

        self.switch_page(page_id=new_page.id)
        return new_page

    def duplicate_current_page(self) -> PageMetadata:
        """Duplicate current page and switch to the clone."""
        self.save_current_page()
        dup_page = self.repository.duplicate_page(self.active_page_id)
        self.pages = self.repository.get_pages_for_board(self.board.id)

        for cb in self._on_pages_list_updated:
            cb(self.pages)

        self.switch_page(page_id=dup_page.id)
        return dup_page

    def delete_current_page(self) -> bool:
        """Delete current page. Preserves at least 1 page."""
        if self.page_count <= 1:
            return False

        del_id = self.active_page_id
        target_idx = max(0, self.current_page_number - 2)

        ok = self.repository.delete_page(del_id)
        if not ok:
            return False

        self.pages = self.repository.get_pages_for_board(self.board.id)
        new_target = self.pages[min(target_idx, len(self.pages) - 1)]

        self.active_page_id = new_target.id
        self._load_active_page_canvas()
        self.repository.set_last_active_board_and_page(self.board.id, self.active_page_id)

        for cb in self._on_pages_list_updated:
            cb(self.pages)
        for cb in self._on_page_changed:
            cb(new_target)

        return True

    # --- Board Lifecycle ---

    def rename_board(self, new_title: str) -> bool:
        if not new_title.strip():
            return False
        ok = self.repository.rename_board(self.board.id, new_title)
        if ok:
            updated = self.repository.get_board(self.board.id)
            if updated:
                self.board = updated
                for cb in self._on_board_changed:
                    cb(self.board)
        return ok

    @classmethod
    def load_or_create_default(
        cls, repository: BoardRepository | None = None
    ) -> MultiPageDocument:
        """Recover last active board/page or initialize a default board."""
        repo = repository or BoardRepository()
        last_board_id, last_page_id = repo.get_last_active_board_and_page()

        if last_board_id:
            board = repo.get_board(last_board_id)
            if board:
                doc = cls(board, repository=repo)
                if last_page_id and any(p.id == last_page_id for p in doc.pages):
                    doc.switch_page(page_id=last_page_id)
                return doc

        # Check existing boards
        boards = repo.list_boards()
        if boards:
            return cls(boards[0], repository=repo)

        # Fresh database: create initial board
        default_board = repo.create_board("My Whiteboard")
        return cls(default_board, repository=repo)
