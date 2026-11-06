"""Visible browser panel injection and structured state updates."""
import json
from pathlib import Path


class HUDInjector:
    _script_cache = None

    @classmethod
    def _get_overlay_script(cls):
        if cls._script_cache is None:
            assets = Path(__file__).parent / "assets"
            cls._script_cache = (assets / "overlay.js").read_text(encoding="utf-8").replace(
                "__HYPERSOLVE_CSS__", json.dumps((assets / "styles.css").read_text(encoding="utf-8")))
        return cls._script_cache

    @classmethod
    async def inject(cls, page):
        await page.evaluate(cls._get_overlay_script().replace("__HYPERSOLVE_BINDING__", "null").replace("__HYPERSOLVE_GENERATION__", '""'))

    @classmethod
    async def install(cls, page, binding_name, handler, generation=""):
        await page.expose_binding(binding_name, handler)
        script = cls._get_overlay_script().replace("__HYPERSOLVE_BINDING__", json.dumps(binding_name)).replace("__HYPERSOLVE_GENERATION__", json.dumps(generation))
        await page.add_init_script(script=script)
        await page.evaluate(script)
        await page.evaluate("() => window.__hypersolve?.reset()")

    @classmethod
    async def update_stats(cls, page, solved, total, status="SOLVING", brain=""):
        await page.evaluate("args => window.__hypersolve?.updateStats(...args)", [solved, total, status, brain])

    @classmethod
    async def start_scan(cls, page, dom_id):
        await page.evaluate("id => window.__hypersolve?.startScan(id)", dom_id)

    @classmethod
    async def lock_answer(cls, page, dom_id, opt_marker, confidence=None, brain="", question_id=None, answer_text=""):
        await page.evaluate("args => window.__hypersolve?.lockAnswer(...args)",
                            [dom_id, opt_marker, confidence, brain, question_id, answer_text])

    @classmethod
    async def set_paused(cls, page, paused):
        await page.evaluate("paused => window.__hypersolve?.setPaused(paused)", paused)

    @classmethod
    async def finish(cls, page, error=""):
        await page.evaluate("error => window.__hypersolve?.finish(error)", error)
