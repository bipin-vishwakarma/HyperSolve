"""
HyperSolve Professional Command Center v2.0
Production-grade native Windows application with decoupled frameless dark-glass UI,
AppUserModelID taskbar identity, live telemetry, AI session manager,
Ghost Shield proctoring armor, human mimicry engine, and OTA updater.
"""

import sys
import os
import ctypes
import asyncio
import threading
import subprocess
import webbrowser
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSlider, QProgressBar,
    QStackedWidget, QLineEdit, QCheckBox, QGraphicsDropShadowEffect,
    QSystemTrayIcon, QSizePolicy
)
from PyQt6.QtGui import (
    QColor, QFont, QCursor, QPainter, QLinearGradient, QIcon, QPixmap, QPen
)
from PyQt6.QtCore import (
    Qt, QPoint, pyqtSignal, pyqtSlot, QTimer, QObject
)

from hypersolve.__version__ import __version__
from hypersolve.stealth.ghost_shield import GhostShield
from hypersolve.updater.engine import OTAUpdateManager, UpdateInfo
from hypersolve.core.daemon import HyperSolveDaemon

# -------------------------------------------------------------
# Register Native Windows Application Identity
# Prevents grouping under "Python" in the Windows Taskbar & Alt+Tab
# -------------------------------------------------------------
APP_ID = "HyperSolve.AutonomousEngine.CommandCenter.2.0"
if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

REPO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICON_PATH = os.path.join(REPO_DIR, "installer", "hypersolve.ico")

class DashboardBridge(QObject):
    target_attached = pyqtSignal(str)
    questions_harvested = pyqtSignal(int, list)
    answer_injected = pyqtSignal(int, str, str, float)
    assessment_completed = pyqtSignal(int, int, str)
    brain_detected = pyqtSignal(str)
    ota_status = pyqtSignal(str, object)


