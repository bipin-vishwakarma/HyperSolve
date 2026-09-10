import asyncio
from typing import Optional
from playwright.async_api import Browser

class HeartbeatDaemon:
    """
    The 'Breathing' Keep-Alive Worker.
    Periodically pulses background AI tabs (ChatGPT, Gemini, Claude)
    to prevent tab discarding, memory suspension, and session timeouts.
    """

    def __init__(self, browser: Browser, interval_seconds: int = 240):
        self.browser = browser
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts the breathing keep-alive background worker."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._pulse_loop())

    async def stop(self):
        """Stops the heartbeat worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _pulse_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self.interval_seconds)
                # Iterate over contexts and pages
                for ctx in self.browser.contexts:
                    for page in ctx.pages:
                        url = page.url.lower()
                        if any(domain in url for domain in ["chatgpt.com", "gemini.google.com", "claude.ai"]):
                            # Micro-pulse: run trivial JS to reset browser idle timers and prevent Chrome tab discarding
                            try:
                                await page.evaluate("() => { window.__hs_last_pulse = Date.now(); }")
                            except Exception:
                                pass
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(10)
