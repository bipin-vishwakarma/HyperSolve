"""Windows integration shared by source and installed builds."""
import logging
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse

import requests

APP_ID = "HyperSolve.Desktop"
RESOURCE_DIR = Path(__file__).resolve().parents[1] / "assets"
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "HyperSolve"
PROFILE_DIR = DATA_DIR / "Browser"
LOG_DIR = DATA_DIR / "Logs"
CDP_URL = "http://127.0.0.1:9222"
PROVIDERS = {"chatgpt.com": "ChatGPT", "chat.openai.com": "ChatGPT",
             "gemini.google.com": "Gemini", "claude.ai": "Claude"}


def configure_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler(LOG_DIR / "desktop.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")


def provider_for_url(url):
    return PROVIDERS.get((urlparse(url).hostname or "").lower())


def inspect_connection(cdp_url=CDP_URL):
    """Read tab metadata only; an open provider tab does not prove sign-in."""
    try:
        response = requests.get(cdp_url + "/json/list", timeout=1.5)
        response.raise_for_status()
        tabs = [t for t in response.json() if t.get("type") == "page"]
        providers = sorted({provider_for_url(t.get("url", "")) for t in tabs} - {None})
        targets = [t for t in tabs if urlparse(t.get("url", "")).scheme in ("http", "https")
                   and not provider_for_url(t.get("url", ""))]
        return {"connected": True, "providers": providers, "targets": targets, "tabs": tabs, "error": ""}
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        return {"connected": False, "providers": [], "targets": [], "error": str(exc)}


def find_chrome():
    candidates = [Path(os.environ.get(root, "")) / "Google/Chrome/Application/chrome.exe"
                  for root in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
    if sys.platform == "win32":
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                    candidates.insert(0, Path(winreg.QueryValue(key, None)))
            except OSError:
                pass
    return next((p for p in candidates if p.is_file()), None)


def launch_chrome(url="https://chatgpt.com", *, urls=None):
    chrome = find_chrome()
    if not chrome:
        raise FileNotFoundError("Google Chrome was not found. Install Chrome, then try again.")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    legacy_profile = Path(__file__).resolve().parents[2] / "chrome_profile"
    profile = legacy_profile if (legacy_profile / "Local State").is_file() else PROFILE_DIR
    return subprocess.Popen([str(chrome), "--remote-debugging-port=9222",
                             "--remote-debugging-address=127.0.0.1",
                             f"--user-data-dir={profile}", "--no-first-run", *(urls if urls is not None else [url])])
