# DoodleLink — Product & Engineering Specification

**Repository:** https://github.com/karthikcmani/DoodleLink  
**Project name:** DoodleLink  
**Document status:** Initial baseline — decisions are provisional only where explicitly marked  
**Primary target:** Windows 11 + Android phone (initial test device: Nothing Phone (3a), 8 GB / 256 GB)  
**Development approach:** Antigravity-led autonomous engineering, milestone-based, GitHub-tracked

---

## 1. Product vision

DoodleLink turns an Android phone into a responsive drawing tablet and remote whiteboard for a Windows PC. A user draws with a finger or compatible stylus on the phone; the same strokes appear on the PC whiteboard with minimal perceived delay.

The product must feel like a practical lightweight graphics tablet, not a screen-mirroring application. The phone sends drawing events and input metadata, not continuous screenshots or video.

DoodleLink is intended for studying, teaching, explaining diagrams, annotating learning material, brainstorming, and presenting handwritten content on a laptop or projector.

## 2. Product principles

1. **Local-first:** Core drawing works without internet, cloud accounts, or a hosted backend.
2. **Responsive:** Drawing should feel immediate; latency and dropped strokes are treated as core quality issues.
3. **Cross-device consistency:** The phone and desktop render the same logical strokes from a shared, versioned data model.
4. **Reliable:** Reconnection, interrupted gestures, resizing, and application lifecycle changes must not corrupt the canvas.
5. **Lightweight:** Avoid unnecessary frameworks, background services, dependencies, and resource usage.
6. **Open source:** MIT license unless the repository already establishes a different license.
7. **Incremental delivery:** A working phone-to-PC drawing path comes before advanced annotation and presentation features.
8. **Honest status:** Planned, implemented, tested, and hardware-verified are distinct states.

## 3. Target users and primary scenarios

### Primary scenarios
- Draw handwritten notes and diagrams on the phone; see them live on the laptop.
- Use the laptop as a larger display or projector while drawing on the phone.
- Explain neural networks, equations, flowcharts, architecture diagrams, and lecture concepts.
- Use the desktop whiteboard independently with a mouse.
- Save a session and export a page as PNG or PDF.
- Annotate PDF material and present it on the laptop.

### Non-goals for the initial MVP
- Cloud synchronization or user accounts.
- Video/screen streaming as the normal drawing transport.
- Replacing professional illustration software.
- Guaranteed pressure sensitivity on devices that do not expose pressure data.
- Full PowerPoint file editing. Presentation support should be scoped carefully; PDF annotation is the first document workflow.

## 4. Supported platforms and connection modes

### Initial platforms
- Android phone: native Android application.
- Desktop: Windows 11 application.
- Initial real-device target: Nothing Phone (3a).

### Connection modes
1. **Same Wi-Fi network:** Phone and PC are on the same LAN.
2. **Phone hotspot:** PC joins the phone's hotspot; internet access is not required.
3. **USB:** Provide a wired mode. Preferred first implementation is ADB reverse port forwarding for development/advanced users when USB debugging and ADB are available. Also investigate USB tethering as a user-facing alternative. Do not claim universal plug-and-play USB support until tested on the target device and Windows.
4. **Discovery and manual pairing:** Support QR code or short pairing code where practical, plus manual IP/port entry as a reliable fallback.

The connection screen must clearly show connection state, selected transport, peer identity, and actionable troubleshooting.

## 5. Applications and responsibilities

### 5.1 Android application

Responsibilities:
- Discover or connect to a desktop host.
- Display a touch-first drawing canvas.
- Capture pointer/stylus input.
- Send normalized drawing events to the desktop.
- Receive session state and remote commands where supported.
- Display connection status and recover from disconnects.

Initial tools:
- Pen.
- Eraser.
- Colour selection.
- Brush size.
- Undo and redo.
- Clear canvas (with confirmation or undo).
- Canvas orientation support.
- Optional palm rejection / stylus-specific behavior only where supported and tested.

The UI should have a minimal toolbar that does not obstruct drawing. A full-screen drawing mode and a toolbar mode are both required. The application must remain usable with finger input; stylus support is an enhancement, not a hard dependency.

### 5.2 Windows desktop application

