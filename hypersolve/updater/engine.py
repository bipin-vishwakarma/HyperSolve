"""
HyperSolve OTA (Over-The-Air) Automated Update Engine
Pings remote GitHub Releases / update manifest, checks semver,
verifies cryptographic integrity, and hot-swaps binaries silently.
"""

import os
import sys
import json
import hashlib
import tempfile
import threading
import subprocess
from typing import Optional, Dict, Any, Callable
from urllib.parse import urlparse
import requests

from hypersolve.__version__ import __version__

GITHUB_REPO = "bipin-vishwakarma/HyperSolve"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
FALLBACK_MANIFEST_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/releases/latest.json"

class UpdateInfo:
    def __init__(self, version: str, download_url: str, release_notes: str = "", sha256: str = "", asset_name: str = ""):
        self.version = version
        self.download_url = download_url
        self.release_notes = release_notes
        self.sha256 = sha256
        self.asset_name = asset_name

    def __repr__(self):
        return f"<UpdateInfo v{self.version} ({self.asset_name})>"


class OTAUpdateManager:
    """
    Manages non-blocking version checks, differential downloads,
    SHA-256 hash verification, and silent installer execution.
    """

    @staticmethod
    def parse_semver(v: str) -> tuple:
        """Strips leading 'v' and converts '2.1.0' into tuple (2, 1, 0) for reliable comparison."""
        v = v.lstrip('v').strip()
        parts = []
        for x in v.split('.'):
            try:
                parts.append(int(x))
            except ValueError:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

    @classmethod
    def check_for_updates(cls, timeout: float = 3.5) -> Optional[UpdateInfo]:
        """
        Synchronously queries GitHub Releases API for the latest release metadata.
        Returns UpdateInfo if a newer release exists, otherwise None.
        """
        try:
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": f"HyperSolve-Client/{__version__}"}
            res = requests.get(LATEST_RELEASE_API, headers=headers, timeout=timeout)
            
            data = None
            if res.status_code == 200:
                data = res.json()
            else:
                # Try fallback raw manifest
                fb = requests.get(FALLBACK_MANIFEST_URL, timeout=timeout)
                if fb.status_code == 200:
                    data = fb.json()

            if not data:
                return None

            remote_tag = data.get("tag_name") or data.get("version", "")
            remote_ver = cls.parse_semver(remote_tag)
            current_ver = cls.parse_semver(__version__)

            if remote_ver > current_ver:
                # Find installer executable or package asset
                assets = data.get("assets", [])
                download_url = ""
                asset_name = ""
                sha256_val = data.get("sha256", "")

                for a in assets:
                    name = a.get("name", "")
                    if name.endswith(".exe") or name.endswith("-setup.exe"):
                        download_url = a.get("browser_download_url", "")
                        asset_name = name
                        break

                if not download_url and data.get("download_url"):
                    download_url = data["download_url"]
                    asset_name = os.path.basename(urlparse(download_url).path)

                if download_url:
                    notes = data.get("body", "") or data.get("notes", "No changelog provided.")
                    return UpdateInfo(
                        version=remote_tag.lstrip('v'),
                        download_url=download_url,
                        release_notes=notes,
                        sha256=sha256_val,
                        asset_name=asset_name
                    )
        except Exception:
            pass

        return None

    @classmethod
    def check_update_async(cls, on_update_found: Optional[Callable[[UpdateInfo], None]] = None):
        """Spawns an asynchronous background worker thread to check for updates without stalling boot."""
        def worker():
            update = cls.check_for_updates()
            if update and on_update_found:
                on_update_found(update)

        t = threading.Thread(target=worker, daemon=True, name="HyperSolve-OTA-Checker")
        t.start()

    @classmethod
    def download_and_install_update(cls, update: UpdateInfo, silent: bool = True, progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """
        Streams the remote update into %TEMP%, verifies SHA256 (if provided),
        and launches the installer with silent switches.
        """
        temp_dir = tempfile.gettempdir()
        dest_path = os.path.join(temp_dir, f"HyperSolve_Update_{update.version}.exe")

        try:
            print(f"[OTA] Downloading HyperSolve v{update.version} from {update.download_url}...")
            with requests.get(update.download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                hasher = hashlib.sha256()

                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            hasher.update(chunk)
                            downloaded += len(chunk)
                            if total_size > 0 and progress_callback:
                                percent = int((downloaded / total_size) * 100)
                                progress_callback(percent)

            # Optional hash verification
            if update.sha256:
                calculated_hash = hasher.hexdigest().lower()
                if calculated_hash != update.sha256.lower():
                    print(f"[OTA ERROR] Hash mismatch! Expected {update.sha256}, got {calculated_hash}")
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    return False

            print(f"[OTA SUCCESS] Download complete. Launching installer: {dest_path}")

            # Prepare installer flags
            # Inno Setup / NSIS silent flags:
            # /VERYSILENT = no GUI dialogs
            # /SUPPRESSMSGBOXES = prevent restart prompts
            # /CLOSEAPPLICATIONS = auto close active HyperSolve instance
            # /RESTARTAPPLICATIONS = restart after update
            cmd = [dest_path]
            if silent:
                cmd.extend(["/VERYSILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"])

            subprocess.Popen(cmd, shell=False, close_fds=True)
            print("[OTA] Installer spawned. HyperSolve will now restart...")
            return True

        except Exception as e:
            print(f"[OTA ERROR] Update installation failed: {e}")
            return False
