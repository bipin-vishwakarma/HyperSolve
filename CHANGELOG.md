# 2.3.0 — Visible interactive session overlay

- Keep the browser panel visible through harvesting, solving, selection, navigation, and completion.
- Add Pause/Resume, Stop, Show question, Copy answers, Collapse/Expand, dragging and keyboard positioning.
- Preserve panel state and selected answers across quiz pages; use generation-aware control bindings for restarted sessions.
- Protect automated option clicks from hitting the overlay, and keep controls reachable in small viewports.
- Synchronize paused state with the desktop and preserve shutdown cleanup during cancellation.

# 2.2.0 — Saved workspaces and automation

- Save and restore local web-tab snapshots while retaining the Chrome profile.
- Add manually started automatic quiz detection alongside selected-tab sessions.
- Detect supported question structures instead of relying only on URL keywords.
- Keep watching after a completed quiz; stop on terminal provider errors.
- Preserve quiz query/hash identities and show restore failures per tab.

# 2.1.0 — Windows desktop refresh

- Replace the decorative command centre with Workspace, Connections, and Settings.
- Add explicit tab selection, Start/Stop, real engine events, persistent window geometry, optional close-to-tray, and single-instance restoration.
- Share one app lifecycle across desktop and tray; leave Chrome open on exit.
- Add an authored multi-resolution icon, executable version metadata, and a bundled GUI entry point.
- Replace source-linked setup with a per-user standalone installer and reproducible Windows build.
- Require a trusted release checksum before launching updates; surface failures in the UI.
- Remove generated confidence percentages and first-option fallback; reject malformed vision coordinates and overlapping screenshot operations.
- Add offline regression checks. Live provider compatibility remains separately unverified.

---

# 📜 HyperSolve Changelog

All notable changes to the **HyperSolve** project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

---

## [2.0.0] - 2026-09-10

### 🚀 Highlights
- **Zero API Key Multi-Brain Harvester**: Eliminated mandatory developer API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`). HyperSolve now harvests and queries active authenticated sessions and cookies from **ChatGPT**, **Google Gemini**, and **Claude** directly over Chrome DevTools Protocol without focus stealing.
- **Native Windows Dynamic Island HUD**: Built an OS-level top-level frosted-glass Dynamic Island pill (PyQt6) that floats above any browser or application.
- **100% Screen Share & Recording Invisibility**: Integrated Windows Display Affinity (`SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)`) making the overlay invisible to Zoom, MS Teams, Google Meet, Discord, and OBS.
- **Universal Multi-Strategy Question Parser**: Zero-selector engine supporting Moodle, Aspirations Institute, Google Forms, Canvas, and Blackboard via native Accessibility Trees (`aria-role`) and structural card heuristics.
- **Ghost Shield**: Neutralizes `visibilitychange`, `blur`, and `hidden` events, preventing LMS proctoring tools from flagging tab switches.
- **Humanized Bézier Mouse Pilot**: Smooth non-linear mouse trajectories for synthetic clicks.
- **Codebase Restructure**: Archived legacy monolithic scripts (`full_auto.py`, `start_all.bat`) to `archive/v1-legacy/` and established clean modular architecture.

---

## [1.0.0] - 2026-09-09

### Initial Release
- Initial proof-of-concept autonomous assessment solver.
- Basic CDP connection and tab switching.
- Prototype CSS selector matching for Moodle quizzes.
