import asyncio
import random
from playwright.async_api import Page

class SyntheticInjector:
    """
    Dispatches full hardware-level synthetic event sequences.
    Bypasses JavaScript framework event suppression (React, Vue, Angular, Moodle, Canvas).
    """

    @staticmethod
    async def select_option(page: Page, opt_marker: str) -> bool:
        """
        Dispatches pointerdown -> mousedown -> focus -> pointerup -> mouseup -> click -> input -> change.
        Also adds a small humanized micro-delay.
        """
        success = await page.evaluate(f"""(marker) => {{
            const input = document.querySelector(`[data-hypersolve-opt="${{marker}}"]`);
            if (!input) return false;

            // Scroll gently into view
            input.scrollIntoView({{ behavior: 'smooth', block: 'center' }});

            // Dispatch realistic synthetic event chain
            const eventSequence = [
                new PointerEvent('pointerdown', {{ bubbles: true, cancelable: true, pointerType: 'mouse' }}),
                new MouseEvent('mousedown', {{ bubbles: true, cancelable: true }}),
                new FocusEvent('focus', {{ bubbles: true }}),
                new PointerEvent('pointerup', {{ bubbles: true, cancelable: true, pointerType: 'mouse' }}),
                new MouseEvent('mouseup', {{ bubbles: true, cancelable: true }}),
                new MouseEvent('click', {{ bubbles: true, cancelable: true }})
            ];

            eventSequence.forEach(evt => input.dispatchEvent(evt));

            if (input.tagName === 'INPUT') {{
                input.checked = true;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }} else if (input.hasAttribute('aria-checked')) {{
                input.setAttribute('aria-checked', 'true');
            }}

            return true;
        }}""", opt_marker)

        # Micro-delay (100ms - 250ms) to simulate organic human rhythm
        await asyncio.sleep(random.uniform(0.1, 0.25))
        return success
