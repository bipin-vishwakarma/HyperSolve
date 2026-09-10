import os
from pathlib import Path
from playwright.async_api import Page

class HUDInjector:
    """Injects and controls the HyperHUD overlay inside target quiz pages."""

    _script_cache = None

    @classmethod
    def _get_overlay_script(cls) -> str:
        if cls._script_cache is None:
            assets_dir = Path(__file__).parent / "assets"
            js_path = assets_dir / "overlay.js"
            if js_path.exists():
                cls._script_cache = js_path.read_text(encoding="utf-8")
            else:
                cls._script_cache = ""
        return cls._script_cache

    @classmethod
    async def inject(cls, page: Page):
        """Injects the isolated Shadow-DOM HUD into the page."""
        script = cls._get_overlay_script()
        if script:
            try:
                await page.evaluate(script)
            except Exception as e:
                # Page might be navigating or restricted
                pass

    @classmethod
    async def update_stats(cls, page: Page, solved: int, total: int, status: str = "SOLVING", brain: str = "ChatGPT-4o"):
        """Updates the HUD dock statistics."""
        try:
            await page.evaluate(f"window.__hypersolve && window.__hypersolve.updateStats({solved}, {total}, '{status}', '{brain}')")
        except Exception:
            pass

    @classmethod
    async def start_scan(cls, page: Page, dom_id: str):
        """Triggers the holographic scanline animation on the target question container."""
        try:
            await page.evaluate(f"window.__hypersolve && window.__hypersolve.startScan('{dom_id}')")
        except Exception:
            pass

    @classmethod
    async def lock_answer(cls, page: Page, dom_id: str, opt_marker: str, confidence: float = 98.4, brain: str = "DeepSeek-R1"):
        """Displays the confidence badge and applies the lock aura to the correct option."""
        try:
            await page.evaluate(f"window.__hypersolve && window.__hypersolve.lockAnswer('{dom_id}', '{opt_marker}', {confidence}, '{brain}')")
        except Exception:
            pass
