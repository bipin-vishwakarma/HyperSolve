"""HyperSolve Desktop: Native Windows Transparent Frosted-Glass HUD, System Tray, and Command Center."""

__all__ = [
    "DesktopOverlayWindow",
    "GlobalHotkeyListener",
    "HyperSolveTrayApp",
    "run_tray",
    "HyperSolveDashboard",
    "run_dashboard",
]

def __getattr__(name):
    if name == "DesktopOverlayWindow":
        from .overlay_window import DesktopOverlayWindow
        return DesktopOverlayWindow
    if name == "GlobalHotkeyListener":
        from .hotkeys import GlobalHotkeyListener
        return GlobalHotkeyListener
    if name in ("HyperSolveTrayApp", "run_tray"):
        from .tray import HyperSolveTrayApp, run_tray
        return HyperSolveTrayApp if name == "HyperSolveTrayApp" else run_tray
    if name in ("HyperSolveDashboard", "run_dashboard"):
        from .dashboard_window import HyperSolveDashboard, run_dashboard
        return HyperSolveDashboard if name == "HyperSolveDashboard" else run_dashboard
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
