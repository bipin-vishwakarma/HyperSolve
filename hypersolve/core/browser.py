import asyncio
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
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def get_all_pages(self) -> List[Page]:
        """Fetch all currently open pages across all contexts."""
        if not self.browser:
            await self.connect()
        pages = []
        for ctx in self.browser.contexts:
            pages.extend(ctx.pages)
        return pages

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

        quiz_signatures = [
            "quiz", "attempt.php", "exam", "assessment", "test", 
            "docs.google.com/forms", "canvas", "blackboard", "moodle"
        ]

        for p in pages:
            url = p.url.lower()
            if "chatgpt.com" in url or "chat.openai.com" in url:
                categorized["chatgpt"].append(p)
            elif "gemini.google.com" in url:
                categorized["gemini"].append(p)
            elif "claude.ai" in url:
                categorized["claude"].append(p)
            elif any(sig in url for sig in quiz_signatures):
                categorized["quiz"].append(p)
            else:
                categorized["other"].append(p)

        return categorized
