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
            # Dismiss any blocking welcome modals or cookies
            for dismiss_sel in ['button:has-text("Stay logged out")', 'button[aria-label="Close"]', 'button:has-text("Dismiss")']:
                btn = page.locator(dismiss_sel)
                if await btn.count() > 0 and await btn.first.is_visible():
                    try:
                        await btn.first.click(timeout=1000)
                    except Exception:
                        pass

            # Check if login is required
            login_btn = page.locator('button:has-text("Log in"), a[href*="login"]')
            textarea = page.locator('#prompt-textarea, div[contenteditable="true"]')
            if await textarea.count() == 0 and await login_btn.count() > 0:
                print("[SESSION POOL] ChatGPT tab is open, but NOT logged in. Please sign in!")
                return None

            await textarea.first.wait_for(state='visible', timeout=8000)

            # Record existing assistant messages before sending
            initial_count = await page.locator('[data-message-author-role="assistant"]').count()

            # Optional image upload via file input
            if image_path and os.path.isfile(image_path):
                file_input = page.locator('input[type="file"]')
                if await file_input.count() > 0:
                    await file_input.first.set_input_files(image_path)
                    await asyncio.sleep(1.5)

            # Fill prompt & submit
            target_editor = textarea.first
            await target_editor.click()
            await target_editor.fill(prompt)
            await asyncio.sleep(0.4)

            # Click send button if present, else press Enter
            send_btn = page.locator('button[data-testid="send-button"], button[aria-label*="Send" i]').first
            if await send_btn.count() > 0 and await send_btn.is_enabled():
                await send_btn.click()
            else:
                await target_editor.press('Enter')

            # Wait for generation to start (stop button appears OR message count increments)
            stop_selector = 'button[data-testid="stop-button"], button[aria-label*="Stop" i]'
            generation_active = False
            for _ in range(10):
                await asyncio.sleep(0.5)
                if await page.locator(stop_selector).count() > 0:
                    generation_active = True
                    break
                curr_count = await page.locator('[data-message-author-role="assistant"]').count()
                if curr_count > initial_count:
                    generation_active = True
                    break

            # Wait for stop button to disappear
            if generation_active:
                try:
                    await page.wait_for_selector(
                        stop_selector,
                        state='hidden',
                        timeout=timeout_seconds * 1000
                    )
                except Exception:
                    pass

            # Poll until text stabilizes or valid JSON is found
            last_text = ""
            stable_ticks = 0
            start_t = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_t) < timeout_seconds:
                txt = await page.evaluate(r"""() => {
                    const selectors = [
                        '[class*="DilResponseRoot"]',
                        '[class*="response-root"]',
                        '[data-message-author-role="assistant"]',
                        'div[class*="agent-turn"]',
                        '.markdown'
                    ];
                    for (const sel of selectors) {
                        const els = Array.from(document.querySelectorAll(sel));
                        if (els.length > 0) {
                            return els[els.length - 1].innerText;
                        }
                    }
                    const codeEls = Array.from(document.querySelectorAll('pre, code, [class*="TextBase"]'));
                    for (let i = codeEls.length - 1; i >= 0; i--) {
                        const t = codeEls[i].innerText;
                        if (t && t.includes('{') && t.includes('}')) return t;
                    }
                    return null;
                }""")
                if txt:
                    clean_txt = txt.strip()
                    # If valid JSON is detected, return immediately!
                    if "{" in clean_txt and "}" in clean_txt:
                        return clean_txt
                    if clean_txt == last_text:
                        stable_ticks += 1
                        if stable_ticks >= 2:
                            return clean_txt
                    else:
                        stable_ticks = 0
                        last_text = clean_txt
                await asyncio.sleep(0.5)

            if last_text:
                return last_text

        except Exception as e:
            print(f"[SESSION POOL] ChatGPT background error: {e}")
            return None

        return None

    async def query_gemini_background(
        self, page: Page, prompt: str, image_path: Optional[str] = None, timeout_seconds: int = 120
    ) -> Optional[str]:
        """
        Executes a prompt query against a background Google Gemini tab WITHOUT stealing focus.
        """
        try:
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
                login_btn = page.locator('button:has-text("Sign in"), a[href*="accounts.google.com"]')
                if await login_btn.count() > 0:
                    print("[SESSION POOL] Google Gemini tab is open, but NOT logged in. Please sign in!")
                return None

            # Record initial response count
            initial_count = await page.locator('message-content, .model-response-text, div[class*="response-content"]').count()

            # Optional image upload
            if image_path and os.path.isfile(image_path):
                file_input = page.locator('input[type="file"]')
                if await file_input.count() > 0:
                    await file_input.first.set_input_files(image_path)
                    await asyncio.sleep(2.0)

            await editor.click()
            await editor.fill(prompt)
            await asyncio.sleep(0.4)

            send_btn = page.locator('button[aria-label*="Send" i], button[aria-label*="Submit" i], button.send-button').first
            if await send_btn.count() > 0 and await send_btn.is_visible():
                await send_btn.click()
            else:
                await editor.press('Enter')

            # Wait for generation to start and finish
            stop_selector = 'button[aria-label*="Stop" i], .streaming, [data-test-id="stop-button"]'
            for _ in range(8):
                await asyncio.sleep(0.5)
                if await page.locator(stop_selector).count() > 0:
                    break

            try:
                await page.wait_for_selector(
                    stop_selector,
                    state='hidden',
                    timeout=timeout_seconds * 1000
                )
            except Exception:
                pass

            # Extract response text once stable
            response_selectors = [
                'message-content',
                '.model-response-text',
                'div[class*="response-content"]',
                'div[class*="model-response"]'
            ]
            last_text = ""
            stable_ticks = 0
            start_t = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_t) < timeout_seconds:
                for r_sel in response_selectors:
                    elements = await page.locator(r_sel).all()
                    if elements:
                        txt = (await elements[-1].inner_text()).strip()
                        if txt and txt == last_text:
                            stable_ticks += 1
                            if stable_ticks >= 2:
                                return txt
                        else:
                            stable_ticks = 0
                            last_text = txt
                        break
                await asyncio.sleep(0.6)

            if last_text:
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
