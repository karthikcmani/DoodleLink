# DoodleLink — Project Status

**Last updated:** 2026-11-25  
**Current phase:** Phase 2 — Android drawing foundation  
**Overall status:** Phase 2 completed and verified; ready for Phase 3.

## Verified facts
- **GitHub repository:** `https://github.com/karthikcmani/DoodleLink.git`
- **Git branch:** `main` tracking `origin/main`
- **Host OS:** Windows 11 (build 10.0.26300)
- **Desktop Environment:**
  - Python 3.13.2 (64-bit)
  - `PySide6` 6.12.0, `websockets` 15.0.1, `pytest` 9.1.1, `ruff` 0.14.4
  - 23 desktop tests passing (`pytest`)
- **Android Environment & Toolchain:**
  - `JAVA_HOME`: `C:\Program Files\Eclipse Adoptium\jdk-21.0.13.9-hotspot\` (OpenJDK 21.0.13 LTS)
  - `ANDROID_HOME`: `C:\Users\Asus\AppData\Local\Android\Sdk`
  - Gradle: 8.11.1 (wrapper configured)
  - Android Gradle Plugin (AGP): 8.7.2
  - Kotlin: 2.0.21 with Compose Compiler plugin
  - Jetpack Compose BOM: 2024.10.01 (Material3, Foundation, UI)
  - Compile SDK: 35, Target SDK: 35, Min SDK: 26 (Android 8.0+)
- **Android Application Architecture (`android/app/src/main/java/com/doodlelink/app`):**
  - `model/Point.kt`, `Stroke.kt`, `ToolType.kt`: Normalized coordinate models `[0.0, 1.0]` with timestamps and pressure
  - `model/CoordinateMapper.kt`: 16:9 aspect-ratio letterbox/pillarbox viewport calculations matching desktop
  - `model/CanvasState.kt`: Decoupled stroke state, pointer down/move/up/cancel lifecycle, and full undo/redo stack
  - `model/DoodleJson.kt`: Standard kotlinx.serialization JSON configuration with `encodeDefaults = true` guaranteeing 100% interoperability with desktop Protocol v1
  - `viewmodel/DrawingViewModel.kt`: Jetpack Compose ViewModel retaining drawing state across screen orientation changes
  - `ui/CanvasSurface.kt`: Hardware-accelerated drawing canvas utilizing `pointerInput(awaitEachGesture)` with pressure sensitivity, round caps/joins, and viewport clipping
  - `ui/DrawingControls.kt`: Modern floating toolbar with Pen/Eraser tools, 10-color palette, thickness chips & slider, Undo, Redo, Clear, and Fullscreen presentation mode
  - `MainActivity.kt`: Hardware back & lifecycle handling, config changes for orientation and screen size
- **Test Results:**
  - Android Unit Tests: 15 unit tests in `android/app/src/test/java/com/doodlelink/app/` (`StrokeModelTest`, `CoordinateMapperTest`, `CanvasStateTest`) — all 15 passed in 18s via `gradlew testDebugUnitTest`.
  - Desktop Unit Tests: 23 unit tests in `tests/` — all 23 passed in 0.20s via `pytest`.
  - Static Analysis: `ruff` and Android lint/compiler checks clean.
- **Build Verification:**
  - `gradlew assembleDebug` successfully generated `app-debug.apk` (16.6 MB) at `android/app/build/outputs/apk/debug/app-debug.apk` in 1m 3s.
- **Device Connectivity:**
  - `adb devices` shows no physical device currently attached via USB. APK is ready for installation once Nothing Phone (3a) is connected.

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
- [x] Commit Phase 1 milestone with Conventional Commit (`c21c38d`) and push to `origin/main` (`feb7a93..ac1f906`).

## Phase 2 milestone checklist
- [x] Initialize Android Gradle project with Gradle wrapper 8.11.1, AGP 8.7.2, and Kotlin 2.0.21.
- [x] Implement Kotlin stroke and point data models (`Point`, `Stroke`, `ToolType`, `BoundingBox`).
- [x] Implement Kotlin coordinate mapper (`CoordinateMapper`) with 16:9 aspect ratio geometry.
- [x] Implement decoupled Kotlin canvas state with undo/redo stack (`CanvasState`).
- [x] Implement Protocol v1 JSON serialization with `encodeDefaults = true` (`DoodleJson`).
- [x] Implement Jetpack Compose drawing surface (`CanvasSurface`) with touch/stylus and pressure capture.
- [x] Implement modern drawing toolbar (`DrawingControls`) with tools, palette, thickness, undo/redo/clear, and fullscreen mode.
- [x] Implement `DrawingViewModel` retaining state across portrait/landscape orientation changes.
- [x] Write and run Android unit tests (15 tests passed).
- [x] Assemble and verify debug APK (`app-debug.apk`, 16.6 MB).
- [ ] Commit Phase 2 milestone with Conventional Commit and push to `origin/main`.

## Next milestone
**Phase 3 — End-to-end Wi-Fi synchronization (MVP)**
- Implement local WebSocket host in desktop application.
- Implement pairing flow (short code / token) and connection state UI on desktop.
- Implement WebSocket client in Android application.
- Stream live pointer events (`stroke_start`, `stroke_points`, `stroke_end`, `stroke_cancel`) and actions (`undo`, `redo`, `clear`) over local LAN.
- Handle reconnection, dropouts, and invalid messages gracefully.
- End-to-end multi-device verification test.
