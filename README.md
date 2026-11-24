# DoodleLink

> Open-source Android-to-Windows drawing tablet and smart whiteboard.

DoodleLink transforms an Android phone into a responsive drawing tablet and remote whiteboard for a Windows PC. Users draw with a finger or compatible stylus on their phone, and strokes appear on the Windows desktop canvas in near real time.

DoodleLink is designed for students, teachers, lecturers, and engineers to sketch diagrams, annotate lecture materials, explain equations, and present handwritten ideas cleanly on laptops or projectors.

---

## Key Principles

- **Local-First:** Operates entirely over local networks without requiring internet access, accounts, or third-party servers.
- **Event-Based Synchronization:** Transmits structured pen/touch vector events instead of streaming video frames or screenshots.
- **Low Latency & Responsive:** Optimized event coalescing and fast rendering ensure strokes feel immediate.
- **Cross-Device Consistency:** Normalized logical canvas coordinate model `[0.0, 1.0]` guarantees faithful rendering across different screen dimensions and aspect ratios.
- **Lightweight & Modular:** Independent modules for canvas UI, drawing models, transport, and session persistence.

---

## Connection Modes

1. **Same Wi-Fi Network:** Automatic discovery or quick manual pairing over local LAN.
2. **Phone Hotspot:** Direct connection when external Wi-Fi is unavailable (offline operation).
3. **USB Connection:** Wired mode via ADB reverse port forwarding or USB tethering for ultra-low latency.

---

## Architecture & Technology Baseline

| Component | Technology | Description |
|---|---|---|
| **Android Client** | Kotlin / Jetpack Compose | Native touch surface, input event capture, and local preview |
| **Desktop Host** | Python 3.13 / PySide6 (Qt) | Desktop whiteboard canvas, event receiver, session management |
| **Transport** | Local WebSocket (TCP) | Bidirectional JSON event exchange with bounds-checked protocol |
| **Persistence** | Local Vector Sessions | Multi-page session saving, PNG/PDF export, PDF annotation |

---

## Repository Structure

```text
DoodleLink/
├── AGENTS.md                  # Autonomous agent workflow rules and instructions
├── README.md                  # Project overview and setup documentation
├── LICENSE                    # MIT License
├── .gitignore                 # Version control exclusions
├── android/                   # Native Android application (Kotlin / Jetpack Compose)
├── desktop/                   # Windows desktop application (Python / PySide6)
│   └── requirements.txt       # Python desktop dependencies
├── shared/
│   └── protocol/              # Logical stroke schema and protocol definitions
├── docs/
│   ├── PROJECT_SPEC.md        # Comprehensive product & engineering specification
│   └── PROJECT_STATUS.md      # Live milestone progress, verified facts, and test records
└── tests/                     # Integration tests and protocol test suites
```

---

## Development Prerequisites

### Windows Environment
- **Operating System:** Windows 11 (64-bit)
- **Python:** Python 3.13+
- **Desktop Dependencies:**
  ```powershell
  pip install -r desktop/requirements.txt
  ```

### Android Environment
- **JDK:** OpenJDK 21 LTS (`JAVA_HOME` configured)
- **Android SDK:** Platform API 34+, Build Tools 34.0.0+ (`ANDROID_HOME` configured)
- **Platform Tools:** `adb` available on system PATH
- **Target Test Device:** Nothing Phone (3a) (Android 14+)

---

## Roadmap

- **Phase 0:** Repository and engineering foundation *(Current)*
- **Phase 1:** Desktop whiteboard foundation (standalone canvas, mouse drawing, undo/redo)
- **Phase 2:** Android drawing foundation (touch canvas, stroke model, tools)
- **Phase 3:** End-to-end Wi-Fi synchronization (MVP)
- **Phase 4:** Hotspot and USB connectivity
- **Phase 5:** Session management and PNG/PDF export
- **Phase 6:** PDF annotation and presentation mode
- **Phase 7:** Hardening, packaging, and release

---

## License

This project is licensed under the [MIT License](LICENSE) &copy; 2026 Karthik C Mani.
