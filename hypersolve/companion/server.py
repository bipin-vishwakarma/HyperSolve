"""Authenticated loopback endpoint reachable through the native bridge."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
from .agents import AgentManager


def data_dir():
    return Path(os.getenv("HYPERSOLVE_DATA_DIR", Path(os.getenv("LOCALAPPDATA", Path.home())) / "HyperSolve"))


class CompanionServer:
    def __init__(self, manager=None, directory=None):
        self.manager = manager or AgentManager()
        self.directory = Path(directory) if directory else data_dir()
        self.token = secrets.token_urlsafe(32)
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.connection.settimeout(6)
                if (self.client_address[0] != "127.0.0.1" or self.headers.get("Origin")
                        or self.headers.get("Host") != f"127.0.0.1:{owner.http.server_port}"
                        or not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + owner.token)):
                    self.reply(403,{"error":"Not authorized"})
                    return
                try:
                    length = int(self.headers.get("Content-Length","0"))
                    if not 1 <= length <= 1_000_000 or self.headers.get_content_type() != "application/json":
                        raise ValueError("Invalid message size or type")
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload,dict) or self.path != "/message":
                        raise ValueError("Invalid message")
                    self.reply(200,owner.dispatch(payload))
                except (ValueError,TypeError,KeyError) as exc:
                    self.reply(400,{"error":str(exc)[:500]})
                except Exception:
                    self.reply(500,{"error":"Manager request failed"})
            def reply(self,status,data):
                body = json.dumps(data,ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(body)))
                self.send_header("Cache-Control","no-store")
                self.end_headers()
                self.wfile.write(body)
            def log_message(self,*args):
                pass
        self.http = ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.http.daemon_threads = True
        self.thread = threading.Thread(target=self.http.serve_forever,daemon=True)

    def start(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        endpoint = {"url":f"http://127.0.0.1:{self.http.server_port}/message","token":self.token,"pid":os.getpid()}
        temporary = self.directory / f"companion-endpoint-{os.getpid()}.tmp"
        temporary.write_text(json.dumps(endpoint),encoding="utf-8")
        temporary.replace(self.directory / "companion-endpoint.json")
        self.thread.start()

    def dispatch(self,payload):
        client = payload.get("client")
        if not isinstance(client,str) or not 1 <= len(client) <= 100:
            raise ValueError("Invalid browser identity")
        op = payload.get("op")
        job_id = payload.get("id")
        if op == "hello":
            return self.manager.hello(client,payload.get("browser","Browser"))
        if op == "detect":
            return self.manager.detect(client,payload)
        if op == "poll":
            self.manager.hello(client,payload.get("browser","Browser"))
            return self.manager.snapshot(client)
        if op == "get":
            return self.manager.get(client,job_id)
        if op == "control":
            return self.manager.control(client,job_id,payload.get("action"))
        if op == "progress":
            return self.manager.progress(client,job_id,payload.get("phase"),payload.get("detail",""),payload.get("total"),payload.get("provider"))
        if op == "solve":
            return self.manager.solve(client,job_id,payload.get("questions"))
        if op == "response":
            return self.manager.response(client,job_id,payload.get("raw"),payload.get("provider","Browser AI"))
        if op == "report":
            return self.manager.report(client,job_id,payload.get("selected",[]),payload.get("failed",[]),bool(payload.get("finish")))
        raise ValueError("Unknown manager operation")

    def close(self):
        self.manager.close()
        self.http.shutdown()
        self.http.server_close()
        endpoint = self.directory / "companion-endpoint.json"
        try:
            if json.loads(endpoint.read_text())["token"] == self.token:
                endpoint.unlink(missing_ok=True)
        except (OSError,ValueError,KeyError):
            pass
