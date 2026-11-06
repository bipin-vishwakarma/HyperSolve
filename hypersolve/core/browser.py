import asyncio
import re
from typing import List, Dict, Tuple, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

class BrowserManager:
    """Manages the Chrome DevTools Protocol (CDP) connection and tab discovery."""

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        self.cdp_url = cdp_url
        self.playwright = None
        self.browser: Optional[Browser] = None

    async def connect(self) -> Browser:
        """Connect to the running Chrome instance over CDP."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
            return self.browser
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Chrome at {self.cdp_url}. "
                "Ensure Chrome is running with '--remote-debugging-port=9222'."
            ) from e

    async def disconnect(self):
        """Close connection cleanly without terminating user browser."""
        # Stop the CDP client, leaving the user's browser and tabs running.
        try:
            if self.playwright:
                await self.playwright.stop()
        finally:
            self.browser = None
            self.playwright = None

    async def get_all_pages(self) -> List[Page]:
        """Fetch all currently open pages across all contexts."""
        if not self.browser:
            await self.connect()
        pages = []
        for ctx in self.browser.contexts:
            pages.extend(ctx.pages)
        return pages

    async def page_target_id(self, page):
        session = await page.context.new_cdp_session(page)
        try:
            return (await session.send("Target.getTargetInfo"))["targetInfo"]["targetId"]
        finally:
            await session.detach()

    async def find_target_page(self, target_url, target_id=None):
        for page in await self.get_all_pages():
            if target_id:
                if await self.page_target_id(page) == target_id:
                    return page
            elif page.url == target_url:
                return page
        return None

    async def scan_tabs(self) -> Dict[str, List[Page]]:
        """
        Categorizes open tabs into:
        - 'quiz': Pages matching known quiz/assessment patterns or forms
        - 'chatgpt': Active ChatGPT web tabs
        - 'gemini': Active Google Gemini web tabs
        - 'claude': Active Claude AI web tabs
        """
        pages = await self.get_all_pages()
        categorized: Dict[str, List[Page]] = {
            "quiz": [],
            "chatgpt": [],
            "gemini": [],
            "claude": [],
            "other": []
        }

        from urllib.parse import urlparse
        from hypersolve.desktop.runtime import provider_for_url
        from hypersolve.parser.a11y_engine import UniversalA11yParser

        for page in pages:
            provider = provider_for_url(page.url)
            if provider:
                categorized[provider.lower()].append(page)
                continue
            if urlparse(page.url).scheme not in ("http", "https") or page.is_closed():
                categorized["other"].append(page)
                continue
            try:
                evidence = await asyncio.wait_for(page.evaluate(r"""() => {
                    const markers = document.querySelector('.qcard .qtext, .que .qtext, .question .question_text, [data-question-id]');
                    const quizTitle = /\b(quiz|assessment|exam|practice test)\b/i.test(document.title);
                    const quizPath = /(?:^|[\/_.-])(quiz|assessment|exam|test)(?:[\/_.-]|$)/i.test(location.pathname);
                    const structured = document.querySelector('.question, .question-container, [role="listitem"]');
                    return Boolean(markers) || Boolean(structured && (quizTitle || quizPath));
                }"""), timeout=2)
                if not evidence:
                    categorized["other"].append(page)
                    continue
                questions = await asyncio.wait_for(UniversalA11yParser.parse_page(page), timeout=2)
                questions = [q for q in questions if q.text.strip()
                             and not re.fullmatch(r"Question\s*\d+", q.text.strip(), flags=re.IGNORECASE)
                             and len(q.options) >= 2 and all(opt.text.strip() for opt in q.options)]
            except Exception:
                questions = []
            categorized["quiz" if questions else "other"].append(page)
        return categorized
