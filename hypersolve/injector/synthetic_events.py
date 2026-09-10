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
            # 1. First attempt: Native Playwright Hardware Click
            target = page.locator(f'[data-hypersolve-opt="{opt_marker}"]').first
            if await target.count() > 0 and await target.is_visible():
                await target.scroll_into_view_if_needed()
                await target.click(force=True)
                await asyncio.sleep(random.uniform(0.1, 0.25))
                return True
        except Exception:
            pass

        # 2. Second attempt: Synthetic PointerEvent & Direct Callback Dispatch
        success = await page.evaluate(f"""(marker, index) => {{
            const input = document.querySelector(`[data-hypersolve-opt="${{marker}}"]`);
            if (!input) return false;

            // Scroll into view
            input.scrollIntoView({{ behavior: 'smooth', block: 'center' }});

            // Native synthetic sequence
            const sequence = [
                new PointerEvent('pointerdown', {{ bubbles: true, cancelable: true, pointerType: 'mouse' }}),
                new MouseEvent('mousedown', {{ bubbles: true, cancelable: true }}),
                new FocusEvent('focus', {{ bubbles: true }}),
                new PointerEvent('pointerup', {{ bubbles: true, cancelable: true, pointerType: 'mouse' }}),
                new MouseEvent('mouseup', {{ bubbles: true, cancelable: true }}),
                new MouseEvent('click', {{ bubbles: true, cancelable: true }})
            ];
            sequence.forEach(evt => input.dispatchEvent(evt));

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
