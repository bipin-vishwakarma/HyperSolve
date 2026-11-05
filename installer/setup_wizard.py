"""Compatibility launcher for the real standalone Windows installer."""
from pathlib import Path
import subprocess
import sys


def run_setup():
    root = Path(__file__).resolve().parents[1]
    installers = sorted((root / "dist_installer").glob("HyperSolve-Setup-v*.exe"), key=lambda p: p.stat().st_mtime)
    if not installers:
        print("No built installer found. Run scripts/build_windows.ps1 first.")
        return 1
    subprocess.Popen([str(installers[-1])], shell=False)
    return 0


if __name__ == "__main__":
    sys.exit(run_setup())
