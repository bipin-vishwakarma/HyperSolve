"""Release updates with mandatory checksums and visible failures."""
import hashlib
import logging
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from urllib.parse import urlparse

import requests
from hypersolve.__version__ import __version__

GITHUB_REPO = "bipin-vishwakarma/HyperSolve"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class UpdateInfo:
    def __init__(self, version, download_url, release_notes="", sha256="", asset_name=""):
        self.version = version
        self.download_url = download_url
        self.release_notes = release_notes
        self.sha256 = sha256
        self.asset_name = asset_name


class OTAUpdateManager:
    @staticmethod
    def parse_semver(version):
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version.strip())
        if not match:
            raise ValueError("Unsupported release version")
        return tuple(map(int, match.groups()))

    @staticmethod
    def _trusted_url(url):
        parsed = urlparse(url)
        return (parsed.scheme == "https" and parsed.netloc == "github.com"
                and parsed.path.startswith(f"/{GITHUB_REPO}/releases/download/")
                and not parsed.query and not parsed.fragment)

    @classmethod
    def check_for_updates(cls, timeout=5):
        response = requests.get(LATEST_RELEASE_API, timeout=timeout,
                                headers={"Accept": "application/vnd.github+json", "User-Agent": "HyperSolve"})
        if response.status_code == 404:
            raise RuntimeError("No published release is available. Check the project release page.")
        response.raise_for_status()
        release = response.json()
        tag = release["tag_name"]
        if release.get("draft") or release.get("prerelease"):
            return None
        if cls.parse_semver(tag) <= cls.parse_semver(__version__):
            return None
        assets = release.get("assets", [])
        manifest_asset = next((a for a in assets if a["name"] == "latest.json"), None)
        if not manifest_asset or not cls._trusted_url(manifest_asset["browser_download_url"]):
            raise RuntimeError("This release has no trusted checksum manifest.")
        manifest_response = requests.get(manifest_asset["browser_download_url"], timeout=timeout)
        manifest_response.raise_for_status()
        manifest = manifest_response.json()
        url, checksum = manifest.get("download_url", ""), manifest.get("sha256", "")
        if (cls.parse_semver(manifest.get("version", "")) != cls.parse_semver(tag)
                or not cls._trusted_url(url) or not re.fullmatch(r"[0-9a-fA-F]{64}", checksum)
                or not any(a.get("browser_download_url") == url and a.get("name", "").endswith(".exe") for a in assets)):
            raise RuntimeError("The release installer or checksum manifest is invalid.")
        return UpdateInfo(tag.lstrip("v"), url, release.get("body", ""), checksum, Path(urlparse(url).path).name)

    @classmethod
    def check_update_async(cls, on_update_found=None):
        def check():
            try:
                info = cls.check_for_updates()
                if info and on_update_found:
                    on_update_found(info)
            except Exception:
                logging.exception("Update check failed")
        threading.Thread(target=check, daemon=True).start()

    @classmethod
    def download_and_install_update(cls, update, silent=False, progress_callback=None):
        if not cls._trusted_url(update.download_url) or not re.fullmatch(r"[0-9a-fA-F]{64}", update.sha256):
            raise ValueError("A trusted release URL and SHA-256 checksum are required.")
        directory = Path(tempfile.mkdtemp(prefix="HyperSolve-update-"))
        destination = directory / "HyperSolve-Setup.exe"
        try:
            digest = hashlib.sha256()
            with requests.get(update.download_url, stream=True, timeout=(5, 30)) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                size = 0
                with destination.open("wb") as output:
                    for chunk in response.iter_content(65536):
                        if chunk:
                            output.write(chunk)
                            digest.update(chunk)
                            size += len(chunk)
                            if progress_callback and total:
                                progress_callback(min(100, int(size / total * 100)))
            if digest.hexdigest().lower() != update.sha256.lower():
                raise ValueError("Installer checksum mismatch. Download discarded.")
            command = [str(destination)]
            if silent:
                command += ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
            subprocess.Popen(command, shell=False, close_fds=True)
            return True
        except Exception:
            destination.unlink(missing_ok=True)
            directory.rmdir()
            raise