Responsibilities:
- Host the local WebSocket endpoint.
- Pair with and receive events from Android.
- Render strokes smoothly on a large canvas.
- Provide standalone mouse drawing.
- Maintain document/page/session state.
- Support export and document annotation in later milestones.

Initial tools:
- Pen and eraser.
- Colour and brush-size controls.
- Undo/redo.
- Clear canvas.
- New page / page navigation (after MVP).
- Save and reopen session (after MVP).
- Export PNG and PDF (after MVP).
- PDF import and annotation (later milestone).
- Presentation/fullscreen mode (later milestone).

Desktop UI should be clean, resizable, and suitable for laptop displays and projectors.

## 6. Technology baseline

The current baseline is selected for native Android input, practical Windows packaging, and a straightforward shared protocol.

| Layer | Baseline |
|---|---|
| Android | Kotlin |
| Android UI | Jetpack Compose |
| Android drawing surface | Custom Canvas / native drawing layer, chosen after input-latency prototype |
| Windows desktop | Python |
| Desktop UI | PySide6 |
| Desktop drawing | QPainter / custom QWidget drawing surface |
| Transport | WebSocket over local TCP |
| Message format | Versioned JSON control and stroke events initially |
| Large payloads | Binary messages only if profiling justifies them |
| Android build | Gradle |
| Desktop packaging | PyInstaller or another verified Windows packaging route |
| Version control | Git + GitHub |

Before installing or upgrading toolchains, inspect what is already installed and compatible. Avoid duplicating SDKs or changing working machine configuration unnecessarily. Record exact versions in `docs/PROJECT_STATUS.md` when established.

### Architecture constraints
- Keep UI, drawing model, transport, session state, and persistence in separate modules.
- Define a platform-independent logical stroke model.
- Use normalized coordinates (0.0–1.0) relative to the logical canvas so device and desktop aspect ratios can differ.
- Store stroke colour, width, tool, points, timestamps/sequence identifiers as needed.
- Keep transport independent of UI frameworks.
- Use a versioned protocol and validate every incoming message.
- The desktop must be able to render a received stroke without requiring a screenshot from the phone.

## 7. Communication and drawing protocol

### 7.1 Transport
Use a WebSocket connection over a local TCP socket. The desktop normally acts as host/server and the phone as client. Do not require an internet connection or external relay.

### 7.2 Event model
At minimum, define and document:
- `hello` / protocol negotiation.
- `pair` or authenticated session establishment.
- `stroke_start`.
- `stroke_points` or batched `stroke_move`.
- `stroke_end`.
- `stroke_cancel`.
- `undo`.
- `redo`.
- `clear_canvas`.
- `ping` / `pong` or heartbeat.
- `error` / capability response.

Every drawing event must include enough information to associate it with a stroke and preserve ordering. Include protocol version, session identifier, stroke identifier, sequence number, normalized coordinates, tool, colour, and width where relevant.

Use pointer lifecycle semantics: down, move, up, cancel. Do not leave a stroke permanently open if the phone app is interrupted.

### 7.3 Performance and correctness
- Coalesce or batch move points without losing the overall path.
- Preserve event order.
- Avoid retransmitting the entire canvas for every movement.
- Handle reconnect and stale sessions.
- Reject malformed, oversized, unsupported, or out-of-range messages safely.
- Provide a visible disconnected/reconnecting state.
- Define a sensible maximum message size and rate limits.
- Measure latency and dropped/missing strokes on real hardware before claiming performance targets.

### 7.4 Security
- Default to local-network-only use.
- Pair devices using a short-lived code, QR token, or equivalent session secret.
- Do not expose an unauthenticated server on public interfaces.
- Avoid logging drawing content or pairing secrets.
- Explain any firewall permission requested by Windows.
- Do not collect analytics or transmit user content externally.

## 8. Coordinate system and rendering

Use a logical canvas independent of physical screen pixels:
- `x` and `y` normalized to `[0, 1]`.
- Width represented consistently relative to the logical canvas or a documented reference dimension.
- Preserve aspect ratio and define how letterboxing/panning/zooming affect coordinate mapping.
- Keep a single source of truth for the logical canvas transform.
- Ensure strokes remain correctly aligned when the desktop window is resized or the phone rotates.
- Use smoothing/interpolation only when it does not introduce visible lag or distort handwriting.

