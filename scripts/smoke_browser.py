"""Optional local Chrome smoke; no account, provider, or external site is used."""
import asyncio
from pathlib import Path
import socket
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hypersolve.desktop.runtime import find_chrome
from hypersolve.core.browser import BrowserManager
from hypersolve.parser.a11y_engine import UniversalA11yParser
from playwright.async_api import async_playwright

async def main():
    chrome_path = find_chrome()
    if not chrome_path:
        raise RuntimeError("Google Chrome is required for this optional smoke test")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    async with async_playwright() as pw:
        chrome = await pw.chromium.launch(executable_path=str(chrome_path), headless=True,
                                         args=[f"--remote-debugging-port={port}"])
        manager = BrowserManager(f"http://127.0.0.1:{port}")
        try:
            context = await chrome.new_context()
            page = await context.new_page()
            await page.set_content('<title>HyperSolve local smoke</title><section class="qcard"><div class="qtext">Practice question?</div><div class="opt" role="radio" aria-checked="false">A. First</div><div class="opt" role="radio" aria-checked="false">B. Second</div></section>')
            questions = await UniversalA11yParser.parse_page(page)
            assert len(questions) == 1 and len(questions[0].options) == 2
            session = await context.new_cdp_session(page)
            target_id = (await session.send("Target.getTargetInfo"))["targetInfo"]["targetId"]
            await session.detach()
            await manager.connect()
            target = await manager.find_target_page(page.url, target_id)
            assert await target.title() == "HyperSolve local smoke"
            await manager.disconnect()
            assert await page.title() == "HyperSolve local smoke"
            print("PASS: isolated Chrome CDP, exact target, parser, browser-preserving disconnect")
        finally:
            await manager.disconnect()
            await chrome.close()

if __name__ == "__main__":
    asyncio.run(main())
