"""Chrome/Edge native-messaging framing; stdout contains protocol messages only."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
from urllib.parse import urlparse
import requests
from .config import EXTENSION_ID, HOST_NAME
from .server import data_dir

MAX_MESSAGE = 1_000_000


def read_message(stream):
    header = stream.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise ValueError("Truncated native message header")
    length = struct.unpack("<I",header)[0]
    if not 1 <= length <= MAX_MESSAGE:
        raise ValueError("Native message is too large")
    body = stream.read(length)
    if len(body) != length:
        raise ValueError("Truncated native message")
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value,dict):
        raise ValueError("Expected native message object")
    return value


def write_message(stream,value):
    body = json.dumps(value,ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_MESSAGE:
        body = json.dumps({"request":value.get("request"),"error":"Manager response is too large"}).encode()
    stream.write(struct.pack("<I",len(body)) + body)
    stream.flush()


def read_endpoint():
    data = json.loads((data_dir() / "companion-endpoint.json").read_text(encoding="utf-8"))
    url = urlparse(data["url"])
    if (url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port
            or url.path != "/message" or url.query or url.fragment or url.username or url.password
            or not isinstance(data.get("token"),str) or len(data["token"]) < 32):
        raise ValueError("Invalid local manager endpoint")
    return data


def launch_manager():
    if getattr(sys,"frozen",False):
        command = [str(Path(sys.executable).with_name("HyperSolve.exe")),"--tray"]
    else:
        root = Path(__file__).resolve().parents[2]
        command = [sys.executable,str(root / "main.py"),"--tray"]
    subprocess.Popen(command,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),close_fds=True)


def main():
    expected = f"chrome-extension://{EXTENSION_ID}/"
    if not any(argument.rstrip("/") == expected.rstrip("/") for argument in sys.argv[1:]):
        return 1
    if sys.platform == "win32":
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(),os.O_BINARY)
    launched = False
    local = requests.Session()
    local.trust_env = False  # Loopback credentials must never pass through an environment proxy.
    while True:
        try:
            message = read_message(sys.stdin.buffer)
        except (ValueError,OSError) as exc:
            write_message(sys.stdout.buffer,{"error":str(exc)[:500]})
            return 1
        if message is None:
            break
        try:
            request_id = message.get("request")
            try:
                endpoint = read_endpoint()
            except (OSError,ValueError,KeyError):
                if message.get("op") == "hello" and not launched:
                    launch_manager()
                    launched = True
                    for _ in range(50):
                        try:
                            endpoint = read_endpoint()
                            break
                        except (OSError,ValueError,KeyError):
                            time.sleep(.1)
                    else:
                        raise ValueError("Open HyperSolve to connect the browser companion")
                else:
                    raise ValueError("Windows manager is offline. Open HyperSolve.")
            try:
                response = local.post(endpoint["url"],headers={"Authorization":"Bearer "+endpoint["token"]},json=message,timeout=(2,5),allow_redirects=False)
            except requests.ConnectionError:
                if message.get("op") != "hello" or launched:
                    raise
                launch_manager()
                launched = True
                for _ in range(50):
                    time.sleep(.1)
                    try:
                        endpoint = read_endpoint()
                        response = local.post(endpoint["url"],headers={"Authorization":"Bearer "+endpoint["token"]},json=message,timeout=(.3,5),allow_redirects=False)
                        break
                    except (OSError,ValueError,requests.ConnectionError):
                        continue
                else:
                    raise ValueError("Open HyperSolve to reconnect the browser companion")
            if response.status_code not in (200,400,403,500):
                raise ValueError("Unexpected manager response")
            result = response.json()
            write_message(sys.stdout.buffer,{"request":request_id,"data":result} if response.ok else {"request":request_id,"error":result.get("error","Manager unavailable")})
        except (ValueError,OSError,requests.RequestException,KeyError) as exc:
            write_message(sys.stdout.buffer,{"request":locals().get("request_id"),"error":str(exc)[:500]})
    return 0


def register_bridge(bridge_path=None):
    if sys.platform != "win32":
        raise ValueError("Native registration is supported on Windows")
    import winreg
    root = Path(__file__).resolve().parents[2]
    bridge = Path(bridge_path) if bridge_path else (Path(sys.executable).with_name("HyperSolveBridge.exe") if getattr(sys,"frozen",False) else root / "dist/HyperSolve/HyperSolveBridge.exe")
    if not bridge.is_file():
        raise ValueError("Build or install HyperSolve first; the native bridge executable is missing")
    directory = data_dir()
    directory.mkdir(parents=True,exist_ok=True)
    manifest = directory / "native-host.json"
    manifest.write_text(json.dumps({"name":HOST_NAME,"description":"HyperSolve Windows manager","path":str(bridge.resolve()),"type":"stdio","allowed_origins":[f"chrome-extension://{EXTENSION_ID}/"]},indent=2),encoding="utf-8")
    for vendor in ("Google\\Chrome","Microsoft\\Edge"):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,rf"Software\{vendor}\NativeMessagingHosts\{HOST_NAME}") as key:
            winreg.SetValueEx(key,"",0,winreg.REG_SZ,str(manifest.resolve()))
    return str(manifest)