Pressure and tilt may be included as optional fields with safe defaults. The app must behave correctly when the hardware provides no pressure or tilt data.

## 9. Data, sessions, and export

Later milestones should introduce a local session format that can preserve:
- Canvas dimensions and background.
- Pages and page order.
- Strokes and tool metadata.
- Session metadata and format version.

Requirements:
- Save and reopen without data loss.
- Version the file format.
- Handle invalid or older files safely.
- Export individual pages to PNG and PDF.
- Do not require cloud storage.

The exact persistence format (for example JSON plus optional binary assets) should be chosen after the MVP data model is stable.

## 10. PDF and presentation workflows

PDF annotation is a post-MVP feature:
- Import a PDF on desktop.
- Display pages at a stable zoom/scroll position.
- Draw annotations over a coordinate-mapped overlay.
- Keep original PDF content unchanged.
- Save annotated output as a new PDF or a DoodleLink project.
- Make page navigation and zoom predictable.

Presentation mode should provide a clean, distraction-free canvas suitable for screen sharing or a projector. PowerPoint integration is not part of the first release; evaluate PDF export/import as the reliable cross-platform route first.

## 11. UX requirements

### Android
- Connection status is always discoverable.
- Drawing surface receives input across the available canvas.
- Toolbar controls have comfortable touch targets.
- Undo/redo and eraser are easy to reach.
- Avoid accidental navigation while drawing.
- Handle orientation changes and app background/resume.
- Provide clear permission explanations.

### Windows
- Canvas is the primary focus.
- Toolbar controls are discoverable and keyboard accessible.
- Window resizing does not distort existing drawings.
- Connection/pairing errors provide actionable guidance.
- Fullscreen presentation mode must be escapable with a clear keyboard shortcut.
- Support mouse input as a fallback and standalone mode.

## 12. Delivery roadmap and acceptance criteria

### Phase 0 — Repository and engineering foundation
Deliver:
- Root `AGENTS.md` persistent Antigravity rules.
- This product specification.
- `docs/PROJECT_STATUS.md`.
- README with project overview and development status.
- `.gitignore` and MIT license verification.
- Clean initial project structure only where needed.

Acceptance:
- Antigravity reads the repository rules.
- Git status is understood; no user work is overwritten.
- Build/toolchain prerequisites are documented.
- Foundation is committed and pushed if remote access is available and authorized.

### Phase 1 — Desktop whiteboard foundation
Deliver a Windows app that opens a blank canvas and supports mouse drawing, pen colour/width, eraser, undo/redo, and clear.

Acceptance:
- App launches on Windows.
- Drawing works smoothly with mouse.
- Undo/redo and eraser behave correctly.
- Unit tests cover core stroke/history logic.

### Phase 2 — Android drawing foundation
Deliver an Android app with a responsive touch canvas and the same logical stroke model.

Acceptance:
- App builds and installs on the target phone.
- Finger drawing works.
- Tool selection and undo/redo work locally.
- Orientation/lifecycle behavior is tested.

### Phase 3 — End-to-end Wi-Fi synchronization (MVP)
Deliver desktop host + Android client with pairing and live stroke transfer.

Acceptance:
- Phone connects to desktop on the same Wi-Fi.
- Phone drawing appears on desktop in real time.
- No internet connection is needed.
- Stroke order and pointer end/cancel are correct.
- Reconnect and invalid-message handling are tested.
- Real-device test is recorded.

### Phase 4 — Hotspot and USB connectivity
Deliver reliable phone-hotspot operation and a documented wired mode.

Acceptance:
- Hotspot test works without internet.
- USB method is tested on the target Windows/Android setup.
- Setup instructions, ADB requirements or tethering steps, and known limitations are documented.
- Do not label USB fully supported until tested.

### Phase 5 — Session and export
Deliver pages, save/open, PNG export, and PDF export.

Acceptance:
- Saved session reopens with identical strokes and page order.
- PNG/PDF output is verified visually.
- Invalid files fail safely.

