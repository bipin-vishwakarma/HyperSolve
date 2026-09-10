<div align="center">

# ⚡ HYPERSOLVE ⚡
### Universal Autonomous Assessment Engine & Undetectable Desktop Vision HUD

[![Python](https://img.shields.io/badge/Python-3.10%2B-00f3ff?style=for-the-badge&logo=python&logoColor=black)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-Dynamic_Island-41cd52?style=for-the-badge&logo=qt&logoColor=black)](https://riverbankcomputing.com/software/pyqt/)
[![Playwright](https://img.shields.io/badge/Playwright-CDP-05ffa1?style=for-the-badge&logo=playwright&logoColor=black)](https://playwright.dev/)
[![Stealth](https://img.shields.io/badge/Stealth-WDA__EXCLUDEFROMCAPTURE-ff007f?style=for-the-badge)](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity)
[![License](https://img.shields.io/badge/License-MIT-white?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Eliminate brittle CSS selectors. Stop tab-bouncing. Dominate any quiz, test, or assessment across ANY browser or app with an undetectable frosted-glass Dynamic Island HUD.</b>
</p>

</div>

---

## 🌌 Overview

Most automated quiz tools rely on hardcoded CSS selectors (like `.que` or `.qtext`) that break the second a platform updates its frontend. Furthermore, in-browser extensions can be detected by anti-cheat scripts, proctoring tools, and screen-sharing software.

**HyperSolve** provides a two-tier dual architecture:

1. **🖥️ HyperSolve Desktop (OS-Level Dynamic Island HUD)**:
   - Floats a sleek frosted-glass Apple Dynamic Island pill natively on Windows.
   - **100% Screen-Share Invisibility**: Uses Windows Display Affinity (`WDA_EXCLUDEFROMCAPTURE`) so Zoom, MS Teams, Discord, and OBS **cannot capture or record** the overlay.
   - **Cross-Browser & Cross-Platform**: Works over **any** browser (Chrome, Brave, Edge, Firefox), PDF viewers, or desktop apps.
   - **Multimodal Vision AI**: Sub-10ms screen grab analyzed by Gemini 2.0 Flash / GPT-4o-mini to calculate exact normalized click coordinates.
   - **Humanized Bézier Mouse Pilot**: Smooth natural curves to avoid bot-flagging.

2. **🌐 HyperSolve Chromium Engine (Autonomous DOM & CDP Daemon)**:
   - **Zero-Selector Accessibility Tree (A11y)**: Parses ARIA roles (`radiogroup`, `radio`, `group`) impervious to CSS obfuscation.
   - **Ghost Shield**: Hooks and neutralizes `visibilitychange` and `blur` events to silence tab-switch flags.
   - **Ghost Neural Mesh**: Queries background AI sessions (ChatGPT, Gemini, Claude) directly over CDP without switching active tabs.
   - **Closed Shadow-DOM HUD**: Injected inside `attachShadow({ mode: 'closed' })` so page scripts cannot detect it.

---

## 🏛️ System Architecture

```text
                               ┌─────────────────────────────┐
                               │       HYPERSOLVE ECOSYSTEM  │
                               └──────────────┬──────────────┘
                                              │
              ┌───────────────────────────────┴───────────────────────────────┐
              ▼                                                               ▼
  ┌───────────────────────────────┐                               ┌───────────────────────────────┐
  │   HYPERSOLVE DESKTOP (HUD)    │                               │  HYPERSOLVE CHROMIUM (DAEMON) │
  │    Native Windows Vision      │                               │    Zero-Selector CDP Mesh     │
  └──────────────┬────────────────┘                               └───────────────┬───────────────┘
                 │                                                                │
     ┌───────────┴───────────┐                                        ┌───────────┴───────────┐
     ▼                       ▼                                        ▼                       ▼
PyQt6 Dynamic Island   Sub-10ms Grabber                          A11y ARIA Parser        Ghost Shield
(Frosted-Glass Pill)    (mss + Pillow)                         (Zero CSS Selectors)   (Tab Switch Block)
     │                       │                                        │                       │
     ▼                       ▼                                        ▼                       ▼
WDA_EXCLUDEFROMCAPTURE  Multimodal VLM                           Closed Shadow DOM     Ghost Neural Mesh
(Zoom/Teams Invisible) (Gemini 2.0 Flash)                       (Undetectable HUD)    (Background Tabs)
     │                       │                                        │                       │
     └───────────┬───────────┘                                        └───────────┬───────────┘
                 ▼                                                                ▼
       Humanized Bézier Mouse                                          Autonomous DOM Injection
         (Auto-Click Target)                                             (Hardware Event Stream)
```

---

## ⚡ Key Features

### 1. Undetectable Desktop Dynamic Island (`Alt + Q`)
- Native Windows top-level frosted-glass pill floating at top-center.
- Fully draggable anywhere on your screen.
- Screen share immunity via `SetWindowDisplayAffinity(hwnd, 0x00000011)`—visible only to your physical eyes, never to meeting participants or recordings.
- Hit **`Alt + Q`** anywhere: instantly captures the active question, reasons with Vision AI, and clicks the right answer with a human-like mouse curve.
- Hit **`Ctrl + Shift + X`** for emergency panic vanish/restore.

### 2. Universal Zero-Selector Engine
- Traverses the browser's native Accessibility Tree (`role="radiogroup"`, `role="radio"`, `role="group"`).
- Permanent compatibility across Moodle, Canvas, Blackboard, Aspirations Institute, Google Forms, and custom LMS platforms.

### 3. Ghost Shield Anti-Proctoring
- Patches `document.hidden`, `document.visibilityState`, and traps `window.blur` / `visibilitychange`.
- Neutralizes "Tab switch detected" warnings and keeps quizzes unbothered.

### 4. Zero Tab-Switching Neural Harvester
- Extracts responses from background ChatGPT, Gemini, or Claude tabs via Chrome DevTools Protocol without stealing window focus.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Choose Your Mode

#### Option A: HyperSolve Desktop (Recommended for any browser / test)
Simply double-click **`run_desktop.bat`** or run:
```bash
python desktop_main.py
```
- A sleek Dynamic Island HUD will appear at the top-center of your screen.
- Set `GEMINI_API_KEY=your_key` in a `.env` file or environment variable (Free on Google AI Studio).
- Open **ANY** quiz, website, or app (Chrome, Brave, Edge, Firefox, PDF).
- Press **`Alt + Q`** to automatically solve and select the correct answer!
- Press **`Ctrl + Shift + X`** to hide/show the HUD.

#### Option B: HyperSolve Chromium Engine (Autonomous DOM Ingestion)
Double-click **`run_hypersolve.bat`** or run:
```bash
python main.py
```
- Launches Chrome with remote debugging on port `9222`.
- Logs into AI providers in the background and injects a closed Shadow-DOM HUD.

---

## ⌨️ Global Controls & Shortcuts

| Shortcut | Scope | Description |
| :--- | :--- | :--- |
| `Alt + Q` | **Desktop HUD** | Instant screen capture, vision analysis, and auto-click answer. |
| `Ctrl + Shift + X` | **Universal** | Panic Vanish / Restore overlay in 0ms. |
| `Ctrl + C` | **Console** | Safely exits the background runners. |

---

## 📂 Project Structure

```text
HyperSolve/
├── run_desktop.bat             # 1-Click Desktop Dynamic Island HUD launcher
├── run_hypersolve.bat          # 1-Click Chromium Engine launcher
├── desktop_main.py             # Desktop Native PyQt6 application
├── main.py                     # Chromium CDP Daemon entrypoint
├── requirements.txt            # Unified dependencies
├── .gitignore                  # Shields user Chrome profile & secrets
├── hypersolve/
│   ├── desktop/
│   │   ├── overlay_window.py   # PyQt6 Frosted Dynamic Island (WDA_EXCLUDEFROMCAPTURE)
│   │   └── hotkeys.py          # Global low-level keyboard listener (pynput)
│   ├── vision/
│   │   ├── screen_capture.py   # Sub-10ms screen grabber (mss)
│   │   ├── vlm_solver.py       # Multimodal Vision Solver (Gemini 2.0 Flash / GPT-4o-mini)
│   │   └── mouse_pilot.py      # Humanized Bézier mouse navigation & clicker
│   ├── core/
│   │   ├── browser.py          # CDP connection & tab classification
│   │   └── daemon.py           # Main monitoring & orchestrator loop
│   ├── parser/
│   │   └── a11y_engine.py      # Zero-selector accessibility tree parser
│   ├── stealth/
│   │   └── ghost_shield.py     # Tab switch & blur event blocker
│   ├── hud/
│   │   ├── injector.py         # In-browser overlay injection controller
│   │   └── assets/             # Frosted Island JS & CSS assets
│   └── router/
│       ├── session_pool.py     # Background tab query (Zero focus stealing)
│       ├── heartbeat.py        # Breathing keep-alive daemon
│       └── brain_router.py     # Tiered multi-brain fallback engine
└── README.md
```

---

## ⚖️ Disclaimer

HyperSolve is an educational research project and browser automation framework designed to demonstrate advanced web accessibility traversal, screen capture optimization, and multi-session browser orchestration. Users are responsible for complying with the terms of service of their respective educational institutions and platforms.

---

<div align="center">
  <b>Crafted with ⚡ by <a href="https://github.com/bipin-vishwakarma">Bipin Vishwakarma</a></b>
</div>
