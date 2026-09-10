import os
import re
import json
import base64
import tempfile
from dataclasses import dataclass
from typing import Optional, Dict, Any
from PIL import Image
import requests
from .screen_capture import ScreenCapturer

@dataclass
class VisionSolveResult:
    question: str
    selected_answer: str
    x_percent: float  # 0.0 - 1.0 (X coordinate of the radio/choice button)
    y_percent: float  # 0.0 - 1.0 (Y coordinate of the radio/choice button)
    confidence: float = 98.5
    brain_used: str = "Zero-Key AI"

class VLMSolver:
    """
    Multimodal Vision-Language Solver with Zero-API-Key Architecture.
    
    1. Zero-API-Key Mode (Default):
       Leverages the user's active ChatGPT / Gemini session open in Chrome.
       Completely free, no subscriptions or developer API keys needed.
    2. Turbo API Mode (Optional):
       Uses GEMINI_API_KEY or OPENAI_API_KEY from .env if provided.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            # Check for .env file in project root
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
            if os.path.isfile(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                k, v = k.strip(), v.strip().strip("'\"")
                                if k in ("GEMINI_API_KEY", "OPENAI_API_KEY") and v:
                                    self.api_key = v
                                    os.environ[k] = v
                                    break
                except Exception:
                    pass

    def solve_screen(self, img: Image.Image) -> Optional[VisionSolveResult]:
        """Analyzes screen image and resolves the question + answer coordinates."""
        jpeg_bytes = ScreenCapturer.to_jpeg_bytes(img, quality=80)
        b64_img = base64.b64encode(jpeg_bytes).decode("utf-8")

        prompt = (
            "You are an automated assessment vision solver.\n"
            "Analyze the image of this test or quiz question on screen.\n"
            "1. Read the main question text and the multiple-choice options.\n"
            "2. Determine which option is factually correct.\n"
            "3. Identify the EXACT center point of the correct option's radio button, checkbox, or card.\n"
            "Return ONLY a JSON object with this exact schema:\n"
            "{\n"
            '  "question": "question text",\n'
            '  "answer": "text of the correct choice",\n'
            '  "x_percent": 0.45,  // horizontal position of choice button from 0.0 (left) to 1.0 (right)\n'
            '  "y_percent": 0.62,  // vertical position of choice button from 0.0 (top) to 1.0 (bottom)\n'
            '  "confidence": 99.2\n'
            "}"
        )

        # 1. Optional Turbo API (if key is explicitly set in .env)
        gemini_key = os.getenv("GEMINI_API_KEY") or (self.api_key if self.api_key and not self.api_key.startswith("sk-") else None)
        openai_key = os.getenv("OPENAI_API_KEY") or (self.api_key if self.api_key and self.api_key.startswith("sk-") else None)

        if gemini_key:
            self.api_key = gemini_key
            res = self._query_gemini(b64_img, prompt)
            if res:
                res.brain_used = "Gemini 2.0 (Turbo API)"
                return res

        if openai_key:
            self.api_key = openai_key
            res = self._query_openai(b64_img, prompt)
            if res:
                res.brain_used = "GPT-4o (Turbo API)"
                return res

        # 2. Zero-API-Key Mode: Harvest active ChatGPT / Gemini tab session
        return self._query_browser_zero_key(img, prompt)

    def _query_browser_zero_key(self, img: Image.Image, prompt: str) -> Optional[VisionSolveResult]:
        """Queries the active authenticated browser session over Chrome CDP without API keys."""
        try:
            import asyncio
            return asyncio.run(self._async_query_browser_zero_key(img, prompt))
        except Exception as e:
            print(f"[VLM ZERO-KEY] Could not query browser session: {e}")
        return None

    async def _async_query_browser_zero_key(self, img: Image.Image, prompt: str) -> Optional[VisionSolveResult]:
        from playwright.async_api import async_playwright
        from hypersolve.router.session_pool import SessionPool

        # Save screenshot to temporary JPEG
        temp_img_path = os.path.join(tempfile.gettempdir(), "hypersolve_screen.jpg")
        img.save(temp_img_path, format="JPEG", quality=85)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                session_pool = SessionPool(browser)
                providers = await session_pool.get_active_providers()

                # Try ChatGPT tab
                if providers.get("chatgpt"):
                    page = providers["chatgpt"][0]
                    raw = await session_pool.query_chatgpt_background(page, prompt, image_path=temp_img_path)
                    if raw:
                        res = self._parse_json_result(raw)
                        if res:
                            res.brain_used = "ChatGPT (Free Tab)"
                            return res

                # Try Gemini tab
                if providers.get("gemini"):
                    page = providers["gemini"][0]
                    raw = await session_pool.query_gemini_background(page, prompt, image_path=temp_img_path)
                    if raw:
                        res = self._parse_json_result(raw)
                        if res:
                            res.brain_used = "Gemini (Free Tab)"
                            return res

        except Exception as e:
            print(f"[VLM NOTICE] No Chrome session active on 9222. Error: {e}")
        finally:
            if os.path.exists(temp_img_path):
                try:
                    os.remove(temp_img_path)
                except Exception:
                    pass

        return None

    def _query_gemini(self, b64_img: str, prompt: str) -> Optional[VisionSolveResult]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}}
                ]
            }],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return self._parse_json_result(raw_text)
        except Exception as e:
            print(f"[VLM ERROR] Gemini Vision request failed: {e}")
        return None

    def _query_openai(self, b64_img: str, prompt: str) -> Optional[VisionSolveResult]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }],
            "response_format": {"type": "json_object"}
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                raw_text = data["choices"][0]["message"]["content"]
                return self._parse_json_result(raw_text)
        except Exception as e:
            print(f"[VLM ERROR] OpenAI Vision request failed: {e}")
        return None

    def _parse_json_result(self, raw_text: str) -> Optional[VisionSolveResult]:
        try:
            match = re.search(r'\{[\s\S]*\}', raw_text)
            if match:
                data = json.loads(match.group(0))
                return VisionSolveResult(
                    question=data.get("question", ""),
                    selected_answer=data.get("answer", ""),
                    x_percent=float(data.get("x_percent", 0.5)),
                    y_percent=float(data.get("y_percent", 0.5)),
                    confidence=float(data.get("confidence", 98.5))
                )
        except Exception:
            pass
        return None
