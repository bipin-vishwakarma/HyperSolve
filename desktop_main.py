import sys
import os
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

# Force UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from hypersolve.desktop.overlay_window import DesktopOverlayWindow
from hypersolve.desktop.hotkeys import GlobalHotkeyListener
from hypersolve.vision.screen_capture import ScreenCapturer
from hypersolve.vision.vlm_solver import VLMSolver
from hypersolve.vision.mouse_pilot import MousePilot

class Bridge(QObject):
    solve_requested = pyqtSignal()
    vanish_requested = pyqtSignal()
    status_updated = pyqtSignal(str, str)

def main():
    app = QApplication(sys.argv)
    overlay = DesktopOverlayWindow()
    overlay.show()

    bridge = Bridge()
    vlm = VLMSolver()

    # Wire up signals
    bridge.vanish_requested.connect(overlay.toggle_vanish)
    bridge.status_updated.connect(overlay.set_status)

    def do_solve_async():
        bridge.status_updated.emit("Capturing Screen...", "analyzing")
        try:
            # 1. Capture screen
            img = ScreenCapturer.capture_primary_screen()
            bridge.status_updated.emit("Vision AI Solving...", "analyzing")

            # 2. Query VLM Solver
            res = vlm.solve_screen(img)
            if res:
                bridge.status_updated.emit(f"Answer: {res.selected_answer[:22]} ({res.confidence}%)", "solved")
                # 3. Move mouse and click
                MousePilot.click_normalized(res.x_percent, res.y_percent, humanized=True)
            else:
                bridge.status_updated.emit("No question resolved (Set API key)", "error")
        except Exception as e:
            print(f"[SOLVER ERROR] {e}")
            bridge.status_updated.emit("Solve failed", "error")

    def on_solve_hotkey():
        # Dispatch background worker so GUI does not freeze
        threading.Thread(target=do_solve_async, daemon=True).start()

    def on_vanish_hotkey():
        bridge.vanish_requested.emit()

    # Start hotkey listener
    hotkeys = GlobalHotkeyListener(
        on_solve=on_solve_hotkey,
        on_vanish=on_vanish_hotkey
    )
    hotkeys.start()

    print("\n" + "=" * 65)
    print("  ⚡ HYPERSOLVE DESKTOP — NATIVE WINDOWS VISION HUD ⚡")
    print("  [STEALTH] Excluded from Screen Captures (WDA_EXCLUDEFROMCAPTURE)")
    print("  [HOTKEY] Press Alt + Q on ANY browser/app to solve")
    print("  [PANIC]  Press Ctrl + Shift + X to vanish/restore overlay")
    print("=" * 65 + "\n")

    exit_code = app.exec()
    hotkeys.stop()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
