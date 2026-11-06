"""Default source and packaged entry point."""
import sys


def main():
    if "--engine" in sys.argv:
        import asyncio
        from hypersolve.core.daemon import HyperSolveDaemon
        try:
            asyncio.run(HyperSolveDaemon().start())
        except KeyboardInterrupt:
            pass
    else:
        from hypersolve.desktop.dashboard_window import run_dashboard
        run_dashboard(start_in_tray="--tray" in sys.argv)


if __name__ == "__main__":
    main()
