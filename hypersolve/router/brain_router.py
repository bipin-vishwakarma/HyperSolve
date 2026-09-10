import os
import re
import json
import base64
from typing import Dict, List, Optional, Tuple, Any
from playwright.async_api import Browser
from hypersolve.parser.a11y_engine import QuizQuestion
from .session_pool import SessionPool

class BrainRouter:
    """
    Tiered AI Routing & Zero-API-Key Fallback Engine.
    Dispatches quiz question payloads across available AI sessions,
    validates output schemas, and seamlessly recovers from timeouts.

    Priority:
    1. Active ChatGPT Web Tab (Free/Plus - Zero API Key)
    2. Active Google Gemini Web Tab (Free Google Account - Zero API Key)
    3. Active Claude Web Tab (Free/Pro - Zero API Key)
    4. Optional Developer API Key (Gemini/OpenAI) if set in .env
    """

    def __init__(self, browser: Optional[Browser] = None):
        self.session_pool = SessionPool(browser) if browser else None

    def build_prompt(self, questions: List[QuizQuestion]) -> str:
        """Constructs a strict, high-accuracy JSON prompt for multiple choice questions."""
        prompt = (
            f"Solve this multiple-choice quiz containing exactly {len(questions)} questions.\n"
            f"Reply ONLY with a valid JSON dictionary mapping question IDs to the EXACT text of the correct option.\n"
            f"Ensure your JSON contains exactly {len(questions)} keys, from 1 to {len(questions)}.\n"
            f"Do not include any explanation or markdown commentary outside the JSON block.\n\n"
        )
        for q in questions:
            prompt += f"Question {q.id}: {q.text}\nOptions:\n"
            for opt in q.options:
                prompt += f"- {opt.text}\n"
            prompt += "\n"
        return prompt

    def extract_answers_json(self, raw_text: str, expected_count: int) -> Optional[Dict[str, str]]:
        """Extracts and validates JSON dictionary from model response."""
        if not raw_text:
            return None

        # Search for JSON block
        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        if not json_match:
            return None

        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, dict) and len(parsed) >= expected_count:
                normalized = {str(k).strip(): str(v).strip() for k, v in parsed.items()}
                return normalized
        except Exception:
            return None

        return None

    async def solve_batch(
        self, questions: List[QuizQuestion], max_attempts: int = 3
    ) -> Tuple[Optional[Dict[str, str]], str]:
        """
        Routes the prompt to the best available brain with automatic fallback.
        Returns: (answers_dict, brain_name)
        """
        prompt = self.build_prompt(questions)
        timeout_dynamic = max(45, 30 + len(questions) * 10)

        # 1. Try Live Browser Sessions if SessionPool is available
        if self.session_pool:
            providers = await self.session_pool.get_active_providers()

            # Priority 1: ChatGPT Tab
            if providers.get("chatgpt"):
                chat_tab = providers["chatgpt"][0]
                for attempt in range(max_attempts):
                    raw = await self.session_pool.query_chatgpt_background(
                        chat_tab, prompt, timeout_seconds=timeout_dynamic
                    )
                    if raw:
                        ans = self.extract_answers_json(raw, len(questions))
                        if ans:
                            return ans, "ChatGPT (Web Tab)"

            # Priority 2: Gemini Tab
            if providers.get("gemini"):
                gemini_tab = providers["gemini"][0]
                for attempt in range(max_attempts):
                    raw = await self.session_pool.query_gemini_background(
                        gemini_tab, prompt, timeout_seconds=timeout_dynamic
                    )
                    if raw:
                        ans = self.extract_answers_json(raw, len(questions))
                        if ans:
                            return ans, "Gemini (Web Tab)"

            # Priority 3: Claude Tab
            if providers.get("claude"):
                claude_tab = providers["claude"][0]
                for attempt in range(max_attempts):
                    raw = await self.session_pool.query_claude_background(
                        claude_tab, prompt, timeout_seconds=timeout_dynamic
                    )
                    if raw:
                        ans = self.extract_answers_json(raw, len(questions))
                        if ans:
                            return ans, "Claude (Web Tab)"

        # Priority 4: Optional Developer API Key (if provided in .env / env)
        gemini_key = os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if gemini_key:
            ans = self._query_gemini_api(prompt, gemini_key, len(questions))
            if ans:
                return ans, "Gemini 2.0 (Turbo API)"

        if openai_key:
            ans = self._query_openai_api(prompt, openai_key, len(questions))
            if ans:
                return ans, "GPT-4o (Turbo API)"

        return None, "No active brain found (Log into ChatGPT or Gemini in Chrome)"

    def _query_gemini_api(self, prompt: str, api_key: str, count: int) -> Optional[Dict[str, str]]:
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 200:
                text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                return self.extract_answers_json(text, count)
        except Exception:
            pass
        return None

    def _query_openai_api(self, prompt: str, api_key: str, count: int) -> Optional[Dict[str, str]]:
        try:
            import requests
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                text = res.json()["choices"][0]["message"]["content"]
                return self.extract_answers_json(text, count)
        except Exception:
            pass
        return None
