import threading
from typing import Callable
from pynput import keyboard

class GlobalHotkeyListener:
    """
    Global Hotkey Listener for HyperSolve Desktop.
    Hooks into Windows keyboard hooks to trigger:
    - Alt + Q: Solve Question on Active Screen
    - Ctrl + Shift + X: Panic Vanish Overlay
    """

    def __init__(self, on_solve: Callable[[], None], on_vanish: Callable[[], None]):
        self.on_solve = on_solve
        self.on_vanish = on_vanish
        self._listener = None
        self._thread = None

    def start(self):
        """Starts the global keyboard listener thread."""
        hotkeys = {
            '<alt>+q': self.on_solve,
            '<ctrl>+<shift>+x': self.on_vanish
        }
        self._listener = keyboard.GlobalHotKeys(hotkeys)
        self._listener.start()
        print("[HOTKEYS] Global Hotkeys Initialized:")
        print("  - [Alt + Q]: Instant Screen Solve")
        print("  - [Ctrl + Shift + X]: Panic Vanish HUD")

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
