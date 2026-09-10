import sys
import os
import threading
import requests
from typing import Tuple
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer

# Force UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from hypersolve.__version__ import __version__
from hypersolve.desktop.overlay_window import DesktopOverlayWindow
from hypersolve.desktop.hotkeys import GlobalHotkeyListener
from hypersolve.vision.screen_capture import ScreenCapturer
from hypersolve.vision.vlm_solver import VLMSolver
from hypersolve.vision.mouse_pilot import MousePilot

class Bridge(QObject):
    solve_requested = pyqtSignal()
    vanish_requested = pyqtSignal()
    status_updated = pyqtSignal(str, str)

def detect_active_brain() -> Tuple[str, str]:
    """Detects if an API key or active authenticated browser tab is available."""
    # 1. Check optional developer API keys
    if os.getenv("GEMINI_API_KEY"):
        return "Gemini API (Turbo)", "api"
    if os.getenv("OPENAI_API_KEY"):
        return "GPT-4o API (Turbo)", "api"

    # 2. Check CDP on port 9222 (Zero-API-Key Browser Sessions)
    try:
        res = requests.get("http://127.0.0.1:9222/json", timeout=0.6)
        if res.status_code == 200:
            tabs = res.json()
            for t in tabs:
                url = t.get("url", "").lower()
                if "chatgpt.com" in url or "chat.openai.com" in url:
                    return "ChatGPT (Web Tab)", "chatgpt"
                elif "gemini.google.com" in url:
                    return "Gemini (Web Tab)", "gemini"
                elif "claude.ai" in url:
                    return "Claude (Web Tab)", "claude"
            return "Chrome Connected (No AI tab)", "chrome"
    except Exception:
        pass

    return "No AI Tab (Open ChatGPT in Chrome)", "idle"

def main():
    app = QApplication(sys.argv)
    overlay = DesktopOverlayWindow()
    overlay.show()

    bridge = Bridge()
    vlm = VLMSolver()

    # Wire up signals
    bridge.vanish_requested.connect(overlay.toggle_vanish)
    bridge.status_updated.connect(overlay.set_status)

    # Initial brain detection
    brain_label, brain_state = detect_active_brain()
    if brain_state in ("api", "chatgpt", "gemini", "claude"):
        overlay.set_status(f"Ready (Alt+Q) • {brain_label}", "idle")
    else:
        overlay.set_status("Ready (Alt+Q) • Open ChatGPT in Chrome", "idle")

    # Periodic brain detector (checks every 6 seconds without blocking GUI)
    def check_brain_periodically():
        label, state = detect_active_brain()
        if overlay._status_state == "idle":
            if state in ("api", "chatgpt", "gemini", "claude"):
                overlay.set_status(f"Ready (Alt+Q) • {label}", "idle")
            else:
                overlay.set_status("Ready (Alt+Q) • Open ChatGPT in Chrome", "idle")

    brain_timer = QTimer()
    brain_timer.timeout.connect(check_brain_periodically)
    brain_timer.start(6000)

    def do_solve_async():
        bridge.status_updated.emit("Capturing Screen...", "analyzing")
        try:
            # 1. Capture screen
            img = ScreenCapturer.capture_primary_screen()
            
            brain_name, _ = detect_active_brain()
            bridge.status_updated.emit(f"Solving via {brain_name}...", "analyzing")

            # 2. Query VLM Solver (Supports both zero-key Chrome session & optional API key)
            res = vlm.solve_screen(img)
            if res:
                bridge.status_updated.emit(f"Answer: {res.selected_answer[:22]} ({res.confidence}%)", "solved")
                # 3. Move mouse and click
                MousePilot.click_normalized(res.x_percent, res.y_percent, humanized=True)
            else:
                bridge.status_updated.emit("No answer (Open ChatGPT or Gemini tab)", "error")
        except Exception as e:
            print(f"[SOLVER ERROR] {e}")
            bridge.status_updated.emit("Solve failed", "error")

    def on_solve_hotkey():
        threading.Thread(target=do_solve_async, daemon=True).start()

    def on_vanish_hotkey():
        bridge.vanish_requested.emit()

    # Start global hotkey listener
    hotkeys = GlobalHotkeyListener(
        on_solve=on_solve_hotkey,
        on_vanish=on_vanish_hotkey
    )
    hotkeys.start()

    print("\n" + "=" * 65)
    print(f"  ⚡ HYPERSOLVE DESKTOP v{__version__} — ZERO-API-KEY VISION HUD ⚡")
    print("  [STEALTH] Excluded from Screen Captures (WDA_EXCLUDEFROMCAPTURE)")
    print("  [BRAIN]   Zero-API-Key: Uses active ChatGPT or Gemini tab in Chrome")
    print("  [HOTKEY]  Press Alt + Q on ANY browser/app to solve")
    print("  [PANIC]   Press Ctrl + Shift + X to vanish/restore overlay")
    print("=" * 65 + "\n")

    exit_code = app.exec()
    hotkeys.stop()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
