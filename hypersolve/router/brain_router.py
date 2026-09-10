import re
import json
from typing import Dict, List, Optional, Tuple
from playwright.async_api import Browser
from hypersolve.parser.a11y_engine import QuizQuestion
from .session_pool import SessionPool

class BrainRouter:
    """
    Tiered AI Routing & Fallback Engine.
    Dispatches quiz question payloads across available AI sessions,
    validates output schemas, and seamlessly recovers from timeouts.
    """

    def __init__(self, browser: Browser):
        self.session_pool = SessionPool(browser)

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
                # Normalize keys and values
                normalized = {str(k).strip(): str(v).strip() for k, v in parsed.items()}
                return normalized
        except Exception:
            return None

        return None

    async def solve_batch(
        self, questions: List[QuizQuestion], max_attempts: int = 4
    ) -> Tuple[Optional[Dict[str, str]], str]:
        """
        Routes the prompt to the best available brain with automatic fallback.
        Returns: (answers_dict, brain_name)
        """
        providers = await self.session_pool.get_active_providers()
        prompt = self.build_prompt(questions)
        timeout_dynamic = max(60, 45 + len(questions) * 12)

        # 1. Tier 1: ChatGPT Background Session
        if providers["chatgpt"]:
            chat_tab = providers["chatgpt"][0]
            for attempt in range(max_attempts):
                raw_response = await self.session_pool.query_chatgpt_background(
                    chat_tab, prompt, timeout_seconds=timeout_dynamic
                )
                if raw_response:
                    answers = self.extract_answers_json(raw_response, len(questions))
                    if answers:
                        return answers, "ChatGPT-4o"

        # 2. Tier 2: Secondary providers or retry
        # (Can be extended with direct Gemini / Claude background evaluations or API keys)
        return None, "None"
