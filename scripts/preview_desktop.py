"""Offline desktop captures; this script never connects to a real browser."""
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

os.environ.pop("QT_QPA_PLATFORM", None)
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont
from hypersolve.desktop.dashboard_window import HyperSolveDashboard

app = QApplication([])
app.setStyle("Fusion")
app.setFont(QFont("Segoe UI", 10))
output = root / "scratch/review"
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as settings_dir:
    settings = QSettings(str(Path(settings_dir) / "preview.ini"), QSettings.Format.IniFormat)
    with patch("hypersolve.desktop.dashboard_window.QSystemTrayIcon.isSystemTrayAvailable", return_value=False), patch("hypersolve.desktop.dashboard_window.QSettings", return_value=settings):
        window = HyperSolveDashboard(auto_scan=False)
    window._connection_result({"connected": False, "providers": [], "targets": []})
    window.show()
    for index, name in enumerate(("workspace-final", "connections-final", "settings-final")):
        window.switch_page(index)
        app.processEvents()
        window.grab().save(str(output / (name + ".png")))
    window.resize(860, 620)
    for index, name in enumerate(("workspace-small-final", "connections-small-final")):
        window.switch_page(index)
        app.processEvents()
        window.grab().save(str(output / (name + ".png")))
    window.switch_page(2)
    window.close_to_tray.setChecked(True)
    window.resize(860, 620)
    app.processEvents()
    window.grab().save(str(output / "settings-small-final.png"))
    window.tray.hide()
