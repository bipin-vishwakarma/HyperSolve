import asyncio
import re
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from playwright.async_api import Page, Browser

class SessionPool:
    """
    Manages active authenticated AI web sessions (ChatGPT, Gemini, Claude)
    via background CDP tab contexts without stealing foreground window focus
    and requiring ZERO API keys or developer credentials.
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
        self, page: Page, prompt: str, image_path: Optional[str] = None, timeout_seconds: int = 120
    ) -> Optional[str]:
        """
        Executes a prompt query against a background ChatGPT tab WITHOUT bringing it to front.
        Optionally attaches an image/screenshot without requiring OpenAI Vision API keys.
        """
        try:
            textarea = page.locator('#prompt-textarea')
            await textarea.wait_for(state='visible', timeout=8000)

            # Optional image upload via file input
            if image_path and os.path.isfile(image_path):
                file_input = page.locator('input[type="file"]')
                if await file_input.count() > 0:
                    await file_input.first.set_input_files(image_path)
                    await asyncio.sleep(1.5)  # Allow upload preview to mount

            # Fill prompt & submit
            await textarea.fill(prompt)
            await asyncio.sleep(0.3)
            await textarea.press('Enter')

            # Wait for generation to start
            try:
                await page.wait_for_selector('button[aria-label="Stop generating"]', state='visible', timeout=4000)
            except Exception:
                pass

            # Wait for generation to complete
            try:
                await page.wait_for_selector(
                    'button[aria-label="Stop generating"]',
                    state='hidden',
                    timeout=timeout_seconds * 1000
                )
            except Exception:
                pass

            # Retrieve newly generated assistant message
            assistant_messages = await page.locator('[data-message-author-role="assistant"]').all()
            if assistant_messages:
                last_msg = await assistant_messages[-1].inner_text()
                return last_msg

        except Exception as e:
            print(f"[SESSION POOL] ChatGPT background error: {e}")
            return None

        return None

    async def query_gemini_background(
        self, page: Page, prompt: str, image_path: Optional[str] = None, timeout_seconds: int = 120
    ) -> Optional[str]:
        """
        Executes a prompt query against a background Google Gemini tab WITHOUT stealing focus.
        Optionally attaches an image/screenshot without requiring Google Cloud Gemini API keys.
        """
        try:
            # Gemini input area can be rich-textarea or contenteditable div
            editor_selectors = [
                'rich-textarea div[contenteditable="true"]',
                'div[role="textbox"][contenteditable="true"]',
                'textarea.textarea',
                'div.ql-editor'
            ]
            editor = None
            for sel in editor_selectors:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    editor = loc.first
                    break

            if not editor:
                print("[SESSION POOL] Gemini input box not found")
                return None

            # Optional image upload in Gemini
            if image_path and os.path.isfile(image_path):
                file_input = page.locator('input[type="file"]')
                if await file_input.count() > 0:
                    await file_input.first.set_input_files(image_path)
                    await asyncio.sleep(2.0)  # Allow thumbnail to attach

            # Fill prompt
            await editor.click()
            await editor.fill(prompt)
            await asyncio.sleep(0.3)

            # Send via Enter or Send button
            send_btn = page.locator('button[aria-label*="Send"], button[aria-label*="Submit"], button.send-button')
            if await send_btn.count() > 0 and await send_btn.first.is_visible():
                await send_btn.first.click()
            else:
                await editor.press('Enter')

            # Wait for generation to start and finish
            await asyncio.sleep(2.0)
            try:
                await page.wait_for_selector(
                    'button[aria-label*="Stop"], .streaming',
                    state='hidden',
                    timeout=timeout_seconds * 1000
                )
            except Exception:
                pass

            # Extract response text
            response_selectors = [
                'message-content',
                '.model-response-text',
                'div[class*="response-content"]',
                'div[class*="model-response"]'
            ]
            for r_sel in response_selectors:
                elements = await page.locator(r_sel).all()
                if elements:
                    last_text = await elements[-1].inner_text()
                    if last_text and len(last_text.strip()) > 0:
                        return last_text

        except Exception as e:
            print(f"[SESSION POOL] Gemini background error: {e}")
            return None

        return None

    async def query_claude_background(
        self, page: Page, prompt: str, timeout_seconds: int = 120
    ) -> Optional[str]:
        """
        Executes a prompt query against a background Claude tab WITHOUT stealing focus.
        """
        try:
            editor = page.locator('div[contenteditable="true"]').first
            await editor.wait_for(state='visible', timeout=8000)

            await editor.click()
            await editor.fill(prompt)
            await asyncio.sleep(0.3)

            send_btn = page.locator('button[aria-label*="Send Message"], button[aria-label*="Send"]')
            if await send_btn.count() > 0 and await send_btn.first.is_visible():
                await send_btn.first.click()
            else:
                await editor.press('Enter')

            await asyncio.sleep(2.0)
            try:
                await page.wait_for_selector(
                    'button[aria-label*="Stop"]',
                    state='hidden',
                    timeout=timeout_seconds * 1000
                )
            except Exception:
                pass

            messages = await page.locator('div[class*="font-claude-message"]').all()
            if messages:
                return await messages[-1].inner_text()

        except Exception as e:
            print(f"[SESSION POOL] Claude background error: {e}")
            return None

        return None
