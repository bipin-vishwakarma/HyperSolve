import asyncio
import random
from playwright.async_api import Page

class SyntheticInjector:
    """
    Dispatches hardware-level mouse clicks via CDP and falls back to
    synthetic event chains to guarantee selection across all frameworks.
    """

    @staticmethod
    async def select_option(page: Page, opt_marker: str, opt_index: int = 0) -> bool:
        """
        Clicks the target option element using real hardware CDP clicks,
        falls back to synthetic events and platform callbacks.
        """
        try:
            # 1. Native Playwright Hardware Click:
            # Try clicking the label first (Moodle standard), then the container, then the input
            locators = [
                page.locator(f'[data-hypersolve-opt-label="{opt_marker}"]').first,
                page.locator(f'[data-hypersolve-opt-container="{opt_marker}"]').first,
                page.locator(f'[data-hypersolve-opt="{opt_marker}"]').first,
            ]
            for loc in locators:
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.scroll_into_view_if_needed()
                    await loc.click(force=True)
                    break
        except Exception:
            pass

        # 2. Enforce selection via synthetic event chain & DOM events
        # This guarantees that even if the radio is custom-styled with opacity: 0,
        # the radio input is checked and the change/input events fire for Moodle autosave.
        success = await page.evaluate(f"""(marker, index) => {{
            const input = document.querySelector(`[data-hypersolve-opt="${{marker}}"]`);
            if (!input) return false;

            const label = document.querySelector(`[data-hypersolve-opt-label="${{marker}}"]`) ||
                          (input.id ? document.querySelector(`label[for="${{CSS.escape(input.id)}}"]`) : null) ||
                          input.closest('label');

            const container = document.querySelector(`[data-hypersolve-opt-container="${{marker}}"]`) || input.closest('div');

            const clickTarget = label || container || input;
            try {{
                clickTarget.click();
            }} catch(e) {{}}

            // Native synthetic mouse event chain
            ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evtName => {{
                try {{
                    clickTarget.dispatchEvent(new MouseEvent(evtName, {{ bubbles: true, cancelable: true, view: window }}));
                }} catch(e) {{}}
            }});

            if (input.tagName === 'INPUT') {{
                input.checked = true;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }} else {{
                input.setAttribute('aria-checked', 'true');
                input.classList.add('sel', 'selected', 'checked');
            }}

            // Site-specific handler hook if present (e.g. Aspirations Institute)
            try {{
                if (typeof window.APP !== 'undefined' && typeof window.APP.pick === 'function') {{
                    window.APP.pick(index);
                }}
            }} catch(e) {{}}

            return true;
        }}""", opt_marker, opt_index)

        await asyncio.sleep(random.uniform(0.1, 0.25))
        return success

        await asyncio.sleep(random.uniform(0.1, 0.25))
        return success
