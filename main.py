import asyncio
import sys
from hypersolve.core.daemon import HyperSolveDaemon

def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    daemon = HyperSolveDaemon(cdp_url="http://127.0.0.1:9222")
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        print("\n[HYPERSOLVE] Gracefully shut down by user.")

if __name__ == "__main__":
    main()
