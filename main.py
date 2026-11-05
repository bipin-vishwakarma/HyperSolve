import asyncio
import sys
from hypersolve.__version__ import __version__
from hypersolve.core.daemon import HyperSolveDaemon
from hypersolve.updater.engine import OTAUpdateManager

def main():
    if sys.platform == "win32" and sys.version_info < (3, 14):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

    print(f"\n⚡ Starting HyperSolve Engine v{__version__} (Zero-API-Key Architecture) ⚡")

    # Non-blocking Over-The-Air Update Check
    OTAUpdateManager.check_update_async(
        on_update_found=lambda u: print(f"[OTA UPDATE AVAILABLE] New version v{u.version} is ready for installation.")
    )

    daemon = HyperSolveDaemon(cdp_url="http://127.0.0.1:9222")
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        print("\n[HYPERSOLVE] Gracefully shut down by user.")

if __name__ == "__main__":
    main()
