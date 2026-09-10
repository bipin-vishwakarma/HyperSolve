"""Zero-selector universal parsing engine using the browser's Accessibility Tree & semantic heuristics."""
from .a11y_engine import UniversalA11yParser, QuizQuestion, QuizOption

__all__ = ["UniversalA11yParser", "QuizQuestion", "QuizOption"]
