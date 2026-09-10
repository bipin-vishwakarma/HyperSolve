<div align="center">

# ⚡ HYPERSOLVE v2.0 ⚡
### Universal Autonomous Assessment Engine & Undetectable Desktop Vision HUD
#### Zero API Keys • Zero Focus Stealing • 100% Screen Share Invisible

[![Python](https://img.shields.io/badge/Python-3.10%2B-00f3ff?style=for-the-badge&logo=python&logoColor=black)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Release-v2.0.0-05ffa1?style=for-the-badge)](CHANGELOG.md)
[![Zero-API-Key](https://img.shields.io/badge/API_Keys-NOT_REQUIRED-ff007f?style=for-the-badge)](#-zero-api-key-multi-brain-harvester)
[![PyQt6](https://img.shields.io/badge/PyQt6-Dynamic_Island-41cd52?style=for-the-badge&logo=qt&logoColor=black)](https://riverbankcomputing.com/software/pyqt/)
[![Stealth](https://img.shields.io/badge/Stealth-WDA__EXCLUDEFROMCAPTURE-yellow?style=for-the-badge)](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity)
[![License](https://img.shields.io/badge/License-MIT-white?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Eliminate brittle CSS selectors. Stop tab-bouncing. Forget expensive API keys.<br>
  Dominate any quiz, test, or assessment across ANY browser or desktop app with an undetectable frosted-glass Dynamic Island HUD.</b>
</p>

</div>

---

## 🌌 Overview

Most automated quiz tools rely on hardcoded CSS selectors (like `.que` or `.qtext`) that break whenever a platform updates. Even worse, they require paid developer API keys (OpenAI / Google Cloud billing) or force users to switch tabs constantly, triggering anti-cheat alerts.

**HyperSolve v2.0** re-engineers everything from the ground up:

- 🧠 **Zero API Keys Required**: Automatically harvests and queries active authenticated sessions and cookies from **ChatGPT**, **Google Gemini**, or **Claude** running in your Chrome browser over CDP without stealing window focus.
- 🖥️ **Undetectable Desktop Dynamic Island**: Floats an Apple-style frosted-glass pill natively on Windows that works over **any browser** (Chrome, Edge, Brave, Firefox) or desktop PDF.
- 🛡️ **100% Screen Share & Recording Invisibility**: Employs `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` so Zoom, Microsoft Teams, Google Meet, Discord, and OBS **cannot see or record the overlay**.
- 👁️ **Universal Multi-Strategy Question Parser**: Traverses native browser Accessibility Trees (`aria-role`) and structural card heuristics—immune to CSS obfuscation.
- 🫥 **Ghost Shield**: Hooks and silences `visibilitychange` and `blur` events, eliminating "Tab switch detected" warnings.
- 🖱️ **Humanized Bézier Mouse Pilot**: Smooth non-linear mouse paths and hardware-level clicks.

---

## 🏛️ System Architecture

```text
                               ┌─────────────────────────────┐
                               │     HYPERSOLVE v2.0 CORE    │
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
(Frosted-Glass Pill)   (Native Qt Surface)                     (Zero CSS Selectors)   (Tab Switch Block)
     │                       │                                        │                       │
     ▼                       ▼                                        ▼                       ▼
WDA_EXCLUDEFROMCAPTURE  Zero-Key Harvester                       Closed Shadow DOM     Multi-Brain Router
(Zoom/Teams Invisible) (Active Web Sessions)                    (Undetectable HUD)    (ChatGPT/Gemini CDP)
     │                       │                                        │                       │
     └───────────┬───────────┘                                        └───────────┬───────────┘
                 ▼                                                                ▼
       Humanized Bézier Mouse                                          Autonomous DOM Injection
         (Auto-Click Target)                                             (Hardware Event Stream)
```

---

## 🧠 Zero-API-Key Multi-Brain Harvester

**You do NOT need a paid API key or credit card to use HyperSolve.**

HyperSolve connects to Chrome via Chrome DevTools Protocol (CDP) and queries your already logged-in browser tabs in the background:
1. **ChatGPT** (`chatgpt.com` / `chat.openai.com`): Works with free or Plus accounts.
2. **Google Gemini** (`gemini.google.com`): Works with any standard Google account.
3. **Claude** (`claude.ai`): Works with any free or Pro account.
4. *(Optional)* **Developer Turbo API**: If you have a `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env`, HyperSolve will use it as an optional speed accelerator.

---

## ⚡ Key Features

### 1. Undetectable Desktop Dynamic Island (`Alt + Q`)
- Native Windows top-level frosted-glass pill floating at top-center.
- Draggable anywhere on your screen.
- Screen share immunity via `SetWindowDisplayAffinity(hwnd, 0x00000011)`.
- Hit **`Alt + Q`** anywhere: instantly captures the active question, queries your active AI brain, and clicks the right answer with a human-like mouse curve.
- Hit **`Ctrl + Shift + X`** for emergency panic vanish/restore.

### 2. Universal Zero-Selector Engine
- Traverses the browser's native Accessibility Tree (`role="radiogroup"`, `role="radio"`, `role="group"`).
- Permanent compatibility across Moodle, Canvas, Blackboard, Aspirations Institute, Google Forms, and custom LMS platforms.

### 3. Ghost Shield Anti-Proctoring
- Patches `document.hidden`, `document.visibilityState`, and traps `window.blur` / `visibilitychange`.
- Neutralizes "Tab switch detected" warnings and keeps quizzes unbothered.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Choose Your Mode

#### Option A: HyperSolve Desktop (Recommended for ANY Browser / Quiz / PDF)
Double-click **`run_desktop.bat`** or run:
```bash
python desktop_main.py
```
1. A frosted-glass Dynamic Island HUD will appear at the top-center of your screen.
2. Chrome will launch on port `9222`. Log into **ChatGPT** or **Gemini** in any tab (or leave your existing tab open).
3. The HUD pill will turn green: `⚡ HyperSolve  Ready (Alt+Q) • ChatGPT (Web Tab)`.
4. Open your quiz on **ANY** browser or app and press **`Alt + Q`**!
5. Press **`Ctrl + Shift + X`** at any time to vanish/restore the HUD.

#### Option B: HyperSolve Chromium Engine (Autonomous DOM Ingestion)
Double-click **`run_hypersolve.bat`** or run:
```bash
python main.py
```
- Automatically navigates and clicks through assessments inside Chrome using the Accessibility Tree and Ghost Shield.

---

## ⌨️ Global Controls & Shortcuts

| Shortcut | Scope | Description |
| :--- | :--- | :--- |
| `Alt + Q` | **Desktop HUD** | Instant screen capture, AI analysis via active tab, and auto-click answer. |
| `Ctrl + Shift + X` | **Universal** | Panic Vanish / Restore overlay in 0ms. |
| `Ctrl + C` | **Console** | Safely exits the background runners. |

---

## 📂 Project Structure (v2.0)

```text
HyperSolve/
├── run_desktop.bat             # 1-Click Desktop Dynamic Island HUD launcher
├── run_hypersolve.bat          # 1-Click Chromium Engine launcher
├── desktop_main.py             # Desktop Native PyQt6 application
├── main.py                     # Chromium CDP Daemon entrypoint
├── requirements.txt            # Unified dependencies
├── CHANGELOG.md                # Formal release history (v1.0.0, v2.0.0)
├── .gitignore                  # Shields user Chrome profile & secrets
├── archive/                    # Archived legacy proof-of-concepts
│   └── v1-legacy/
│       ├── full_auto.py        # Original v1 monolithic script
│       ├── start_all.bat       # Original v1 launcher
│       └── README.md
├── hypersolve/
│   ├── __version__.py          # Package metadata (__version__ = "2.0.0")
│   ├── auth/
│   │   └── cookie_vault.py     # Chrome session cookie & token harvester
│   ├── desktop/
│   │   ├── overlay_window.py   # PyQt6 Frosted Dynamic Island (WDA_EXCLUDEFROMCAPTURE)
│   │   └── hotkeys.py          # Global low-level keyboard listener (pynput)
│   ├── vision/
│   │   ├── screen_capture.py   # Sub-10ms native Qt screen grabber
│   │   ├── vlm_solver.py       # Zero-key browser session & vision solver
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
│       ├── session_pool.py     # Zero-API-key tab querying (ChatGPT, Gemini, Claude)
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
