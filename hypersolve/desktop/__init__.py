"""HyperSolve desktop workspace, tray entry point, and legacy screenshot HUD."""

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
    if name == "HyperSolveTrayApp":
        from .dashboard_window import HyperSolveDashboard
        return HyperSolveDashboard
    if name == "run_tray":
        from .tray import run_tray
        return run_tray
    if name in ("HyperSolveDashboard", "run_dashboard"):
        from .dashboard_window import HyperSolveDashboard, run_dashboard
        return HyperSolveDashboard if name == "HyperSolveDashboard" else run_dashboard
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
