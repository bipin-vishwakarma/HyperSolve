"""Generate the exact manifest consumed by the desktop update client."""
import hashlib
import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from hypersolve.__version__ import __version__
name = f"HyperSolve-Setup-v{__version__}.exe"
installer = root / "dist_installer" / name
checksum = hashlib.file_digest(installer.open("rb"), "sha256").hexdigest()
manifest = {"version": __version__, "tag_name": f"v{__version__}",
            "download_url": f"https://github.com/bipin-vishwakarma/HyperSolve/releases/download/v{__version__}/{name}",
            "sha256": checksum}
(root / "dist_installer/latest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"{name}  SHA256 {checksum}")