class QuestionCard(QFrame):
    def __init__(self, q_num: int, text: str, selected_option: str = "Analyzing question...", confidence: float = 0.0, parent=None):
        super().__init__(parent)
        self.q_num = q_num
        self.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.num_lbl = QLabel(f"QUESTION {q_num}")
        self.num_lbl.setStyleSheet("color: #94a3b8; font-weight: 800; font-size: 11px; letter-spacing: 0.5px;")
        header.addWidget(self.num_lbl)
        header.addStretch()

        self.badge = QLabel("ROUTING")
        self.badge.setStyleSheet("background-color: #0284c7; color: white; font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
        header.addWidget(self.badge)
        layout.addLayout(header)

        self.text_lbl = QLabel(text[:95] + ("..." if len(text) > 95 else ""))
        self.text_lbl.setWordWrap(True)
        self.text_lbl.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: 500;")
        layout.addWidget(self.text_lbl)

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
    """Production Frameless Command Center GUI for Windows."""

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        super().__init__()
        self.cdp_url = cdp_url
        self.bridge = DashboardBridge()
        self.daemon: Optional[HyperSolveDaemon] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._drag_pos = QPoint()
        self.cards: Dict[int, QuestionCard] = {}
        self.latest_update_info: Optional[UpdateInfo] = None

        self._init_window()
        self._build_ui()
        self._wire_bridge()
        self._start_daemon_thread()

    def _init_window(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinMaxButtonsHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("HyperSolve Command Center")
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.resize(840, 660)
        self.setMinimumSize(780, 560)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self.container = QFrame(self)
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet("""
            QFrame#MainContainer {
                background-color: #0b0f19;
                border: 1px solid #1e293b;
                border-radius: 14px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(6, 182, 212, 50))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. Custom Frameless Draggable Title Bar
        # -------------------------------------------------------------
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 2)

        logo = QLabel("⚡ HYPERSOLVE COMMAND CENTER")
        logo.setStyleSheet("color: #06b6d4; font-weight: 800; font-size: 13px; letter-spacing: 1px;")
        title_bar.addWidget(logo)

        ver_badge = QLabel(f"v{__version__} Production")
        ver_badge.setStyleSheet("color: #64748b; font-size: 11px; margin-left: 6px; font-weight: 600;")
        title_bar.addWidget(ver_badge)

        title_bar.addStretch()

        min_btn = QPushButton("—")
        min_btn.setFixedSize(28, 28)
        min_btn.setStyleSheet("QPushButton { background-color: #1e293b; color: #94a3b8; border-radius: 6px; font-weight: bold; border: none; } QPushButton:hover { background-color: #334155; color: white; }")
        min_btn.clicked.connect(self.showMinimized)
        title_bar.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("QPushButton { background-color: #1e293b; color: #94a3b8; border-radius: 6px; font-weight: bold; border: none; } QPushButton:hover { background-color: #ef4444; color: white; }")
        close_btn.clicked.connect(self.hide)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)

        # -------------------------------------------------------------
        # 2. Modern Navigation Bar (Tabs)
        # -------------------------------------------------------------
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(8)

        self.nav_btns = []
        tabs_config = [
            ("📊 Live Telemetry", 0),
            ("🧠 AI Sessions", 1),
            ("🛡️ Ghost Shield", 2),
            ("🎯 Mimicry Engine", 3),
            ("🔄 Updates & System", 4),
        ]

        for text, idx in tabs_config:
            btn = QPushButton(text)
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.setStyleSheet(self._nav_btn_style(idx == 0))
            btn.clicked.connect(lambda chk, i=idx: self._switch_tab(i))
            nav_bar.addWidget(btn)
            self.nav_btns.append(btn)

        nav_bar.addStretch()
        layout.addLayout(nav_bar)

        # -------------------------------------------------------------
        # 3. Stacked View Pages
        # -------------------------------------------------------------
        self.stack = QStackedWidget()

        # Page 0: Live Telemetry
        self.stack.addWidget(self._build_telemetry_page())
        # Page 1: AI Sessions Hub
        self.stack.addWidget(self._build_ai_hub_page())
        # Page 2: Ghost Shield Diagnostics
        self.stack.addWidget(self._build_shield_page())
        # Page 3: Human Mimicry Settings
        self.stack.addWidget(self._build_mimicry_page())
        # Page 4: OTA Updates & Diagnostics
        self.stack.addWidget(self._build_updates_page())

        layout.addWidget(self.stack)

        # -------------------------------------------------------------
        # 4. Global Bottom Action Bar
        # -------------------------------------------------------------
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.launch_chrome_btn = QPushButton("🌐 Launch Exam Chrome")
        self.launch_chrome_btn.setStyleSheet(self._action_btn_style("#0284c7", "#0369a1"))
        self.launch_chrome_btn.clicked.connect(self._launch_chrome)
        btn_bar.addWidget(self.launch_chrome_btn)

        self.fast_solve_btn = QPushButton("⚡ Auto-Solve Active Tab")
        self.fast_solve_btn.setStyleSheet(self._action_btn_style("#059669", "#047857"))
        self.fast_solve_btn.clicked.connect(self._trigger_fast_solve)
        btn_bar.addWidget(self.fast_solve_btn)

        btn_bar.addStretch()

        self.panic_btn = QPushButton("👻 Emergency Panic (Ctrl+Shift+X)")
        self.panic_btn.setStyleSheet(self._action_btn_style("#dc2626", "#b91c1c"))
        self.panic_btn.clicked.connect(self.hide)
        btn_bar.addWidget(self.panic_btn)

        layout.addLayout(btn_bar)
        outer.addWidget(self.container)

    # =========================================================================
    # Page Builders
    # =========================================================================

    def _build_telemetry_page(self) -> QWidget:
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(0, 4, 0, 0)
        l.setSpacing(12)

        # Metrics Row
        m_row = QHBoxLayout()
        m_row.setSpacing(10)

        self.metric_shield = self._make_metric_card("🛡️ GHOST SHIELD", "ARMED", "#10b981")
        self.metric_brain = self._make_metric_card("🧠 BRAIN SESSION", "ChatGPT (Web Tab)", "#38bdf8")
        self.metric_grade = self._make_metric_card("🎯 MIMICRY GRADE", "100% (Turbo)", "#f59e0b")
        self.metric_status = self._make_metric_card("📡 ENGINE STATUS", "MONITORING", "#06b6d4")

        m_row.addWidget(self.metric_shield)
        m_row.addWidget(self.metric_brain)
        m_row.addWidget(self.metric_grade)
        m_row.addWidget(self.metric_status)
        l.addLayout(m_row)

        # Feed Header
        feed_header = QHBoxLayout()
        self.feed_title = QLabel("ACTIVE ASSESSMENT TELEMETRY")
        self.feed_title.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 12px; letter-spacing: 0.5px;")
        feed_header.addWidget(self.feed_title)
        feed_header.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #1e293b; border-radius: 4px; }
            QProgressBar::chunk { background-color: #06b6d4; border-radius: 4px; }
        """)
        self.progress_bar.setValue(0)
        feed_header.addWidget(self.progress_bar)
        l.addLayout(feed_header)

        # Scroll Feed
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: #0f172a; width: 8px; border-radius: 4px; } QScrollBar::handle:vertical { background: #334155; border-radius: 4px; }")

        self.feed_container = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(8)

        self.empty_lbl = QLabel("Waiting for an active assessment tab in Chrome (Moodle, Canvas, Forms)...")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color: #64748b; font-size: 13px; padding: 50px;")
        self.feed_layout.addWidget(self.empty_lbl)

        self.scroll.setWidget(self.feed_container)
        l.addWidget(self.scroll)
        return page

    def _build_ai_hub_page(self) -> QWidget:
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(0, 6, 0, 0)
        l.setSpacing(14)

        desc = QLabel("Manage your zero-API web tab sessions or connect optional direct API keys:")
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        l.addWidget(desc)

        # Provider Cards
        l.addWidget(self._make_provider_card("ChatGPT (OpenAI)", "Active Tab Connected • Free / Plus Session Pool", "https://chatgpt.com", active=True))
        l.addWidget(self._make_provider_card("Google Gemini", "Active Tab Connected • Free Google Account Session", "https://gemini.google.com", active=True))
        l.addWidget(self._make_provider_card("Claude AI", "Web Tab Supported • Anthropic Session", "https://claude.ai", active=False))

        # API Key Fallback Card
        api_card = QFrame()
        api_card.setStyleSheet("QFrame { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px; }")
        a_layout = QVBoxLayout(api_card)
        a_title = QLabel("Optional Developer Turbo API Key (Zero Setup Required)")
        a_title.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: bold;")
        a_desc = QLabel("If no browser tab is open, HyperSolve can seamlessly fall back to your personal API key:")
        a_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")

        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Enter GEMINI_API_KEY or OPENAI_API_KEY (Optional)")
        self.api_input.setStyleSheet("background-color: #0f172a; color: white; border: 1px solid #475569; border-radius: 6px; padding: 8px;")

        a_layout.addWidget(a_title)
        a_layout.addWidget(a_desc)
        a_layout.addWidget(self.api_input)
        l.addWidget(api_card)

        l.addStretch()
        return page

    def _build_shield_page(self) -> QWidget:
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(0, 6, 0, 0)
        l.setSpacing(14)

        header = QLabel("Ghost Shield Anti-Proctoring Matrix")
        header.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: bold;")
        l.addWidget(header)

        features = [
            ("Tab Switch & Blur Interceptor", "Captures and stops 'blur', 'focusout', and 'visibilitychange' before LMS scripts receive them.", True),
            ("Document Visibility Spoofing", "Forces document.visibilityState to permanently return 'visible' and document.hidden to false.", True),
            ("Warning Banner Neutralizer", "Finds and removes any red 'Tab Switch Detected' warning banners from the quiz DOM automatically.", True),
            ("Autosave Event Emulation", "Simulates native hardware pointer events to guarantee answers are saved without triggering cheat flags.", True)
        ]

        for title, detail, default_val in features:
            f_frame = QFrame()
            f_frame.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 8px; padding: 12px; border: 1px solid #334155; }")
            fl = QHBoxLayout(f_frame)
            info_col = QVBoxLayout()
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #f8fafc; font-weight: bold; font-size: 13px;")
            d_lbl = QLabel(detail)
            d_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            d_lbl.setWordWrap(True)
            info_col.addWidget(t_lbl)
            info_col.addWidget(d_lbl)
            fl.addLayout(info_col)

            chk = QCheckBox()
            chk.setChecked(default_val)
            chk.setStyleSheet("QCheckBox::indicator { width: 22px; height: 22px; border-radius: 4px; background-color: #0f172a; border: 1px solid #06b6d4; } QCheckBox::indicator:checked { background-color: #06b6d4; }")
            fl.addWidget(chk)
            l.addWidget(f_frame)

        l.addStretch()
        return page

    def _build_mimicry_page(self) -> QWidget:
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(0, 6, 0, 0)
        l.setSpacing(16)

        title = QLabel("Human Mimicry & Score Calibration")
        title.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: bold;")
        l.addWidget(title)

        desc = QLabel("Adjust how HyperSolve behaves to ensure your score matches a natural top student instead of an obvious 100% bot:")
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        l.addWidget(desc)

        # Target Accuracy Slider Card
        slider_card = QFrame()
        slider_card.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 8px; padding: 16px; border: 1px solid #334155; }")
        s_layout = QVBoxLayout(slider_card)

        self.slider_lbl = QLabel("Target Score: 100% (Perfect / All Correct)")
        self.slider_lbl.setStyleSheet("color: #06b6d4; font-size: 14px; font-weight: bold;")
        s_layout.addWidget(self.slider_lbl)

        self.score_slider = QSlider(Qt.Orientation.Horizontal)
        self.score_slider.setRange(75, 100)
        self.score_slider.setValue(100)
        self.score_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 8px; background: #0f172a; border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #06b6d4; border-radius: 4px; }
            QSlider::handle:horizontal { background: #ffffff; border: 2px solid #06b6d4; width: 18px; margin-top: -5px; margin-bottom: -5px; border-radius: 9px; }
        """)
        self.score_slider.valueChanged.connect(self._on_slider_changed)
        s_layout.addWidget(self.score_slider)

        s_notes = QLabel("Dialing down to 90%-95% introduces natural second-choice variance so exams look authentically human.")
        s_notes.setStyleSheet("color: #64748b; font-size: 12px; margin-top: 6px;")
        s_layout.addWidget(s_notes)
        l.addWidget(slider_card)

        l.addStretch()
        return page

    def _build_updates_page(self) -> QWidget:
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(0, 6, 0, 0)
        l.setSpacing(14)

        title = QLabel("Over-The-Air (OTA) Updates & Diagnostics")
        title.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: bold;")
        l.addWidget(title)

        up_card = QFrame()
        up_card.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 8px; padding: 16px; border: 1px solid #334155; }")
        u_layout = QVBoxLayout(up_card)

        cur_ver = QLabel(f"Installed Version: v{__version__} (Production Channel)")
        cur_ver.setStyleSheet("color: #f8fafc; font-size: 14px; font-weight: bold;")
        u_layout.addWidget(cur_ver)

        self.update_status_lbl = QLabel("Status: You are running the latest version.")
        self.update_status_lbl.setStyleSheet("color: #10b981; font-size: 13px;")
        u_layout.addWidget(self.update_status_lbl)

        btn_row = QHBoxLayout()
        self.check_update_btn = QPushButton("🔄 Check for Updates Now")
        self.check_update_btn.setStyleSheet(self._action_btn_style("#0284c7", "#0369a1"))
        self.check_update_btn.clicked.connect(self._manual_check_ota)
        btn_row.addWidget(self.check_update_btn)

        self.install_update_btn = QPushButton("🚀 Install Update Silently")
        self.install_update_btn.setStyleSheet(self._action_btn_style("#059669", "#047857"))
        self.install_update_btn.setEnabled(False)
        self.install_update_btn.clicked.connect(self._install_ota_update)
        btn_row.addWidget(self.install_update_btn)
        btn_row.addStretch()

        u_layout.addLayout(btn_row)
        l.addWidget(up_card)

        # Release Notes Box
        self.notes_box = QLabel("Release Notes:\n • 3-phase rapid full quiz harvesting engine\n • Zero-API ChatGPT & Gemini web tab session pool\n • Native Windows Frameless Command Center & System Tray\n • Ghost Shield Anti-Proctoring tab switch neutralizer")
        self.notes_box.setStyleSheet("background-color: #0f172a; color: #94a3b8; padding: 14px; border-radius: 8px; font-size: 12px; line-height: 1.5; border: 1px solid #1e293b;")
        l.addWidget(self.notes_box)

        l.addStretch()
        return page

    # =========================================================================
    # Helpers & Component Factories
    # =========================================================================

    def _make_metric_card(self, title: str, value: str, val_color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 8px; padding: 10px; border: 1px solid #334155; }")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        v_lbl = QLabel(value)
        v_lbl.setObjectName("ValLbl")
        v_lbl.setStyleSheet(f"color: {val_color}; font-size: 13px; font-weight: 800;")
        cl.addWidget(t_lbl)
        cl.addWidget(v_lbl)
        return card

    def _make_provider_card(self, name: str, status: str, url: str, active: bool) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 8px; padding: 12px; border: 1px solid #334155; }")
        l = QHBoxLayout(card)

        col = QVBoxLayout()
        nl = QLabel(name)
        nl.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: bold;")
        sl = QLabel(status)
        sl.setStyleSheet(f"color: {'#10b981' if active else '#94a3b8'}; font-size: 12px;")
        col.addWidget(nl)
        col.addWidget(sl)
        l.addLayout(col)

        l.addStretch()

        open_btn = QPushButton("Open Session")
        open_btn.setStyleSheet(self._action_btn_style("#334155", "#475569"))
        open_btn.clicked.connect(lambda: webbrowser.open(url))
        l.addWidget(open_btn)
        return card

    def _nav_btn_style(self, checked: bool) -> str:
        bg = "#06b6d4" if checked else "#1e293b"
        color = "#0b0f19" if checked else "#94a3b8"
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                font-size: 12px;
                font-weight: 700;
                padding: 7px 14px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {'#22d3ee' if checked else '#334155'};
                color: {'#0b0f19' if checked else '#ffffff'};
            }}
        """

    def _action_btn_style(self, bg: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:disabled {{
                background-color: #334155;
                color: #64748b;
            }}
        """

    def _switch_tab(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == idx)
            btn.setStyleSheet(self._nav_btn_style(i == idx))

    def _on_slider_changed(self, val: int):
        if val == 100:
            txt = "100% (Perfect / All Correct)"
            desc = "100% (Turbo)"
        elif val >= 95:
            txt = f"{val}% (Top Distinction A+)"
            desc = f"{val}% (A+)"
        elif val >= 90:
            txt = f"{val}% (Natural Top Grade A)"
            desc = f"{val}% (A)"
        else:
            txt = f"{val}% (Realistic Pass B+)"
            desc = f"{val}% (B+)"
        self.slider_lbl.setText(f"Target Score: {txt}")
        val_lbl = self.metric_grade.findChild(QLabel, "ValLbl")
        if val_lbl:
            val_lbl.setText(desc)
        if self.daemon:
            self.daemon.target_accuracy = val / 100.0

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
    # Bridge Slots & Events
    # -------------------------------------------------------------
    def _wire_bridge(self):
        self.bridge.target_attached.connect(self._on_target_attached)
        self.bridge.questions_harvested.connect(self._on_questions_harvested)
        self.bridge.answer_injected.connect(self._on_answer_injected)
        self.bridge.assessment_completed.connect(self._on_assessment_completed)
        self.bridge.ota_status.connect(self._on_ota_status)

    def _on_target_attached(self, url: str):
        self.empty_lbl.hide()
        self.feed_title.setText(f"TARGET ATTACHED: {url[:50]}...")
        self.progress_bar.setValue(15)
        val_lbl = self.metric_status.findChild(QLabel, "ValLbl")
        if val_lbl:
            val_lbl.setText("SOLVING")

    def _on_questions_harvested(self, count: int, questions: list):
        self.empty_lbl.hide()
        self.progress_bar.setValue(45)
        for card in self.cards.values():
            card.deleteLater()
        self.cards.clear()

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
        val_lbl = self.metric_status.findChild(QLabel, "ValLbl")
        if val_lbl:
            val_lbl.setText("STANDBY")

    def _on_ota_status(self, msg: str, info: Optional[UpdateInfo]):
        self.update_status_lbl.setText(f"Status: {msg}")
        if info:
            self.latest_update_info = info
            self.install_update_btn.setEnabled(True)
            self.install_update_btn.setText(f"🚀 Install v{info.version} Silently")

    def _manual_check_ota(self):
        self.update_status_lbl.setText("Status: Pinging GitHub Releases API...")
        def check():
            info = OTAUpdateManager.check_for_updates()
            if info:
                self.bridge.ota_status.emit(f"Update Available: v{info.version} ready!", info)
            else:
                self.bridge.ota_status.emit("You are running the latest version.", None)
        threading.Thread(target=check, daemon=True).start()

    def _install_ota_update(self):
        if self.latest_update_info:
            self.update_status_lbl.setText("Status: Downloading payload and launching silent installer...")
            threading.Thread(
                target=lambda: OTAUpdateManager.download_and_install_update(self.latest_update_info, silent=True),
                daemon=True
            ).start()

    def _launch_chrome(self):
        profile_dir = os.path.join(REPO_DIR, "chrome_profile")
        cmd = f'start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="{profile_dir}" "https://chatgpt.com"'
        subprocess.Popen(cmd, shell=True)

    def _trigger_fast_solve(self):
        if self.daemon and self.loop:
            self.feed_title.setText("Scanning open tabs...")

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
    # Register Native Windows Application Identity
    # Prevents grouping under "Python" in the Windows Taskbar & Alt+Tab
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass
        # Auto-hide any console window attached to this process
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0) # SW_HIDE

    app = QApplication(sys.argv)
    app.setApplicationName("HyperSolve Command Center")
    app.setApplicationDisplayName("HyperSolve Command Center")
    app.setOrganizationName("HyperSolve")
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))
    dashboard = HyperSolveDashboard()
    dashboard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_dashboard()
