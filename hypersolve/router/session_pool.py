import asyncio
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from playwright.async_api import Page, Browser

class SessionPool:
    """
    Manages active authenticated AI web sessions (ChatGPT, Gemini, Claude)
    via background CDP tab contexts without stealing foreground window focus.
    """

    def __init__(self, browser: Browser):
        self.browser = browser

    async def get_active_providers(self) -> Dict[str, List[Page]]:
        """Scans all open tabs and categorizes active AI providers."""
        providers: Dict[str, List[Page]] = {
            "chatgpt": [],
            "gemini": [],
            "claude": []
        }
        for ctx in self.browser.contexts:
            for page in ctx.pages:
                url = page.url.lower()
                if "chatgpt.com" in url or "chat.openai.com" in url:
                    providers["chatgpt"].append(page)
                elif "gemini.google.com" in url:
                    providers["gemini"].append(page)
                elif "claude.ai" in url:
                    providers["claude"].append(page)
        return providers

    async def query_chatgpt_background(
        self, page: Page, prompt: str, timeout_seconds: int = 120
    ) -> Optional[str]:
        """
        Executes a prompt query against a background ChatGPT tab WITHOUT bringing it to front.
        """
        try:
            # Check prompt textarea
            textarea = page.locator('#prompt-textarea')
            await textarea.wait_for(state='visible', timeout=8000)

            # Check if there is an existing assistant message count to detect fresh replies
            initial_count = await page.locator('[data-message-author-role="assistant"]').count()

            # Fill prompt & submit
            await textarea.fill(prompt)
            await asyncio.sleep(0.3)
            await textarea.press('Enter')

            # Wait for generation to start (Stop generating button appears)
            try:
                await page.wait_for_selector('button[aria-label="Stop generating"]', state='visible', timeout=4000)
            except Exception:
                pass  # May have finished quickly or button label differs

            # Wait for generation to complete (Stop generating disappears)
            try:
                await page.wait_for_selector(
                    'button[aria-label="Stop generating"]',
                    state='hidden',
                    timeout=timeout_seconds * 1000
                )
            except Exception:
                # Timed out waiting for stop button to hide
                pass

            # Retrieve newly generated assistant message
            assistant_messages = await page.locator('[data-message-author-role="assistant"]').all()
            if assistant_messages:
                last_msg = await assistant_messages[-1].inner_text()
                return last_msg

        except Exception as e:
            # Background execution error
            return None

        return None