### Phase 6 — PDF annotation and presentation
Deliver PDF import, annotation overlay, annotated export, and fullscreen presentation.

Acceptance:
- Annotations remain aligned at different zoom levels.
- Original PDF remains unmodified.
- Presentation mode is stable and keyboard escapable.

### Phase 7 — Hardening and release
Deliver performance tuning, packaging, documentation, security review, and release artifacts.

Acceptance:
- Fresh setup instructions are tested.
- Desktop executable and Android APK are built.
- Regression tests pass.
- Known limitations are documented.
- Release notes and version tags are created only after verification.

## 13. Testing strategy

Use layered tests:
- Unit tests for stroke model, coordinate transforms, undo/redo, serialization, and protocol validation.
- Integration tests for WebSocket message ordering, reconnects, invalid messages, and session handling.
- UI tests where practical.
- Build verification for Android and Windows.
- Real hardware tests on the target Android phone and Windows laptop.
- Manual latency and drawing continuity checks.

For each test, record:
- Exact command or procedure.
- Environment and device.
- Pass/fail result.
- Known limitation.
- Whether it was automated or manual.

Never claim hardware verification from emulator-only testing.

## 14. Repository and Git conventions

Use the existing repository:
`https://github.com/karthikcmani/DoodleLink`

Suggested structure (adapt to the real repo; do not destroy existing work):

```text
DoodleLink/
├── AGENTS.md
├── README.md
├── LICENSE
├── .gitignore
├── android/
├── desktop/
├── shared/
│   └── protocol/
├── docs/
│   ├── PROJECT_SPEC.md
│   └── PROJECT_STATUS.md
└── tests/
```

Commit format: Conventional Commits.
Examples:
- `docs: establish DoodleLink engineering baseline`
- `feat(desktop): add standalone whiteboard canvas`
- `feat(android): add touch drawing surface`
- `feat(sync): stream strokes over local websocket`
- `fix(sync): recover interrupted strokes after reconnect`

Do not commit generated build output, local IDE state, virtual environments, signing credentials, secrets, or personal machine paths.

## 15. Antigravity autonomous execution contract

Antigravity is expected to act as the primary engineering agent:
1. Read `AGENTS.md`, `docs/PROJECT_SPEC.md`, `docs/PROJECT_STATUS.md`, README, and relevant source before each task.
2. Inspect repository state before changes.
3. Select the smallest complete milestone that advances the product.
4. Implement, build, test, diagnose, and repair autonomously where possible.
5. Update status and relevant docs based on verified outcomes.
6. Commit coherent, passing milestones using Conventional Commits.
7. Push only when permitted and never force-push.
8. Keep this specification stable; modify it only when product requirements or durable technical decisions genuinely change.
9. If a requirement is ambiguous but does not block safe progress, choose a conservative implementation and record the assumption. Ask the user only when a decision is genuinely blocking or risky.
10. Never claim completion based only on generated code or an unexecuted plan.

## 16. Current decisions and open questions

### Decisions already made
- Product name: DoodleLink.
- Public GitHub repository: `karthikcmani/DoodleLink`.
- Android + Windows desktop applications.
- Phone supports both full-screen drawing and a toolbar-equipped drawing mode.
- Desktop supports a canvas-only workflow and expanded whiteboard/document/presentation workflows.
- Support wireless and wired connection modes.
- Local-first operation; internet is not required for core drawing.
- Baseline stack: Kotlin/Jetpack Compose for Android; Python/PySide6 for Windows; WebSocket for local transport.

### Open implementation choices
These should be resolved through prototypes/evidence, not guesswork:
- Best Android drawing surface for low-latency input under current Android/Compose versions.
- QR pairing implementation and local discovery mechanism.
- Whether USB should use ADB reverse, USB tethering, or both in the polished UX.
- Session serialization format.
- PDF rendering/annotation library and licensing compatibility.
- Windows packaging and installer approach.
- Pressure/tilt support on the target device and any stylus.

Update this section only when an open choice is resolved. Include a short rationale and date in the relevant status or architecture decision record.

---

**End of specification.** This document is the durable agreement for product intent and engineering direction. Keep it accurate, stable, and concise enough to remain useful; do not turn it into a daily activity log.
