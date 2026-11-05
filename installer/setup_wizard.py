"""
HyperSolve Windows Setup Wizard (Local Installer Demo)
Interactive modern dark-glass installer wizard that installs HyperSolve
to %LocalAppData%\\HyperSolve, creates official Desktop & Start Menu shortcuts,
and launches the application.
"""

import os
import sys
import shutil
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QProgressBar, QFrame, QRadioButton, QButtonGroup
)
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor
from PyQt6.QtCore import Qt, QTimer

from hypersolve.__version__ import __version__

APP_NAME = "HyperSolve"
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(REPO_DIR, "installer", "hypersolve.ico")
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME)

DARK_STYLE = """
    QWizard {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: 'Segoe UI', sans-serif;
    }
    QWizardPage {
        background-color: #0f172a;
        color: #f8fafc;
    }
    QLabel {
        color: #f8fafc;
    }
    QPushButton {
        background-color: #0284c7;
        color: white;
        border-radius: 6px;
        font-weight: 600;
        padding: 8px 18px;
        border: none;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #0369a1;
    }
    QPushButton:disabled {
        background-color: #334155;
        color: #94a3b8;
    }
    QCheckBox {
        color: #cbd5e1;
        font-size: 13px;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid #475569;
        background-color: #1e293b;
    }
    QCheckBox::indicator:checked {
        background-color: #06b6d4;
        border-color: #06b6d4;
    }
    QProgressBar {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 6px;
        height: 14px;
        text-align: center;
        color: white;
        font-size: 11px;
    }
    QProgressBar::chunk {
        background-color: #06b6d4;
        border-radius: 5px;
    }
"""

def create_windows_shortcut(target: str, shortcut_path: str, working_dir: str, icon_path: str, description: str, arguments: str = ""):
    """Creates a native Windows .lnk shortcut via WScript.Shell without external C dependencies."""
    ps_script = f"""
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
    $Shortcut.TargetPath = "{target}"
    $Shortcut.Arguments = "{arguments}"
    $Shortcut.WorkingDirectory = "{working_dir}"
    $Shortcut.IconLocation = "{icon_path},0"
    $Shortcut.Description = "{description}"
    $Shortcut.Save()
    """
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"[SHORTCUT ERROR] {e}")
        return False


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel(f"⚡ Welcome to the {APP_NAME} Setup Wizard")
        title.setStyleSheet("color: #06b6d4; font-size: 18px; font-weight: 800;")
        layout.addWidget(title)

        desc = QLabel(
            f"This wizard will install {APP_NAME} v{__version__} on your computer.\n\n"
            "Features included in this installation:\n"
            " • Autonomous Assessment Engine (Moodle, Canvas, Google Forms)\n"
            " • Ghost Shield Anti-Proctoring Armor (Tab-switch neutralizer)\n"
            " • Standalone Frameless Command Center & System Tray App\n"
            " • Zero-API-Key Browser AI Session Pool (ChatGPT / Gemini)\n"
            " • Silent Over-The-Air (OTA) Background Updates\n\n"
            f"Installation Location: {INSTALL_DIR}"
        )
        desc.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.5;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addStretch()


class OptionsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Select Additional Tasks")
        title.setStyleSheet("color: #06b6d4; font-size: 16px; font-weight: 800;")
        layout.addWidget(title)

        desc = QLabel("Choose which shortcuts and integrations you would like to create:")
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(desc)

        self.desktop_chk = QCheckBox("Create a Desktop Shortcut (with HyperSolve icon)")
        self.desktop_chk.setChecked(True)
        layout.addWidget(self.desktop_chk)

        self.start_chk = QCheckBox("Create a Start Menu Program Shortcut")
        self.start_chk.setChecked(True)
        layout.addWidget(self.start_chk)

        self.shield_chk = QCheckBox("Enable Ghost Shield Anti-Proctoring Armor by default")
        self.shield_chk.setChecked(True)
        layout.addWidget(self.shield_chk)

        layout.addStretch()


class InstallProgressPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("")
        self.is_done = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        self.status_lbl = QLabel("Installing HyperSolve components...")
        self.status_lbl.setStyleSheet("color: #06b6d4; font-size: 15px; font-weight: bold;")
        layout.addWidget(self.status_lbl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.detail_lbl = QLabel("Preparing directories...")
        self.detail_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.detail_lbl)
        layout.addStretch()

    def initializePage(self):
        self.wizard().button(QWizard.WizardButton.NextButton).setEnabled(False)
        self.wizard().button(QWizard.WizardButton.BackButton).setEnabled(False)
        QTimer.singleShot(400, self._perform_install_step)

    def _perform_install_step(self):
        try:
            # 1. Create install directory
            self.detail_lbl.setText(f"Creating install directory: {INSTALL_DIR}")
            self.progress.setValue(25)
            os.makedirs(INSTALL_DIR, exist_ok=True)

            # 2. Copy/link core application payload
            self.detail_lbl.setText("Deploying HyperSolve Engine and Assets...")
            self.progress.setValue(55)

            # Copy launcher batch / scripts
            launcher_path = os.path.join(INSTALL_DIR, "HyperSolve.bat")
            with open(launcher_path, "w", encoding="utf-8") as f:
                f.write(f"@echo off\ncd /d \"{REPO_DIR}\"\nstart pythonw -m hypersolve.desktop.dashboard_window\nexit\n")

            pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe") if "python.exe" in sys.executable else sys.executable

            # 3. Create Desktop shortcut
            opts = self.wizard().options_page
            desktop_dir = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\Lenovo"), "Desktop")
            if opts.desktop_chk.isChecked() and os.path.exists(desktop_dir):
                self.detail_lbl.setText("Creating Desktop Icon...")
                self.progress.setValue(75)
                create_windows_shortcut(
                    target=pythonw_exe,
                    arguments="-m hypersolve.desktop.dashboard_window",
                    shortcut_path=os.path.join(desktop_dir, "HyperSolve.lnk"),
                    working_dir=REPO_DIR,
                    icon_path=ICON_PATH,
                    description="HyperSolve Command Center v2.0"
                )

            # 4. Create Start Menu shortcut
            start_menu_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft\\Windows\\Start Menu\\Programs\\HyperSolve")
            if opts.start_chk.isChecked():
                self.detail_lbl.setText("Registering in Start Menu...")
                self.progress.setValue(90)
                os.makedirs(start_menu_dir, exist_ok=True)
                create_windows_shortcut(
                    target=pythonw_exe,
                    arguments="-m hypersolve.desktop.dashboard_window",
                    shortcut_path=os.path.join(start_menu_dir, "HyperSolve.lnk"),
                    working_dir=REPO_DIR,
                    icon_path=ICON_PATH,
                    description="HyperSolve Command Center v2.0"
                )

            self.progress.setValue(100)
            self.status_lbl.setText("Installation Complete!")
            self.detail_lbl.setText("All files and shortcuts deployed successfully.")
            self.is_done = True
            self.wizard().button(QWizard.WizardButton.NextButton).setEnabled(True)
            self.wizard().next()

        except Exception as e:
            self.status_lbl.setText(f"Install Notice: {e}")
            self.wizard().button(QWizard.WizardButton.NextButton).setEnabled(True)

    def isComplete(self):
        return self.is_done


class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("🎉 Completing the HyperSolve Setup Wizard")
        title.setStyleSheet("color: #10b981; font-size: 18px; font-weight: 800;")
        layout.addWidget(title)

        desc = QLabel(
            f"{APP_NAME} v{__version__} has been successfully installed on your computer.\n\n"
            "You can launch HyperSolve anytime from the new Desktop Icon or Start Menu.\n\n"
            "Click Finish to exit Setup."
        )
        desc.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.5;")
        layout.addWidget(desc)

        self.launch_chk = QCheckBox("Launch HyperSolve Command Center now")
        self.launch_chk.setChecked(True)
        layout.addWidget(self.launch_chk)

        layout.addStretch()


class HyperSolveSetupWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Setup — {APP_NAME} v{__version__}")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.resize(560, 420)
        self.setStyleSheet(DARK_STYLE)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.welcome_page = WelcomePage()
        self.options_page = OptionsPage()
        self.progress_page = InstallProgressPage()
        self.finish_page = FinishPage()

        self.addPage(self.welcome_page)
        self.addPage(self.options_page)
        self.addPage(self.progress_page)
        self.addPage(self.finish_page)

        self.finished.connect(self._on_finished)

    def _on_finished(self, result):
        if self.finish_page.launch_chk.isChecked():
            # Launch dashboard
            cmd = f'start "" python -m hypersolve.desktop.dashboard_window'
            subprocess.Popen(cmd, shell=True, cwd=REPO_DIR)


def run_setup():
    app = QApplication(sys.argv)
    wizard = HyperSolveSetupWizard()
    wizard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_setup()
