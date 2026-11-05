"""
HyperSolve Frameless Desktop Command Center
Decoupled standalone window providing live assessment telemetry,
Ghost Shield controls, AI Brain monitor, and human mimicry configuration.
"""

import sys
import os
import asyncio
import threading
import subprocess
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSlider, QProgressBar,
    QGraphicsDropShadowEffect, QSystemTrayIcon
)
from PyQt6.QtGui import (
    QColor, QFont, QCursor, QPainter, QLinearGradient, QIcon
)
from PyQt6.QtCore import (
    Qt, QPoint, pyqtSignal, pyqtSlot, QTimer, QObject
)

from hypersolve.__version__ import __version__
from hypersolve.stealth.ghost_shield import GhostShield
from hypersolve.updater.engine import OTAUpdateManager
from hypersolve.core.daemon import HyperSolveDaemon
from hypersolve.desktop.tray import HyperSolveTrayApp

class DashboardBridge(QObject):
    target_attached = pyqtSignal(str)
    questions_harvested = pyqtSignal(int, list)
    answer_injected = pyqtSignal(int, str, str, float)
    assessment_completed = pyqtSignal(int, int, str)
    brain_detected = pyqtSignal(str)
    shield_toggled = pyqtSignal(bool)


class QuestionCard(QFrame):
    """Visual telemetry card showing a question, selected option, and confidence."""
    def __init__(self, q_num: int, text: str, selected_option: str = "Analyzing...", confidence: float = 0.0, parent=None):
        super().__init__(parent)
        self.q_num = q_num
        self.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: Q number + Badge
        header = QHBoxLayout()
        self.num_lbl = QLabel(f"QUESTION {q_num}")
        self.num_lbl.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 11px;")
        header.addWidget(self.num_lbl)

        header.addStretch()

        self.badge = QLabel("ROUTING")
        self.badge.setStyleSheet("""
            background-color: #0284c7;
            color: white;
            font-size: 10px;
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 4px;
        """)
        header.addWidget(self.badge)
        layout.addLayout(header)

        # Question text snippet
        self.text_lbl = QLabel(text[:95] + ("..." if len(text) > 95 else ""))
        self.text_lbl.setWordWrap(True)
        self.text_lbl.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: 500;")
        layout.addWidget(self.text_lbl)

        # Selected Option
        self.opt_lbl = QLabel(f"➔ {selected_option}")
        self.opt_lbl.setStyleSheet("color: #38bdf8; font-size: 12px; font-style: italic;")
        layout.addWidget(self.opt_lbl)

    def set_answer(self, option_text: str, confidence: float, verified: bool = False):
        self.opt_lbl.setText(f"➔ {option_text}")
        if verified:
            self.badge.setText("VERIFIED ✓")
            self.badge.setStyleSheet("background-color: #059669; color: white; font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
            self.setStyleSheet("QFrame { background-color: #064e3b; border: 1px solid #10b981; border-radius: 8px; }")
        else:
            self.badge.setText(f"LOCKED {confidence:.1f}%")
            self.badge.setStyleSheet("background-color: #0284c7; color: white; font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
            self.setStyleSheet("QFrame { background-color: #1e293b; border: 1px solid #0284c7; border-radius: 8px; }")


class HyperSolveDashboard(QWidget):
    """Frameless, transparent-glass desktop command center decoupled from Chrome."""

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        super().__init__()
        self.cdp_url = cdp_url
        self.bridge = DashboardBridge()
        self.daemon: Optional[HyperSolveDaemon] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._drag_pos = QPoint()
        self.cards: Dict[int, QuestionCard] = {}

        self._init_window()
        self._build_ui()
        self._wire_bridge()
        self._start_daemon_thread()

    def _init_window(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinMaxButtonsHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(760, 620)
        self.setMinimumSize(680, 520)

    def _build_ui(self):
        # Outer Layout with Shadow container
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame#MainContainer {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 14px;
            }
        """)
        self.container.setObjectName("MainContainer")

        # Soft glow shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(6, 182, 212, 60)) # Cyan glow
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. Custom Draggable Title Bar
        # -------------------------------------------------------------
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 4)

        logo = QLabel("⚡ HYPERSOLVE COMMAND CENTER")
        logo.setStyleSheet("color: #06b6d4; font-weight: 800; font-size: 13px; letter-spacing: 1px;")
        title_bar.addWidget(logo)

        ver_badge = QLabel(f"v{__version__}")
        ver_badge.setStyleSheet("color: #64748b; font-size: 11px; margin-left: 6px;")
        title_bar.addWidget(ver_badge)

        title_bar.addStretch()

        # Window Controls
        min_btn = QPushButton("—")
        min_btn.setFixedSize(28, 28)
        min_btn.setStyleSheet("QPushButton { background-color: #1e293b; color: #94a3b8; border-radius: 6px; font-weight: bold; border: none; } QPushButton:hover { background-color: #334155; color: white; }")
        min_btn.clicked.connect(self.showMinimized)
        title_bar.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("QPushButton { background-color: #1e293b; color: #94a3b8; border-radius: 6px; font-weight: bold; border: none; } QPushButton:hover { background-color: #ef4444; color: white; }")
        close_btn.clicked.connect(self.hide) # Hides to tray without killing daemon
        title_bar.addWidget(close_btn)

        layout.addLayout(title_bar)

        # -------------------------------------------------------------
        # 2. Status & Metric Cards Row
        # -------------------------------------------------------------
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(10)

        # Ghost Shield Card
        self.shield_card = QFrame()
        self.shield_card.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 8px; padding: 10px; border: 1px solid #334155; }")
        s_layout = QVBoxLayout(self.shield_card)
        s_layout.setContentsMargins(10, 8, 10, 8)
        s_title = QLabel("🛡️ GHOST SHIELD")
        s_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self.shield_val = QLabel("ARMED")
        self.shield_val.setStyleSheet("color: #10b981; font-size: 14px; font-weight: 800;")
        s_layout.addWidget(s_title)
        s_layout.addWidget(self.shield_val)
        metrics_row.addWidget(self.shield_card)

        # AI Session Card
        self.ai_card = QFrame()
        self.ai_card.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 8px; padding: 10px; border: 1px solid #334155; }")
        a_layout = QVBoxLayout(self.ai_card)
        a_layout.setContentsMargins(10, 8, 10, 8)
        a_title = QLabel("🧠 ACTIVE BRAIN")
        a_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self.ai_val = QLabel("ChatGPT (Web Tab)")
        self.ai_val.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: 800;")
        a_layout.addWidget(a_title)
        a_layout.addWidget(self.ai_val)
        metrics_row.addWidget(self.ai_card)

        # Target Accuracy Card
        self.score_card = QFrame()
        self.score_card.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 8px; padding: 10px; border: 1px solid #334155; }")
        sc_layout = QVBoxLayout(self.score_card)
        sc_layout.setContentsMargins(10, 8, 10, 8)
        sc_title = QLabel("🎯 TARGET GRADE")
        sc_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self.score_val = QLabel("100% (Turbo)")
        self.score_val.setStyleSheet("color: #f59e0b; font-size: 14px; font-weight: 800;")
        sc_layout.addWidget(sc_title)
        sc_layout.addWidget(self.score_val)
        metrics_row.addWidget(self.score_card)

        layout.addLayout(metrics_row)

        # -------------------------------------------------------------
        # 3. Live Assessment Telemetry Feed (Scrollable)
        # -------------------------------------------------------------
        feed_header = QHBoxLayout()
        self.feed_title = QLabel("LIVE ASSESSMENT TELEMETRY")
        self.feed_title.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 12px; letter-spacing: 0.5px;")
        feed_header.addWidget(self.feed_title)
        feed_header.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #06b6d4;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setValue(0)
        feed_header.addWidget(self.progress_bar)
        layout.addLayout(feed_header)

        # Scroll Area for Questions
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: #0f172a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 4px;
            }
        """)

        self.feed_container = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(8)

        # Standby placeholder
        self.empty_lbl = QLabel("Waiting for an active assessment tab (Moodle, Canvas, Forms)...")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color: #64748b; font-size: 13px; padding: 40px;")
        self.feed_layout.addWidget(self.empty_lbl)

        self.scroll.setWidget(self.feed_container)
        layout.addWidget(self.scroll)

        # -------------------------------------------------------------
        # 4. Bottom Controls & Action Bar
        # -------------------------------------------------------------
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.toggle_shield_btn = QPushButton("Toggle Shield")
        self.toggle_shield_btn.setStyleSheet(self._btn_style("#1e293b", "#334155"))
        self.toggle_shield_btn.clicked.connect(self._toggle_shield)
        btn_bar.addWidget(self.toggle_shield_btn)

        self.launch_chrome_btn = QPushButton("Launch Exam Chrome")
        self.launch_chrome_btn.setStyleSheet(self._btn_style("#0284c7", "#0369a1"))
        self.launch_chrome_btn.clicked.connect(self._launch_chrome)
        btn_bar.addWidget(self.launch_chrome_btn)

        btn_bar.addStretch()

        self.panic_btn = QPushButton("👻 Panic Vanish (Ctrl+Shift+X)")
        self.panic_btn.setStyleSheet(self._btn_style("#dc2626", "#b91c1c"))
        self.panic_btn.clicked.connect(self.hide)
        btn_bar.addWidget(self.panic_btn)

        layout.addLayout(btn_bar)
        outer.addWidget(self.container)

    def _btn_style(self, bg: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 14px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """

    # -------------------------------------------------------------
    # Mouse Drag Handling for Frameless Window
    # -------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    # -------------------------------------------------------------
    # Bridge Slots & Event Handlers
    # -------------------------------------------------------------
    def _wire_bridge(self):
        self.bridge.target_attached.connect(self._on_target_attached)
        self.bridge.questions_harvested.connect(self._on_questions_harvested)
        self.bridge.answer_injected.connect(self._on_answer_injected)
        self.bridge.assessment_completed.connect(self._on_assessment_completed)

    def _on_target_attached(self, url: str):
        self.empty_lbl.hide()
        self.feed_title.setText(f"TARGET ATTACHED: {url[:55]}...")
        self.progress_bar.setValue(10)

    def _on_questions_harvested(self, count: int, questions: list):
        self.empty_lbl.hide()
        self.progress_bar.setValue(40)
        # Clear existing cards
        for card in self.cards.values():
            card.deleteLater()
        self.cards.clear()

        # Render question cards
        for q in questions:
            card = QuestionCard(q.get("id", len(self.cards) + 1), q.get("text", ""))
            self.cards[q.get("id")] = card
            self.feed_layout.addWidget(card)

    def _on_answer_injected(self, q_num: int, text: str, opt: str, conf: float):
        if q_num in self.cards:
            self.cards[q_num].set_answer(opt, conf, verified=False)
        self.progress_bar.setValue(min(90, self.progress_bar.value() + 5))

    def _on_assessment_completed(self, injected: int, total: int, brain: str):
        self.progress_bar.setValue(100)
        self.feed_title.setText(f"COMPLETED: {injected}/{total} Solved via {brain} 🎉")

    def _toggle_shield(self):
        GhostShield.is_enabled = not GhostShield.is_enabled
        state = "ARMED" if GhostShield.is_enabled else "DISARMED"
        color = "#10b981" if GhostShield.is_enabled else "#ef4444"
        self.shield_val.setText(state)
        self.shield_val.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 800;")

    def _launch_chrome(self):
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        profile_dir = os.path.join(script_dir, "chrome_profile")
        cmd = f'start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="{profile_dir}" "https://chatgpt.com"'
        subprocess.Popen(cmd, shell=True)

    def _start_daemon_thread(self):
        def runner():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.daemon = HyperSolveDaemon(
                cdp_url=self.cdp_url,
                on_target_attached=lambda url: self.bridge.target_attached.emit(url),
                on_solved=lambda inj, tot, brain: self.bridge.assessment_completed.emit(inj, tot, brain),
            )
            try:
                self.loop.run_until_complete(self.daemon.start())
            except Exception:
                pass

        t = threading.Thread(target=runner, daemon=True, name="HyperSolve-Daemon-Worker")
        t.start()


def run_dashboard():
    app = QApplication(sys.argv)
    dashboard = HyperSolveDashboard()
    dashboard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_dashboard()
