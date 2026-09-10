<div align="center">

# ⚡ HYPERSOLVE ⚡
### Universal Autonomous Assessment Engine & Cyberpunk In-Browser HUD

[![Python](https://img.shields.io/badge/Python-3.10%2B-00f3ff?style=for-the-badge&logo=python&logoColor=black)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-CDP-05ffa1?style=for-the-badge&logo=playwright&logoColor=black)](https://playwright.dev/)
[![Stealth](https://img.shields.io/badge/Isolation-Closed_Shadow_DOM-ff007f?style=for-the-badge)](https://developer.mozilla.org/en-US/docs/Web/API/ShadowRoot/mode)
[![License](https://img.shields.io/badge/License-MIT-white?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Eliminate brittle CSS selectors. Stop tab-bouncing. Dominate any quiz, form, or assessment in parallel with a futuristic, non-detectable HUD.</b>
</p>

</div>

---

## 🌌 Overview

Most automated quiz tools rely on hardcoded CSS selectors (like `.que` or `.qtext`) that break the second a platform updates its frontend. Furthermore, they aggressively steal window focus by switching back and forth between tabs.

**HyperSolve** re-engineers browser automation from the ground up:
- 👁️ **Zero-Selector Semantic Parsing**: Uses the browser's **Accessibility Tree (A11y)** and semantic clustering to understand questions on *any* platform (Moodle, Canvas, Blackboard, Google Forms).
- 🛡️ **Closed Shadow-DOM HUD**: Injects a glowing cyberpunk HUD with laser scanlines, live confidence pills, and a floating dock—rendered inside `attachShadow({ mode: 'closed' })` so page scripts and anti-cheat trackers cannot detect it.
- 🧠 **Ghost Neural Mesh (Zero Tab-Switching)**: Queries background AI sessions (ChatGPT, Gemini, Claude) directly over Chrome DevTools Protocol without ever switching active tabs.
- 🫀 **Breathing Keep-Alive Daemon**: Prevents Chrome tab discarding and session timeouts with background micro-pulses during lengthy exams.
- ⚡ **Panic Vanish Key (`Ctrl + Shift + X`)**: Instantly purges the HUD from the DOM in 0 milliseconds.

---

## 🏛️ System Architecture

```text
                           ┌──────────────────────────────────────────────┐
                           │               HYPERSOLVE CORE                │
                           │          Autonomous Asyncio Daemon           │
                           └──────────────────────┬───────────────────────┘
                                                  │
                 ┌────────────────────────────────┴────────────────────────────────┐
                 ▼                                                                 ▼
 ┌───────────────────────────────┐                                 ┌───────────────────────────────┐
 │     ZERO-SELECTOR ENGINE      │                                 │      GHOST NEURAL MESH        │
 │  Accessibility Tree & A11y    │                                 │ Multi-Brain Session Harvester │
 └───────────────┬───────────────┘                                 └───────────────┬───────────────┘
                 │                                                                 │
  ┌──────────────┴──────────────┐                                   ┌──────────────┴──────────────┐
  ▼                             ▼                                   ▼                             ▼
Accessibility Tree         Spatial Clustering              Session Pool Vault            Breathing Daemon
(ARIA roles, groups)     (Bounding box heuristics)       (ChatGPT, Gemini, Claude)       (Keep-Alive Pulse)
  │                             │                                   │                             │
  └──────────────┬──────────────┘                                   └──────────────┬──────────────┘
                 ▼                                                                 ▼
        Normalized Quiz AST                                              Tiered Brain Router
     (Question + Choice Targets)                                         (Fallback & Validations)
                 │                                                                 │
                 └───────────────────────────────┬─────────────────────────────────┘
                                                 ▼
                                   Autonomous Synthetic Injection
                              (PointerEvent -> MouseEvent -> Input)
                                                 │
                                                 ▼
                                   Closed Shadow-DOM HyperHUD
                              (Scanlines & 99% Confidence Badges)
```

---

## ⚡ Key Features

### 1. Universal Zero-Selector Engine
HyperSolve traverses the browser's native Accessibility Tree (`role="radiogroup"`, `role="radio"`, `role="group"`). Because educational platforms must remain accessible to screen readers, this semantic structure is virtually permanent and immune to CSS class obfuscation.

### 2. Isolated Cyberpunk HUD (100% Non-Detectable)
- **Closed Shadow-DOM Isolation**: Page scripts querying `document.querySelectorAll('*')` cannot penetrate or detect the HUD.
- **Holographic Scanline**: Real-time laser sweep across questions currently being analyzed.
- **Confidence Badges**: Floating neon badges above each question (e.g. `⚡ 99.2% Confidence • ChatGPT-4o`).
- **Choice Aura**: Ambient emerald glow locking onto the selected option.
- **Vanish Hotkey**: Press **`Ctrl + Shift + X`** anywhere to vanish the HUD instantly.

### 3. Hardware-Level Synthetic Events
Modern frameworks (React, Angular, Vue) ignore standard `.click()` triggers. HyperSolve dispatches full native event sequences:
```javascript
pointerdown -> mousedown -> focus -> pointerup -> mouseup -> click -> input -> change
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Google Chrome installed

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Launch HyperSolve
Double-click `run_hypersolve.bat` or run:
```bash
python main.py
```

1. Chrome will open with remote debugging enabled on port `9222`.
2. Log in to your AI of choice (ChatGPT, Gemini, or Claude).
3. Navigate to your quiz tab on any LMS or platform.
4. HyperSolve automatically detects the assessment, renders the HUD, and executes full autonomous solving.

---

## ⌨️ Shortcuts & Controls

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| `Ctrl + Shift + X` | **Panic Vanish** | Instantly hides or unmounts the HUD overlay from the active page. |
| `Ctrl + C` | **Stop Daemon** | Safely exits the Python background runner. |

---

## 📂 Project Structure

```text
HyperSolve/
├── run_hypersolve.bat          # 1-Click persistent launcher
├── main.py                     # CLI entrypoint
├── requirements.txt            # Python dependencies
├── .gitignore                  # Shields user Chrome profile & secrets
├── hypersolve/
│   ├── core/
│   │   ├── browser.py          # CDP connection & tab classification
│   │   └── daemon.py           # Main monitoring & orchestrator loop
│   ├── parser/
│   │   └── a11y_engine.py      # Zero-selector accessibility tree parser
│   ├── hud/
│   │   ├── injector.py         # Overlay injection controller
│   │   └── assets/
│   │       ├── overlay.js      # Closed Shadow-DOM HUD & scanline beams
│   │       └── styles.css      # Cyberpunk neon stylesheets
│   ├── router/
│   │   ├── session_pool.py     # Background tab query (Zero focus stealing)
│   │   ├── heartbeat.py        # "Breathing" keep-alive daemon
│   │   └── brain_router.py     # Tiered multi-brain fallback engine
│   └── injector/
│       └── synthetic_events.py # Hardware-level pointer/click dispatcher
└── README.md
```

---

## ⚖️ Disclaimer

HyperSolve is an educational research project and browser automation framework designed to demonstrate advanced web accessibility traversal, closed shadow-DOM encapsulation, and multi-session browser orchestration. Users are responsible for complying with the terms of service of their respective educational institutions and platforms.

---

<div align="center">
  <b>Crafted with ⚡ by <a href="https://github.com/bipin-vishwakarma">Bipin Vishwakarma</a></b>
</div>
