"""Native desktop workspace with explicit runs and a shared tray lifecycle."""
import asyncio
import ctypes
from datetime import datetime
import logging
import os
import sys
import threading
import webbrowser

from PyQt6.QtCore import Qt, QSettings, QThread, QTimer, pyqtSignal, QUrl, QLockFile
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QStackedWidget, QComboBox, QCheckBox, QPlainTextEdit,
    QSystemTrayIcon, QMenu, QMessageBox, QProgressBar, QToolButton, QSizePolicy,
)
from hypersolve.__version__ import __version__
from hypersolve.core.daemon import HyperSolveDaemon
from hypersolve.updater.engine import OTAUpdateManager
from .runtime import (
    APP_ID, RESOURCE_DIR, DATA_DIR, LOG_DIR, CDP_URL,
    configure_logging, inspect_connection, launch_chrome,
)

STYLE = """
QWidget { background: #f3f4f8; color: #24293b; font-family: 'Segoe UI'; font-size: 14px; }
QFrame#Sidebar, QFrame#Sidebar QWidget { background: #191e2e; color: #bdc5d9; }
QFrame#Sidebar QLabel#Brand { color: #ffffff; font-size: 20px; font-weight: 600; }
QFrame#Sidebar QPushButton { text-align: left; background: transparent; color: #bdc5d9; border: 0; padding: 12px 13px; }
QFrame#Sidebar QPushButton:hover { background: #252c42; color: white; }
QFrame#Sidebar QPushButton:checked { background: #313c60; color: white; }
QFrame#Sidebar QLabel#RailState { color: #cbd4f3; background: #252c42; padding: 10px; border-radius: 5px; }
QLabel { background: transparent; }
QLabel#Title { font-size: 30px; font-weight: 600; color: #1d2335; }
QLabel#Subtitle, QLabel#Muted { color: #606b82; }
QLabel#Section { font-size: 16px; font-weight: 600; }
QLabel#Status { color: #3c4f83; background: #e9edfb; padding: 7px 12px; border-radius: 4px; }
QFrame#Panel { background: white; border: 1px solid #dfe3ed; border-radius: 8px; }
QFrame#Panel QCheckBox { background: transparent; }
QPushButton { background: #ffffff; border: 1px solid #c2c9da; padding: 9px 15px; border-radius: 5px; font-weight: 600; }
QPushButton:hover { background: #eceffa; border-color: #8d9ab8; }
QPushButton:pressed { background: #e1e6f5; }
QPushButton:focus, QComboBox:focus, QCheckBox:focus { border: 2px solid #3759dc; }
QPushButton#Primary { background: #3759dc; border-color: #3759dc; color: white; }
QPushButton#Primary:hover { background: #2945b5; }
QPushButton:disabled, QPushButton#Primary:disabled { background: #e7eaf1; border-color: #d8deea; color: #6c7589; }
QComboBox { background: #ffffff; border: 1px solid #c2c9da; border-radius: 5px; padding: 10px; min-height: 20px; }
QComboBox QAbstractItemView { background: white; selection-background-color: #e9edfb; selection-color: #24293b; }
QCheckBox { spacing: 10px; padding: 8px 0; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #8d9ab8; border-radius: 3px; background: white; }
QCheckBox::indicator:checked { background: #3759dc; border: 1px solid #3759dc; image: url(CHECK_ICON); }
QFrame#Panel QLabel#Status { background: #e9edfb; }
QPlainTextEdit { background: white; border: 1px solid #dfe3ed; border-radius: 5px; padding: 10px; font-family: 'Cascadia Mono', 'Consolas'; font-size: 12px; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #c2c9da; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QToolButton { color: #3c4f83; background: transparent; border: 0; padding: 6px 0; text-align: left; }
QToolButton:hover { color: #2945b5; }
QToolButton:focus { border: 1px solid #3759dc; }
QLabel#EmptyTitle { font-size: 21px; font-weight: 600; color: #303b5a; }
QLabel#StepTitle { font-weight: 600; color: #303b5a; }
QLabel#StepDetail { color: #606b82; font-size: 12px; }
QFrame#Workbench { background: white; border: 1px solid #dfe3ed; border-radius: 9px; }
QFrame#Workbench QScrollArea, QFrame#Workbench QWidget#ResultBody { background: white; }
QFrame#Divider { background: #dfe3ed; max-height: 1px; border: 0; }
QProgressBar { background: #e4e8f3; border: 0; border-radius: 2px; max-height: 4px; }
QProgressBar::chunk { background: #3759dc; border-radius: 2px; }
QMenu { background: white; border: 1px solid #dfe3ed; padding: 4px; }
QMenu::item { padding: 8px 20px; }
QMenu::item:selected { background: #e9edfb; }
"""


