import sys
import ctypes
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont

WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 Version 2004+ (Completely excludes window from screen captures & recordings)

class DesktopOverlayWindow(QWidget):
    """
    Native Windows Top-Level Frosted-Glass Dynamic Island HUD.
    Features:
    - 100% Screen Share & Recording Invisibility via WDA_EXCLUDEFROMCAPTURE
    - Always on top, frameless, translucent background
    - Draggable anywhere on screen
    - Real-time status, active brain display, and hotkey tips
    """

    trigger_solve_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._is_vanished = False
        self._drag_pos = QPoint()
        self._status_text = "Ready (Alt + Q)"
        self._status_state = "idle"  # idle, analyzing, solved, error

        self._init_window()
        self._init_ui()
        self._apply_stealth_affinity()

    def _init_window(self):
        # Frameless, Always on Top, Tool window (no taskbar clutter)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(360, 42)

        # Position at top-center of primary screen
        screen = self.screen().geometry()
        x = (screen.width() - self.width()) // 2
        y = 16
        self.move(x, y)

    def _apply_stealth_affinity(self):
        """Applies Windows Display Affinity to exclude overlay from screen shares/recordings."""
        try:
            hwnd = int(self.winId())
            # Set WDA_EXCLUDEFROMCAPTURE
            res = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            if res:
                print("[STEALTH] Display Affinity Applied: Window excluded from screen capture (Zoom/Teams/OBS).")
            else:
                # Fallback to WDA_MONITOR
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x01)
        except Exception as e:
            print(f"[STEALTH NOTICE] Could not set display affinity: {e}")

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        # Status Dot
        self.dot = QLabel(self)
        self.dot.setFixedSize(8, 8)
        self.dot.setStyleSheet("background: #10b981; border-radius: 4px;")
        layout.addWidget(self.dot)

        # Brand Title
        self.brand = QLabel("⚡ HyperSolve", self)
        self.brand.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 12px;")
        layout.addWidget(self.brand)

        # Separator
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.2); max-height: 14px;")
        layout.addWidget(sep)

        # Status Label
        self.status_label = QLabel(self._status_text, self)
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.status_label, 1)

        # Badge
        self.badge = QLabel("ARMORED", self)
        self.badge.setStyleSheet("""
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            font-size: 9px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 10px;
            border: 1px solid rgba(16, 185, 129, 0.35);
        """)
        layout.addWidget(self.badge)

    def paintEvent(self, event):
        """Draws the frosted-glass rounded pill background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dark Frosted Capsule Background
        brush = QBrush(QColor(13, 17, 23, 230))
        pen = QPen(QColor(255, 255, 255, 30))
        pen.setWidth(1)

        if self._status_state == "analyzing":
            pen = QPen(QColor(0, 243, 255, 120))
        elif self._status_state == "solved":
            pen = QPen(QColor(16, 185, 129, 140))
        elif self._status_state == "error":
            pen = QPen(QColor(239, 68, 68, 140))

        painter.setBrush(brush)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)

    # Mouse Dragging Support
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    # Public Controls
    def set_status(self, text: str, state: str = "idle"):
        self._status_text = text
        self._status_state = state
        self.status_label.setText(text)

        if state == "analyzing":
            self.dot.setStyleSheet("background: #00f3ff; border-radius: 4px;")
            self.badge.setText("ANALYZING")
            self.badge.setStyleSheet("background: rgba(0, 243, 255, 0.15); color: #00f3ff; font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 10px; border: 1px solid rgba(0, 243, 255, 0.35);")
        elif state == "solved":
            self.dot.setStyleSheet("background: #10b981; border-radius: 4px;")
            self.badge.setText("SOLVED")
            self.badge.setStyleSheet("background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 10px; border: 1px solid rgba(16, 185, 129, 0.35);")
        elif state == "error":
            self.dot.setStyleSheet("background: #ef4444; border-radius: 4px;")
            self.badge.setText("ERROR")
            self.badge.setStyleSheet("background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 10px; border: 1px solid rgba(239, 68, 68, 0.35);")
        else:
            self.dot.setStyleSheet("background: #10b981; border-radius: 4px;")
            self.badge.setText("ARMORED")
            self.badge.setStyleSheet("background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 10px; border: 1px solid rgba(16, 185, 129, 0.35);")

        self.update()

    def toggle_vanish(self):
        """Instantly vanishes or reveals the overlay (Ctrl + Shift + X)."""
        self._is_vanished = not self._is_vanished
        if self._is_vanished:
            self.hide()
            print("[STEALTH] HyperSolve Overlay Hidden (Ctrl+Shift+X to restore)")
        else:
            self.show()
            print("[STEALTH] HyperSolve Overlay Restored")
