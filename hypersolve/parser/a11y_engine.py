import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

@dataclass
class QuizOption:
    index: int
    text: str
    is_checked: bool = False
    ref_id: Optional[str] = None

@dataclass
class QuizQuestion:
    id: int
    text: str
    options: List[QuizOption] = field(default_factory=list)
    is_answered: bool = False
    dom_id: Optional[str] = None

class UniversalA11yParser:
    """
    Multi-Strategy Universal Question Detector.
    Uses targeted platform adapters (Moodle, Canvas, Aspirations, Google Forms)
    backed by semantic DOM clustering for 100% reliable detection.
    """

    @staticmethod
    async def parse_page(page: Page) -> List[QuizQuestion]:
        """
        Extracts questions and choices with deterministic accuracy.
        """
        script = (Path(__file__).parent / "dom_parser.js").read_text(encoding="utf-8")
        extracted_data = await page.evaluate("() => { " + script + "; return globalThis.HyperSolveParser(); }")

        parsed_questions: List[QuizQuestion] = []
        for q in extracted_data:
            options = [
                QuizOption(
                    index=opt["index"],
                    text=opt["text"],
                    is_checked=opt["is_checked"],
                    ref_id=opt["ref_id"]
                ) for opt in q["options"]
            ]
            parsed_questions.append(
                QuizQuestion(
                    id=q["id"],
                    text=q["text"],
                    options=options,
                    is_answered=q["is_answered"],
                    dom_id=q["dom_id"]
                )
            )

        return parsed_questions
