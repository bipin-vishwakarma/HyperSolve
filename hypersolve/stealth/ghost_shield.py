from playwright.async_api import Page

class GhostShield:
    """
    Ghost Shield: Anti-Proctoring & Tab Switch Neutralizer.
    Spoofs document.visibilityState, intercepts blur/visibilitychange events,
    and removes warning banners from the DOM.
    """

    SHIELD_SCRIPT = r"""(() => {
        if (window.__ghost_shield_active) return;
        window.__ghost_shield_active = true;

        // 1. Spoof Visibility & Hidden attributes
        try {
            Object.defineProperty(document, 'hidden', { get: () => false });
            Object.defineProperty(document, 'visibilityState', { get: () => 'visible' });
            Object.defineProperty(document, 'webkitVisibilityState', { get: () => 'visible' });
        } catch(e) {}

        // 2. Intercept and kill event bubbling for blur & visibilitychange
        const killEvent = (e) => {
            e.stopImmediatePropagation();
            e.stopPropagation();
        };

        window.addEventListener('blur', killEvent, true);
        window.addEventListener('focusout', killEvent, true);
        document.addEventListener('visibilitychange', killEvent, true);
        document.addEventListener('webkitvisibilitychange', killEvent, true);

        // 3. Periodic cleaner for in-DOM warning banners & site counters
        setInterval(() => {
            // Find and hide any tab switch warning banners
            const allElements = document.querySelectorAll('*');
            for (const el of allElements) {
                if (el.children.length === 0 && el.innerText && /tab\s*switch/i.test(el.innerText)) {
                    const banner = el.closest('.tabwarn, .warn, [class*="tabWarn"], div, section') || el.parentElement;
                    if (banner && banner.style.display !== 'none') {
                        banner.style.display = 'none';
                    }
                }
            }

            // Reset site-specific test counters if present
            try {
                if (window.S && window.S.T) {
                    window.S.T.tabWarns = 0;
                }
            } catch(e) {}
        }, 1000);
    })();"""

    @classmethod
    async def arm(cls, page: Page):
        """Arm Ghost Shield immediately in the live page context."""
        try:
            await page.evaluate(cls.SHIELD_SCRIPT)
        except Exception:
            pass
