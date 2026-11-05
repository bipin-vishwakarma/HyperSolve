"""
HyperSolve Windows System Tray Application
Provides a native notification area icon, quick controls for Ghost Shield,
AI Brain monitor, Human Mimicry target score selector, OTA updates, and panic hotkey.
"""

import sys
import os
import asyncio
import threading
import subprocess
from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont, QPen, QAction, QActionGroup
)
from PyQt6.QtCore import (
    QObject, pyqtSignal, pyqtSlot, QTimer
)

from hypersolve.__version__ import __version__
from hypersolve.stealth.ghost_shield import GhostShield
from hypersolve.updater.engine import OTAUpdateManager, UpdateInfo
from hypersolve.core.daemon import HyperSolveDaemon

class TrayEventBridge(QObject):
    """Bridge for cross-thread communication between Asyncio daemon and Qt GUI."""
    status_changed = pyqtSignal(str)
    target_attached = pyqtSignal(str)
    assessment_solved = pyqtSignal(int, int, str)
    ota_available = pyqtSignal(object)

class HyperSolveTrayApp:
    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        self.cdp_url = cdp_url
        self.bridge = TrayEventBridge()
        self.daemon: Optional[HyperSolveDaemon] = None
        self.daemon_thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        # State
        self.shield_enabled = True
        self.target_score = 100 # 100%, 95%, 90%, 85%
        self.current_brain = "Scanning..."
        self.latest_update: Optional[UpdateInfo] = None

        self._init_ui()
        self._wire_signals()
        self._start_background_daemon()
        self._check_ota_on_boot()

    def _create_tray_pixmap(self, active: bool = True) -> QPixmap:
        """Dynamically generates a high-DPI cyberpunk lightning badge icon."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background rounded dark plate
        painter.setBrush(QColor(15, 23, 42)) # Slate 900
        painter.setPen(QPen(QColor(6, 182, 212) if active else QColor(100, 116, 139), 3)) # Cyan 500 or Slate
        painter.drawRoundedRect(4, 4, 56, 56, 16, 16)

        # Draw Neon Lightning Bolt
        painter.setPen(QPen(QColor(6, 182, 212), 2))
        painter.setBrush(QColor(34, 211, 238)) # Cyan 400
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint
        points = [
            QPoint(34, 10),
            QPoint(18, 32),
            QPoint(30, 32),
            QPoint(26, 54),
            QPoint(46, 26),
            QPoint(34, 26),
        ]
        painter.drawPolygon(QPolygon(points))

        # Status Dot
        dot_color = QColor(34, 197, 94) if active else QColor(239, 68, 68) # Green or Red
        painter.setBrush(dot_color)
        painter.setPen(QPen(QColor(15, 23, 42), 2))
        painter.drawEllipse(44, 44, 14, 14)

        painter.end()
        return pixmap

    def _init_ui(self):
        self.tray_icon = QSystemTrayIcon()
        self.icon_active = QIcon(self._create_tray_pixmap(active=True))
        self.icon_inactive = QIcon(self._create_tray_pixmap(active=False))
        self.tray_icon.setIcon(self.icon_active)
        self.tray_icon.setToolTip(f"HyperSolve v{__version__} - Standby")

        # Context Menu
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #06b6d4;
                color: #0f172a;
                font-weight: bold;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 4px 8px;
            }
        """)

        # Title
        self.title_action = QAction(f"⚡ HyperSolve v{__version__}", self.menu)
        self.title_action.setEnabled(False)
        self.menu.addAction(self.title_action)

        # Status item
        self.status_action = QAction("● Standing by for active assessments...", self.menu)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()

        # Ghost Shield Toggle
        self.shield_action = QAction("🛡️ Ghost Shield Anti-Proctoring", self.menu)
        self.shield_action.setCheckable(True)
        self.shield_action.setChecked(True)
        self.shield_action.toggled.connect(self._on_toggle_shield)
        self.menu.addAction(self.shield_action)

        # Human Mimicry Target Score Submenu
        self.score_menu = QMenu("🎯 Target Score (Mimicry)", self.menu)
        self.score_group = QActionGroup(self.score_menu)
        self.score_group.setExclusive(True)

        scores = [
            ("100% Perfect (All Correct)", 100),
            ("95% Top Distinction (A+)", 95),
            ("90% Natural Top Grade (A)", 90),
            ("85% Realistic Pass (B+)", 85),
        ]
        for label, val in scores:
            act = QAction(label, self.score_menu)
            act.setCheckable(True)
            if val == 100:
                act.setChecked(True)
            act.setData(val)
            act.triggered.connect(lambda chk, v=val: self._on_set_target_score(v))
            self.score_group.addAction(act)
            self.score_menu.addAction(act)
        self.menu.addMenu(self.score_menu)
        self.menu.addSeparator()

        # Launch Browser / AI Sessions
        self.open_chrome_action = QAction("🌐 Launch Assessment Chrome (Port 9222)", self.menu)
        self.open_chrome_action.triggered.connect(self._launch_chrome)
        self.menu.addAction(self.open_chrome_action)

        self.open_chatgpt_action = QAction("🧠 Open ChatGPT Tab", self.menu)
        self.open_chatgpt_action.triggered.connect(lambda: self._open_url("https://chatgpt.com"))
        self.menu.addAction(self.open_chatgpt_action)
        self.menu.addSeparator()

        # OTA Update Checker
        self.ota_action = QAction("🔄 Check for Updates (OTA)", self.menu)
        self.ota_action.triggered.connect(self._manual_check_ota)
        self.menu.addAction(self.ota_action)

        # Panic Hotkey Reminder
        self.panic_action = QAction("👻 Emergency Panic (Ctrl + Shift + X)", self.menu)
        self.panic_action.setEnabled(False)
        self.menu.addAction(self.panic_action)
        self.menu.addSeparator()

        # Exit
        self.quit_action = QAction("❌ Exit HyperSolve", self.menu)
        self.quit_action.triggered.connect(self._on_quit)
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def _wire_signals(self):
        self.bridge.status_changed.connect(self._update_status)
        self.bridge.target_attached.connect(self._show_attached_notification)
        self.bridge.assessment_solved.connect(self._show_solved_notification)
        self.bridge.ota_available.connect(self._notify_ota_available)

    def _update_status(self, text: str):
        self.status_action.setText(f"● {text}")
        self.tray_icon.setToolTip(f"HyperSolve v{__version__} - {text}")

    def _show_attached_notification(self, url: str):
        clean_url = url[:45] + "..." if len(url) > 45 else url
        self.tray_icon.showMessage(
            "HyperSolve — Assessment Attached",
            f"Scanning questions on {clean_url}",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
        self._update_status("Solving Assessment...")

    def _show_solved_notification(self, injected: int, total: int, brain: str):
        self.tray_icon.showMessage(
            "HyperSolve — Assessment Complete 🎉",
            f"Successfully injected & verified {injected}/{total} answers via {brain}.",
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )
        self._update_status("Standby (Assessment Complete)")

    def _notify_ota_available(self, update: UpdateInfo):
        self.latest_update = update
        self.ota_action.setText(f"🚀 Install Update v{update.version}!")
        self.tray_icon.showMessage(
            "HyperSolve Update Available",
            f"Version {update.version} is ready. Click tray menu to install.",
            QSystemTrayIcon.MessageIcon.Information,
            6000
        )

    def _on_toggle_shield(self, checked: bool):
        self.shield_enabled = checked
        GhostShield.is_enabled = checked
        state = "ARMED" if checked else "DISARMED"
        self.tray_icon.setIcon(self.icon_active if checked else self.icon_inactive)
        self.tray_icon.showMessage(
            "Ghost Shield",
            f"Anti-Proctoring Armor is now {state}.",
            QSystemTrayIcon.MessageIcon.Warning if not checked else QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _on_set_target_score(self, score: int):
        self.target_score = score
        if self.daemon:
            self.daemon.target_accuracy = score / 100.0

    def _launch_chrome(self):
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        bat_path = os.path.join(script_dir, "run_hypersolve.bat")
        # Direct Chrome launch with CDP
        profile_dir = os.path.join(script_dir, "chrome_profile")
        cmd = f'start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="{profile_dir}" "https://chatgpt.com"'
        subprocess.Popen(cmd, shell=True)

    def _open_url(self, url: str):
        import webbrowser
        webbrowser.open(url)

    def _check_ota_on_boot(self):
        OTAUpdateManager.check_update_async(
            on_update_found=lambda u: self.bridge.ota_available.emit(u)
        )

    def _manual_check_ota(self):
        if self.latest_update:
            # Install now
            self.tray_icon.showMessage("HyperSolve OTA", "Downloading and applying update...", QSystemTrayIcon.MessageIcon.Information, 3000)
            threading.Thread(
                target=lambda: OTAUpdateManager.download_and_install_update(self.latest_update, silent=True),
                daemon=True
            ).start()
        else:
            self.tray_icon.showMessage("HyperSolve OTA", "Checking GitHub for updates...", QSystemTrayIcon.MessageIcon.Information, 2000)
            def check():
                u = OTAUpdateManager.check_for_updates()
                if u:
                    self.bridge.ota_available.emit(u)
                else:
                    self.tray_icon.showMessage("HyperSolve OTA", "You are running the latest version!", QSystemTrayIcon.MessageIcon.Information, 2500)
            threading.Thread(target=check, daemon=True).start()

    def _start_background_daemon(self):
        def runner():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.daemon = HyperSolveDaemon(
                cdp_url=self.cdp_url,
                on_target_attached=lambda url: self.bridge.target_attached.emit(url),
                on_solved=lambda inj, tot, brain: self.bridge.assessment_solved.emit(inj, tot, brain),
                on_status_change=lambda txt: self.bridge.status_changed.emit(txt)
            )
            try:
                self.loop.run_until_complete(self.daemon.start())
            except Exception:
                pass

        self.daemon_thread = threading.Thread(target=runner, daemon=True, name="HyperSolve-Daemon-Worker")
        self.daemon_thread.start()

    def _on_quit(self):
        if self.daemon and self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        QApplication.quit()
        sys.exit(0)

def run_tray():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray = HyperSolveTrayApp()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_tray()
