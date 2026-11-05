"""Compatibility entry point; the desktop app owns the tray lifecycle."""

def run_tray():
    from .dashboard_window import run_dashboard
    run_dashboard(start_in_tray=True)


if __name__ == "__main__":
    run_tray()
