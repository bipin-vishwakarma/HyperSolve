"""One pause gate and stop action for the whole running session."""
import asyncio
import logging
import uuid
import time
from .injector import HUDInjector


class OverlayControls:
    def __init__(self, on_event=None):
        self.gate = asyncio.Event()
        self.gate.set()
        self.owner = None
        self.pages = set()
        self.on_event = on_event
        self.last_error = ""
        self.generation = f"{time.monotonic_ns():020d}-" + uuid.uuid4().hex
        self.binding = "__hs_control_" + uuid.uuid4().hex

    async def attach(self, page):
        if page not in self.pages:
            await HUDInjector.install(page, self.binding, self.handle, self.generation)
            self.pages.add(page)
        else:
            await HUDInjector.reset(page)
        self.last_error = ""
        await HUDInjector.set_paused(page, not self.gate.is_set())

    async def checkpoint(self):
        await self.gate.wait()

    async def handle(self, source, action):
        if (source.get("page") not in self.pages or action not in ("pause", "resume", "stop")
                or (source.get("frame") and source["frame"] != source["page"].main_frame)):
            return {"accepted": False}
        if not self.owner or self.owner.done():
            return {"accepted": False}
        if action == "stop":
            asyncio.get_running_loop().call_soon(self.owner.cancel)
        else:
            if action == "pause":
                self.gate.clear()
            else:
                self.gate.set()
            if self.on_event:
                self.on_event("paused", action == "pause")
            for page in tuple(self.pages):
                try:
                    if not page.is_closed():
                        await HUDInjector.set_paused(page, action == "pause")
                except Exception:
                    logging.debug("Could not update paused overlay", exc_info=True)
        return {"accepted": True}

    async def finish(self):
        self.gate.set()
        self.owner = None
        async def finish_page(page):
            try:
                if not page.is_closed():
                    await asyncio.wait_for(HUDInjector.finish(page, self.last_error), timeout=1)
            except Exception:
                logging.debug("Could not update final overlay state", exc_info=True)
        await asyncio.gather(*(finish_page(page) for page in tuple(self.pages)))
