# DoodleLink — Project Status

**Last updated:** 2026-11-25  
**Current phase:** Phase 1 — Desktop whiteboard foundation  
**Overall status:** Phase 1 completed and verified; ready for Phase 2.

## Verified facts
- **GitHub repository:** `https://github.com/karthikcmani/DoodleLink.git`
- **Git branch:** `main` tracking `origin/main`
- **Host OS:** Windows 11 (build 10.0.26300)
- **Python environment:** Python 3.13.2 (64-bit)
- **Desktop dependencies installed & verified:**
  - `PySide6` 6.12.0 (Qt 6.12.0)
  - `websockets` 15.0.1
  - `pytest` 9.1.1
  - `pytest-asyncio` 1.4.0
  - `ruff` 0.14.4
- **Shared Protocol Baseline:**
  - Protocol v1 JSON schema established at `shared/protocol/schema_v1.json`
  - Normalized coordinates `[0.0, 1.0] x [0.0, 1.0]` with timestamps and pressure
  - Reusable serialization/deserialization for future WebSocket transport
- **Desktop Application Architecture (`desktop/src/doodlelink`):**
  - `models/stroke.py`: `Point`, `Stroke`, `ToolType` (pure Python dataclasses, bounded coordinate clamping, JSON serialization)
  - `models/coordinate.py`: `CoordinateMapper`, `LogicalCanvas`, `ViewportRect` (16:9 aspect-ratio letterbox/pillarbox geometry, bidirectional coordinate conversions)
  - `models/canvas_state.py`: `CanvasState` (stroke management, pointer down/move/up/cancel lifecycle, undo/redo stacks, undoable canvas clear, observer change events)
  - `ui/canvas_widget.py`: `CanvasWidget` (PySide6 `QPainter` rendering, antialiasing, dynamic cursor, pen/eraser modes, mouse event dispatch)
  - `ui/color_palette.py`: `ColorPalette` (10-color quick palette + QColorDialog picker)
  - `ui/toolbar.py`: `WhiteboardToolbar` (Pen/Eraser toggles, color palette, preset size chips, slider, undo/redo/clear, fullscreen presentation button, status badge)
  - `ui/main_window.py`: `MainWindow` (status bar with live normalized/pixel coordinate readout and stroke count, comprehensive keyboard shortcuts: `Ctrl+Z`, `Ctrl+Y`, `Ctrl+Shift+Z`, `Ctrl+L`, `F11`, `Escape`, `P`, `E`, `1-4`)
  - `main.py` & `desktop/run.py`: executable launcher
- **Test Results:**
  - 23 unit and GUI tests in `tests/`: 23 passed in 0.21s (0 warnings)
  - Static analysis: `ruff check desktop tests` passed with 0 errors
  - Application runtime verification: launched headless with offscreen QPA, initialized UI, processed events, and closed cleanly with exit code 0.

## Phase 0 milestone checklist
- [x] Place `AGENTS.md` at repository root.
- [x] Place `docs/PROJECT_SPEC.md` in repository.
- [x] Place `docs/PROJECT_STATUS.md` in repository.
- [x] Connect local git tracking to `origin/main` (`https://github.com/karthikcmani/DoodleLink.git`).
- [x] Preserve existing commit (`ee5d7f92da452a7e8ca18116acd639de486924ff`) and MIT `LICENSE`.
- [x] Create comprehensive `.gitignore` for Python, Android/Gradle, and Windows.
- [x] Create project `README.md` with system overview, architecture, and setup instructions.
- [x] Establish initial directory structure (`android/`, `desktop/`, `shared/protocol/`, `tests/`).
- [x] Pin and install desktop requirements (`desktop/requirements.txt`), verifying PySide6 6.12.0 and pytest.
- [x] Verify Java (JDK 21) and Android SDK (platforms 34+, build-tools 34+, adb).
- [x] Commit foundation files with Conventional Commit message (`1dc6a25`).
- [x] Push to `origin/main` (`ee5d7f9..feb7a93`).

## Phase 1 milestone checklist
- [x] Implement normalized coordinate stroke model (`Point`, `Stroke`, `ToolType`).
- [x] Implement viewport aspect ratio mapper (`CoordinateMapper`).
- [x] Implement decoupled canvas state and undo/redo logic (`CanvasState`).
- [x] Implement interactive PySide6 drawing canvas (`CanvasWidget`).
- [x] Implement whiteboard toolbar with tools, palette, thickness, and actions (`WhiteboardToolbar`).
- [x] Implement main window with keyboard shortcuts and coordinate status bar (`MainWindow`).
- [x] Establish Protocol v1 schema (`shared/protocol/schema_v1.json`).
- [x] Write comprehensive unit tests for models, coordinates, canvas state, and UI.
- [x] Verify test execution (`pytest`: 23 passed) and static checks (`ruff`: clean).
- [x] Verify application launch and rendering.
- [ ] Commit Phase 1 milestone with Conventional Commit and push to `origin/main`.

## Next milestone
**Phase 2 — Android drawing foundation**
- Initialize native Android project with Gradle, Kotlin, and Jetpack Compose (`android/`).
- Implement touch drawing surface and normalized logical stroke model matching `shared/protocol`.
- Implement local tool selection (Pen, Eraser, Color, Brush size), undo/redo, and canvas clear.
- Test lifecycle events, orientation changes, and build debug APK.
