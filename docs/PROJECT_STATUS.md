# DoodleLink — Project Status

**Last updated:** 2026-11-25  
**Current phase:** Phase 3 — End-to-end Wi-Fi synchronization (MVP)  
**Overall status:** Phase 3 completed and verified; ready for Phase 4.

## Verified facts
- **GitHub repository:** `https://github.com/karthikcmani/DoodleLink.git`
- **Git branch:** `main` tracking `origin/main`
- **Host OS:** Windows 11 (build 10.0.26300)
- **Shared Protocol Baseline:**
  - Protocol v1 JSON schema at `shared/protocol/schema_v1.json`
  - Versioned events: `pair`, `pair_success`, `stroke_start`, `stroke_points`, `stroke_end`, `stroke_cancel`, `undo`, `redo`, `clear_canvas`, `ping`, `pong`, `error`
  - Normalized logical coordinates `[0.0, 1.0] x [0.0, 1.0]` with timestamps and pressure
- **Desktop Host Architecture (`desktop/src/doodlelink`):**
  - `network/protocol.py`: Protocol v1 payload builders and message validator
  - `network/pairing.py`: `PairingManager` with 6-digit secure pairing tokens, constant-time verification, and local network interface discovery
  - `network/server.py`: `WhiteboardServer` running `websockets` asyncio event loop on a daemon thread, emitting Qt signals to main thread, broadcasting drawing events, and rejecting unauthenticated clients
  - `ui/pairing_dialog.py`: `PairingDialog` displaying Host IP, Port, 6-digit code, connected device name, and regeneration button
  - `ui/main_window.py`: Integrated WebSocket server, incoming event routing to `CanvasState`, bidirectional local mouse stroke broadcast to connected clients without echo loops
  - `ui/toolbar.py`: Interactive connection status badge and quick connect button
- **Android Client Architecture (`android/app/src/main/java/com/doodlelink/app`):**
  - `network/ConnectionState.kt`: Connection state machine (`DISCONNECTED`, `CONNECTING`, `CONNECTED`, `RECONNECTING`, `ERROR`)
  - `network/ProtocolMessages.kt`: Serializable Kotlin data classes for all Protocol v1 events
  - `network/WebSocketClient.kt`: OkHttp WebSocket client with automatic pairing handshake, heartbeat ping/pong (10s), exponential backoff auto-reconnect, and outbound stroke/action streaming
  - `ui/ConnectionDialog.kt`: Material3 dialog for entering PC host IP, port, and 6-digit pairing code
  - `ui/DrawingControls.kt`: Interactive toolbar connection status pill
  - `viewmodel/DrawingViewModel.kt`: Coordinated local canvas state and network synchronization
  - `AndroidManifest.xml`: Configured `INTERNET`, `ACCESS_NETWORK_STATE`, and `android:usesCleartextTraffic="true"` for local LAN/Wi-Fi WebSocket access
- **Test Results:**
  - Desktop Tests: 33 tests in `tests/` (`test_stroke_model`, `test_coordinate_mapping`, `test_canvas_state`, `test_ui_canvas`, `test_network_protocol`, `test_pairing_manager`, `test_network_integration`) — all 33 passed in 1.98s via `pytest`.
  - Android Tests: 16 unit and protocol tests in `android/app/src/test/java/com/doodlelink/app/` — all 16 passed in 31s via `gradlew testDebugUnitTest`.
  - Static Analysis: `ruff check desktop tests` clean (0 errors), Android lint/compiler checks clean.
- **Build Verification:**
  - Desktop: Successfully launches headless, initializes WebSocket host, binds port, processes paint events, and cleanly stops.
  - Android: `gradlew assembleDebug` successfully built `app-debug.apk` (17.1 MB) at `android/app/build/outputs/apk/debug/app-debug.apk`.
- **Hardware Verification Limitation:**
  - Checked `adb devices`: no physical device is currently attached via USB. Automated integration tests simulated end-to-end WebSocket connection, unauthorized rejection, pairing handshake, bidirectional stroke streams, undo/redo/clear, and ping-pong heartbeats against the live server. Real hardware drawing will be exercised when Nothing Phone (3a) is connected.

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
- [x] Commit Phase 2 milestone with Conventional Commit (`95bb80f`) and push to `origin/main` (`68f5ef1`).

## Phase 3 milestone checklist
- [x] Expand Protocol v1 JSON schema with pairing handshake events (`pair`, `pair_success`, `error`).
- [x] Implement desktop WebSocket host server on local TCP (`WhiteboardServer`).
- [x] Implement cryptographically secure 6-digit pairing code manager (`PairingManager`).
- [x] Implement Desktop pairing dialog (`PairingDialog`) and toolbar connection status.
- [x] Implement Android OkHttp WebSocket client (`WebSocketClient`) with pairing, heartbeats, and auto-reconnect.
- [x] Implement Android connection UI (`ConnectionDialog`) and status pill.
- [x] Stream real-time drawing events (`stroke_start`, `stroke_points`, `stroke_end`, `stroke_cancel`) and actions (`undo`, `redo`, `clear`) bidirectionally.
- [x] Write desktop and Android network unit and integration tests (33 desktop passed, 16 Android passed).
- [x] Build debug APK and verify desktop app launch.
- [ ] Commit Phase 3 milestone with Conventional Commit and push to `origin/main`.

## Next milestone
**Phase 4 — Hotspot and USB connectivity**
- Verify operation over Android phone Wi-Fi hotspot without external internet connection.
- Implement and document wired USB mode using ADB reverse port forwarding (`adb reverse tcp:8765 tcp:8765`).
- Test USB tethering mode fallback.
- Add connection troubleshooting UI and diagnostics on both applications.
