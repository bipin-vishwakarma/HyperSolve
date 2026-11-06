"""Local Chrome integration smoke: no real account, AI service, or external site."""
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import sys
import tempfile
import threading
from unittest.mock import AsyncMock, MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hypersolve.desktop.runtime import find_chrome
from hypersolve.desktop.workspaces import save_workspace, restore_workspace, load_workspace
from hypersolve.core.browser import BrowserManager
from hypersolve.core.daemon import HyperSolveDaemon
from playwright.async_api import async_playwright

QUIZ = b'<title>Local practice</title><section class="qcard"><div class="qtext">Practice question?</div><div class="opt" role="radio" aria-checked="false">A. First</div><div class="opt" role="radio" aria-checked="false">B. Second</div></section>'
SETTINGS = b'<title>Quiz settings</title><fieldset><legend>Choose your preferred colour</legend><label><input type="radio" name="colour">Blue</label><label><input type="radio" name="colour">Red</label></fieldset>'

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/lesson?quiz=redirected")
            self.end_headers()
            return
        body = SETTINGS if self.path == "/preferences" else QUIZ
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

async def main():
    chrome_path = find_chrome()
    if not chrome_path:
        raise RuntimeError("Google Chrome is required for this optional smoke")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    cdp = f"http://127.0.0.1:{port}"
    try:
        async with async_playwright() as pw:
            chrome = await pw.chromium.launch(executable_path=str(chrome_path),headless=True,args=[f"--remote-debugging-port={port}"])
            manager = BrowserManager(cdp)
            try:
                context = await chrome.new_context()
                source = await context.new_page()
                await source.goto(base + "/lesson?quiz=one")
                settings = await context.new_page()
                await settings.goto(base + "/preferences")
                await manager.connect()
                tabs = await manager.scan_tabs()
                assert len(tabs["quiz"]) == 1, "Ordinary radio preferences must not be a quiz"
                target_id = await manager.page_target_id(tabs["quiz"][0])
                assert await (await manager.find_target_page(source.url,target_id)).title() == "Local practice"
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "workspace.json"
                    save_workspace([{"url":source.url},{"url":base + "/redirect"}],source.url,path)
                    await asyncio.to_thread(restore_workspace,cdp,path)
                    redirected = next(page for page in await manager.get_all_pages() if "redirected" in page.url)
                    await redirected.reload()
                    before = len(await manager.get_all_pages())
                    await asyncio.to_thread(restore_workspace,cdp,path)
                    assert len(await manager.get_all_pages()) == before, "Repeat restore after redirect/reload duplicated a tab"
                    assert load_workspace(path)["restored_targets"]
                    assert not settings.is_closed()
                complete = asyncio.Event()
                events = []
                def event(kind,payload):
                    if kind == "complete":
                        events.append(payload)
                        if len(events) == 2:
                            complete.set()
                brain = MagicMock()
                brain.session_pool.get_active_providers = AsyncMock(return_value={"chatgpt":[object()]})
                brain.solve_batch = AsyncMock(return_value=({"1":"Second"},"Local test stub"))
                daemon = HyperSolveDaemon(cdp_url=cdp,on_event=event)
                with patch("hypersolve.core.daemon.BrainRouter",return_value=brain):
                    task = asyncio.create_task(daemon.start())
                    try:
                        await asyncio.wait_for(complete.wait(),20)
                        assert not task.done(), "Watch stopped after a completed quiz"
                    finally:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                assert brain.solve_batch.await_count == 2
                assert await settings.locator("input:checked").count() == 0
                await manager.disconnect()
                assert await source.title() == "Local practice"
                print("PASS: DOM detection, unrelated-form exclusion, exact targets, save/restore after redirect/reload, two-quiz Watch, cancellation, browser-preserving disconnect")
            finally:
                await manager.disconnect()
                await chrome.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    asyncio.run(main())