def label(text, name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    if primary:
        widget.setObjectName("Primary")
    return widget


def panel():
    frame = QFrame()
    frame.setObjectName("Panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(12)
    return frame, layout


class FunctionWorker(QThread):
    result = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function

    def run(self):
        try:
            self.result.emit(self.function())
        except Exception as exc:
            logging.exception("Background operation failed")
            self.failed.emit(str(exc))


class EngineWorker(QThread):
    event = pyqtSignal(str, object)
    failed = pyqtSignal(str)

    def __init__(self, target_url, parent=None, *, target_id=None):
        super().__init__(parent)
        self.target_url = target_url
        self.target_id = target_id
        self._loop = None
        self._task = None
        self._stop_requested = threading.Event()
        self._lock = threading.Lock()

    async def _run_engine(self):
        with self._lock:
            self._loop = asyncio.get_running_loop()
            self._task = asyncio.current_task()
        if self._stop_requested.is_set():
            with self._lock:
                self._loop = self._task = None
            return
        daemon = HyperSolveDaemon(target_url=self.target_url, target_id=self.target_id, on_event=self.event.emit)
        try:
            await daemon.start()
        except asyncio.CancelledError:
            pass
        finally:
            with self._lock:
                self._loop = self._task = None

    def run(self):
        try:
            asyncio.run(self._run_engine())
        except Exception as exc:
            logging.exception("Engine stopped unexpectedly")
            self.failed.emit(str(exc))

    def stop(self):
        self._stop_requested.set()
        with self._lock:
            if self._loop and self._task:
                self._loop.call_soon_threadsafe(self._task.cancel)


class HyperSolveDashboard(QWidget):
    def __init__(self, cdp_url=CDP_URL, *, auto_scan=True):
        super().__init__()
        self.cdp_url = cdp_url
        self.settings = QSettings("HyperSolve", "Desktop")
        self.engine = None
        self.jobs = []
        self.scanning = False
        self.connection = {"connected": False, "providers": [], "targets": []}
        self.latest_update = None
        self.question_rows = {}
        self._quitting = False
        self.setWindowTitle("HyperSolve")
        self.setWindowIcon(QIcon(str(RESOURCE_DIR / "hypersolve.ico")))
        self.resize(1160, 780)
        self.setMinimumSize(860, 620)
        self.setStyleSheet(STYLE.replace("CHECK_ICON", (RESOURCE_DIR / "check.svg").as_posix()))
        self._build_ui()
        self._build_tray()
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_connection)
        if auto_scan:
            self.timer.start(6000)
            QTimer.singleShot(0, self.refresh_connection)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(198)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 28, 14, 20)
        side.setSpacing(7)
        brand = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(QIcon(str(RESOURCE_DIR / "hypersolve.ico")).pixmap(32, 32))
        brand.addWidget(mark)
        brand.addWidget(label("HyperSolve", "Brand"))
        side.addLayout(brand)
        side.addSpacing(34)
        self.nav = []
        for index, text in enumerate(("Workspace", "Connections", "Settings")):
            item = button(text, lambda checked=False, i=index: self.switch_page(i))
            item.setIcon(QIcon(str(RESOURCE_DIR / ("workspace.svg", "connections.svg", "settings.svg")[index])))
            item.setCheckable(True)
            self.nav.append(item)
            side.addWidget(item)
        side.addStretch()
        self.rail_state = label("Browser not connected", "RailState")
        side.addWidget(self.rail_state)
        side.addSpacing(9)
        side.addWidget(label(f"Version {__version__}"))
        root.addWidget(sidebar)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self._build_workspace()
        self._build_connections()
        self._build_settings()
        self.switch_page(0)

    def _page(self, title, subtitle):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 26)
        layout.setSpacing(18)
        layout.addWidget(label(title, "Title"))
        layout.addWidget(label(subtitle, "Subtitle"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.stack.addWidget(scroll)
        return layout

    def _build_workspace(self):
        layout = self._page("Workspace", "One tab. One session. Everything in view.")
        columns = QHBoxLayout()
        columns.setSpacing(24)
        workbench = QFrame()
        workbench.setObjectName("Workbench")
        work = QVBoxLayout(workbench)
        work.setContentsMargins(22, 22, 22, 18)
        work.setSpacing(14)
        top = QHBoxLayout()
        top.addWidget(label("Source tab", "Section"))
        top.addStretch()
        self.state_label = label("Stopped", "Status")
        top.addWidget(self.state_label)
        work.addLayout(top)
        self.targets = QComboBox()
        self.targets.setAccessibleName("Browser tab to process")
        self.targets.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.targets.setMinimumContentsLength(10)
        self.targets.addItem("Connect Chrome to choose a tab", None)
        self.targets.currentIndexChanged.connect(self._update_start)
        work.addWidget(self.targets)
        self.connection_hint = label("Checking the browser connection…", "Muted")
        work.addWidget(self.connection_hint)
        actions = QHBoxLayout()
        self.start_button = button("Start session", self.start_session, True)
        self.start_button.setEnabled(False)
        self.stop_button = button("Stop", self.stop_session)
        self.stop_button.setEnabled(False)
        actions.addWidget(self.start_button)
        actions.addWidget(self.stop_button)
        actions.addStretch()
        self.compact_setup_button = button("Open Chrome", self._next_setup_action, True)
        self.compact_setup_button.hide()
        actions.addWidget(self.compact_setup_button)
        work.addLayout(actions)
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFixedHeight(1)
        work.addWidget(divider)
        header = QHBoxLayout()
        self.results_title = label("Results", "Section")
        header.addWidget(self.results_title)
        header.addStretch()
        self.progress_label = label("Waiting to start", "Muted")
        self.progress_label.setWordWrap(False)
        self.progress_label.setMaximumWidth(240)
        header.addWidget(self.progress_label)
        work.addLayout(header)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        work.addWidget(self.progress)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("ResultBody")
        self.results = QVBoxLayout(body)
        self.results.setContentsMargins(0, 0, 0, 0)
        self.results.setSpacing(12)
        self.empty = QWidget()
        self.empty.setStyleSheet("background: white;")
        empty = QVBoxLayout(self.empty)
        empty.setContentsMargins(20, 28, 20, 28)
        empty.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(QIcon(str(RESOURCE_DIR / "tabs.svg")).pixmap(80, 64))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(icon)
        title = label("A clear view of every answer", "EmptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(title)
        description = label("Choose your source tab above. Questions and selected answers will appear here as the session runs.", "Muted")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(description)
        self.results.addStretch()
        self.results.addWidget(self.empty)
        self.results.addStretch()
        scroll.setWidget(body)
        work.addWidget(scroll, 1)
        self.log_toggle = QToolButton()
        self.log_toggle.setText("Show activity log")
        self.log_toggle.setCheckable(True)
        self.log_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.log_toggle.toggled.connect(self._toggle_log)
        work.addWidget(self.log_toggle)
        self.activity = QPlainTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setAccessibleName("Session event log")
        self.activity.setMaximumBlockCount(300)
        self.activity.setFixedHeight(110)
        self.activity.hide()
        work.addWidget(self.activity)
        columns.addWidget(workbench, 1)
        setup = QWidget()
        self.setup_panel = setup
        setup.setFixedWidth(218)
        info = QVBoxLayout(setup)
        info.setContentsMargins(0, 8, 0, 0)
        info.setSpacing(14)
        info.addWidget(label("Session setup", "Section"))
        self.setup_states = []
        for title in ("Connect Chrome", "Open an AI provider", "Choose a source tab"):
            info.addSpacing(4)
            info.addWidget(label(title, "StepTitle"))
            detail = label("Not ready", "StepDetail")
            self.setup_states.append(detail)
            info.addWidget(detail)
            line = QFrame()
            line.setObjectName("Divider")
            line.setFixedHeight(1)
            info.addWidget(line)
        self.next_button = button("Open Chrome", self._next_setup_action, True)
        info.addWidget(self.next_button)
        info.addStretch()
        info.addWidget(label("How a session works", "StepTitle"))
        info.addWidget(label("Reads questions from your tab, asks an AI provider, then selects matching answers and navigates pages. Review the result in Chrome.", "StepDetail"))
        columns.addWidget(setup)
        layout.addLayout(columns, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "setup_panel"):
            wide = self.width() >= 1040
            self.setup_panel.setVisible(wide)
            self.compact_setup_button.setVisible(not wide)

    def _toggle_log(self, checked):
        self.activity.setVisible(checked)
        self.log_toggle.setText("Hide activity log" if checked else "Show activity log")

    def _next_setup_action(self):
        if not self.connection["connected"]:
            self.open_browser()
        elif not (self.connection["providers"] or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")):
            self.switch_page(1)
        else:
            self.targets.setFocus()
            self.targets.showPopup()

    def _build_connections(self):
        layout = self._page("Connections", "A separate Chrome profile keeps this workspace apart from your everyday browsing.")
        frame, content = panel()
        content.addWidget(label("Browser connection", "Section"))
        self.browser_status = label("Not checked yet", "Muted")
        content.addWidget(self.browser_status)
        content.addWidget(label("Open the workspace browser, sign in to an AI provider, and open the page you want to work with."))
        row = QHBoxLayout()
        row.addWidget(button("Open workspace browser", self.open_browser, True))
        self.refresh_button = button("Refresh connection", self.refresh_connection)
        row.addWidget(self.refresh_button)
        row.addStretch()
        content.addLayout(row)
        layout.addWidget(frame)
        frame, content = panel()
        content.addWidget(label("AI providers", "Section"))
        content.addWidget(label("An open tab is detected automatically. Sign-in and availability are checked when a request runs.", "Muted"))
        self.provider_labels = {}
        for name, url in (("ChatGPT", "https://chatgpt.com"), ("Gemini", "https://gemini.google.com"), ("Claude", "https://claude.ai")):
            row = QHBoxLayout()
            row.addWidget(label(name))
            row.addStretch()
            state = label("No tab detected", "Muted")
            self.provider_labels[name] = state
            row.addWidget(state)
            open_button = button("Open", lambda checked=False, u=url: self._open_provider(u))
            open_button.setAccessibleName(f"Open {name} in workspace browser")
            row.addWidget(open_button)
            content.addLayout(row)
        layout.addWidget(frame)
        layout.addStretch()

    def _build_settings(self):
        layout = self._page("Settings", "Windows preferences, updates, and help when something goes wrong.")
        frame, content = panel()
        content.addWidget(label("Desktop behaviour", "Section"))
        self.close_to_tray = QCheckBox("Keep running in the system tray when I close the window")
        self.close_to_tray.setChecked(self.settings.value("close_to_tray", False, type=bool))
        self.close_to_tray.toggled.connect(lambda value: self.settings.setValue("close_to_tray", value))
        content.addWidget(self.close_to_tray)
        content.addWidget(label("With this enabled, closing the window keeps the session running. Quit HyperSolve stops it. Chrome stays open.", "Muted"))
        layout.addWidget(frame)
        frame, content = panel()
        content.addWidget(label("Application updates", "Section"))
        self.update_label = label(f"Installed version: {__version__}", "Muted")
        content.addWidget(self.update_label)
        row = QHBoxLayout()
        self.check_button = button("Check for updates", self.check_updates)
        self.install_button = button("Download and install", self.install_update, True)
        self.install_button.setEnabled(False)
        row.addWidget(self.check_button)
        row.addWidget(self.install_button)
        row.addStretch()
        content.addLayout(row)
        layout.addWidget(frame)
        frame, content = panel()
        content.addWidget(label("Diagnostics", "Section"))
        content.addWidget(label("Local logs record application errors. Review them before sharing; session details may appear in diagnostic output.", "Muted"))
        row = QHBoxLayout()
        row.addWidget(button("Open log folder", self.open_logs))
        row.addWidget(button("Report an issue", lambda: webbrowser.open("https://github.com/bipin-vishwakarma/HyperSolve/issues")))
        row.addStretch()
        content.addLayout(row)
        layout.addWidget(frame)
        layout.addStretch()

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("HyperSolve — Stopped")
        menu = QMenu(self)
        menu.addAction("Open HyperSolve", self.restore_window)
        self.tray_stop = menu.addAction("Stop session", self.stop_session)
        self.tray_stop.setEnabled(False)
        menu.addSeparator()
        menu.addAction("Quit HyperSolve", self.request_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.restore_window() if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick) else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, item in enumerate(self.nav):
            item.setChecked(i == index)

    def _job(self, function, callback, error_callback=None):
        worker = FunctionWorker(function, self)
        self.jobs.append(worker)
        worker.result.connect(callback)
        worker.failed.connect(error_callback or self.show_error)
        worker.finished.connect(lambda: self._job_finished(worker))
        worker.start()

    def _job_finished(self, worker):
        self.jobs.remove(worker)
        worker.deleteLater()
        self._finish_quit_if_ready()

    def refresh_connection(self):
        if self.scanning or self._quitting:
            return
        self.scanning = True
        self.refresh_button.setEnabled(False)
        self._job(lambda: inspect_connection(self.cdp_url), self._connection_result, self._scan_failed)

    def _scan_failed(self, message):
        self._connection_result({"connected": False, "providers": [], "targets": [], "error": message})

    def _connection_result(self, data):
        self.scanning = False
        self.refresh_button.setEnabled(True)
        self.connection = data
        connected = data["connected"]
        self.rail_state.setText("Chrome connected" if connected else "Browser not connected")
        self.browser_status.setText("Connected to Chrome on this computer" if connected else "Chrome is not connected. Open the workspace browser, then refresh.")
        self.connection_hint.setText(("Browser connected  ·  " + (", ".join(data["providers"]) + " tab detected" if data["providers"] else "Open an AI provider tab to continue")) if connected else "Connect the workspace browser to get started.")
        previous = self.targets.currentData()
        self.targets.blockSignals(True)
        self.targets.clear()
        for target in data["targets"]:
            self.targets.addItem(target.get("title") or target["url"], {"url": target["url"], "id": target.get("id")})
            self.targets.setItemData(self.targets.count() - 1, target["url"], Qt.ItemDataRole.ToolTipRole)
        if not data["targets"]:
            self.targets.addItem("Open a page in workspace Chrome" if connected else "Connect Chrome to choose a tab", None)
        index = self.targets.findData(previous)
        if index >= 0:
            self.targets.setCurrentIndex(index)
        self.targets.blockSignals(False)
        for name, status in self.provider_labels.items():
            status.setText("Tab detected" if name in data["providers"] else "No tab detected")
        self._update_start()

    def _update_start(self):
        has_ai = bool(self.connection["providers"] or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY"))
        connected = self.connection["connected"]
        target = self.targets.currentData()
        ready = not self._quitting and self.engine is None and connected and has_ai and bool(target)
        self.start_button.setEnabled(ready)
        self.targets.setEnabled(connected and self.engine is None)
        if hasattr(self, "setup_states"):
            self.setup_states[0].setText("Connected on this computer" if connected else "A separate profile for this workspace")
            self.setup_states[1].setText(", ".join(self.connection["providers"]) + " tab detected" if self.connection["providers"] else ("API key configured" if has_ai else "ChatGPT, Gemini, or Claude"))
            self.setup_states[2].setText("Tab selected — ready to start" if target else "Open the page you want to work with")
            self.next_button.setText("Open Chrome" if not connected else ("Connect AI" if not has_ai else "Choose tab"))
            self.next_button.setEnabled(self.engine is None and not self._quitting)
            self.compact_setup_button.setText(self.next_button.text())
            self.compact_setup_button.setEnabled(self.next_button.isEnabled())

    def open_browser(self):
        try:
            launch_chrome()
            self.browser_status.setText("Browser requested. Refresh after Chrome opens.")
            QTimer.singleShot(1800, self.refresh_connection)
        except OSError as exc:
            self.show_error(str(exc))

    def _open_provider(self, url):
        try:
            launch_chrome(url)
            QTimer.singleShot(1800, self.refresh_connection)
        except OSError as exc:
            self.show_error(str(exc))

    def start_session(self):
        if self.engine is not None or not self.start_button.isEnabled():
            return
        self.empty.hide()
        for frame in self.question_rows.values():
            self.results.removeWidget(frame)
            frame.deleteLater()
        self.question_rows.clear()
        self.activity.clear()
        self.progress.setValue(0)
        self.progress_label.setText("Starting…")
        target = self.targets.currentData()
        self.engine = EngineWorker(target["url"], self, target_id=target["id"])
        self.engine.event.connect(self._engine_event)
        self.engine.failed.connect(self.show_error)
        self.engine.finished.connect(self._engine_finished)
        self.start_button.setEnabled(False)
        self.targets.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.tray_stop.setEnabled(True)
        self._set_status("Running")
        self.engine.start()

    def stop_session(self):
        if self.engine:
            self._set_status("Stopping…")
            self.stop_button.setEnabled(False)
            self.tray_stop.setEnabled(False)
            self.engine.stop()

    def _engine_finished(self):
        self.engine.deleteLater()
        self.engine = None
        self.targets.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.tray_stop.setEnabled(False)
        self._set_status("Stopped")
        self._append_activity("Session stopped. Chrome has been left open.")
        self._update_start()
        self._finish_quit_if_ready()

    def _engine_event(self, kind, payload):
        if kind == "status":
            self._append_activity(payload)
            self.progress_label.setText(payload)
            self.progress_label.setToolTip(payload)
        elif kind == "error":
            self.show_error(payload)
        elif kind == "questions":
            for question in payload:
                frame, content = panel()
                content.addWidget(label(f"Question {question['id']}", "Section"))
                content.addWidget(label(question["text"]))
                answer = label("Waiting for a response", "Muted")
                content.addWidget(answer)
                frame.answer_label = answer
                self.question_rows[question["id"]] = frame
                self.results.insertWidget(self.results.count() - 1, frame)
        elif kind == "answer":
            frame = self.question_rows.get(payload["id"])
            if frame:
                frame.answer_label.setText("Selected: " + payload["answer"])
            self.progress.setValue(round(payload["done"] / max(payload["total"], 1) * 100))
            self.progress_label.setText(f"{payload['done']} of {payload['total']} selected")
        elif kind == "complete":
            self.progress.setValue(round(payload["done"] / max(payload["total"], 1) * 100))
            self._append_activity(f"Session finished: {payload['done']}/{payload['total']} selected via {payload['brain']}.")
            self.stop_session()

    def _append_activity(self, message):
        self.activity.appendPlainText(f"{datetime.now():%H:%M:%S}  {message}")

    def _set_status(self, text):
        self.state_label.setText(text)
        self.tray.setToolTip(f"HyperSolve — {text}")

    def show_error(self, message):
        self._append_activity("Error: " + message)
        self.progress_label.setText("A problem occurred — see activity below")
        self.empty.hide()
        self.log_toggle.setChecked(True)
        self.switch_page(0)

    def check_updates(self):
        self.check_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.latest_update = None
        self.update_label.setText("Checking for updates…")
        self._job(OTAUpdateManager.check_for_updates, self._update_result, self._update_failed)

    def _update_result(self, info):
        self.check_button.setEnabled(True)
        self.latest_update = info
        self.update_label.setText(f"Version {info.version} is available." if info else f"You’re up to date. Installed version: {__version__}.")
        self.install_button.setEnabled(bool(info))

    def _update_failed(self, message):
        self.check_button.setEnabled(True)
        self.install_button.setEnabled(bool(self.latest_update))
        self.update_label.setText("Update failed: " + message)

    def install_update(self):
        if not self.latest_update or self.engine:
            self.update_label.setText("Stop the current session before installing an update.")
            return
        self.install_button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.update_label.setText("Downloading and verifying installer…")
        self._job(lambda: OTAUpdateManager.download_and_install_update(self.latest_update, silent=False), self._install_result, self._update_failed)

    def _install_result(self, success):
        self.check_button.setEnabled(True)
        self.install_button.setEnabled(not success)
        self.update_label.setText("Installer opened. Follow Windows Setup to finish." if success else "The installer could not be verified or launched. Try again or use the release page.")

    def open_logs(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_DIR)))

    def restore_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self._quitting:
            event.setAccepted(self.engine is None and not self.jobs)
            return
        self.settings.setValue("geometry", self.saveGeometry())
        if self.close_to_tray.isChecked() and self.tray.isVisible() and not self._quitting:
            self.hide()
            event.ignore()
        else:
            event.ignore()
            self.request_quit()

    def request_quit(self):
        if self._quitting:
            return
        self._quitting = True
        self.timer.stop()
        self.settings.setValue("geometry", self.saveGeometry())
        self.start_button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.stop_session()
        self._finish_quit_if_ready()

    def _finish_quit_if_ready(self):
        if self._quitting and self.engine is None and not self.jobs:
            self.tray.hide()
            QTimer.singleShot(0, QApplication.instance().quit)


def run_dashboard(start_in_tray=False):
    configure_logging()
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName("HyperSolve")
    app.setOrganizationName("HyperSolve")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    from PyQt6.QtGui import QPalette, QColor
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f3f4f8"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#24293b"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#24293b"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#24293b"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3759dc"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(RESOURCE_DIR / "hypersolve.ico")))
    # A second launch asks the existing instance to restore its window.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(DATA_DIR / "desktop.lock"))
    if not lock.tryLock(100):
        socket = QLocalSocket()
        socket.connectToServer(APP_ID)
        socket.waitForConnected(1500)
        return
    QLocalServer.removeServer(APP_ID)
    server = QLocalServer()
    server.listen(APP_ID)
    window = HyperSolveDashboard()
    def restore():
        socket = server.nextPendingConnection()
        if socket:
            socket.disconnectFromServer()
            socket.deleteLater()
        window.restore_window()
    server.newConnection.connect(restore)
    if not start_in_tray or not window.tray.isVisible():
        window.show()
    exit_code = app.exec()
    server.close()
    lock.unlock()
    return exit_code


if __name__ == "__main__":
    run_dashboard()
