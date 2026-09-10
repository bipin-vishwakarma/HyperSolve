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
