import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

@dataclass
class QuizOption:
    index: int
    text: str
    is_checked: bool = False
    ref_id: Optional[str] = None  # Internal reference or locator selector

@dataclass
class QuizQuestion:
    id: int
    text: str
    options: List[QuizOption] = field(default_factory=list)
    is_answered: bool = False
    dom_id: Optional[str] = None  # Host element identifier for visual HUD targeting

class UniversalA11yParser:
    """
    Universal Zero-Selector Parser.
    Extracts structured quiz questions and choices across Moodle, Canvas, 
    Google Forms, Blackboard, and custom LMS platforms using semantic trees.
    """

    @staticmethod
    async def parse_page(page: Page) -> List[QuizQuestion]:
        """
        Extracts all questions and choices on the current page.
        Combines Accessibility Tree inspection with semantic DOM clustering.
        """
        # Execute an in-page universal semantic extractor that doesn't depend on fragile CSS classes
        extracted_data = await page.evaluate("""() => {
            const questions = [];
            
            // 1. Identify question containers via semantic indicators
            // Standard forms, fieldsets, role='radiogroup', or generic question cards
            const candidates = document.querySelectorAll(
                'fieldset, [role="radiogroup"], [role="group"], .que, div[data-region="question"], div[role="listitem"]'
            );
            
            let idCounter = 1;
            
            // Helper to clean extracted text
            function cleanText(str) {
                if (!str) return '';
                return str.replace(/\\s+/g, ' ').trim();
            }

            // If explicit semantic containers are found, parse them
            const targetContainers = candidates.length > 0 ? Array.from(candidates) : [document.body];
            
            for (const container of targetContainers) {
                // Look for radio or checkbox inputs within this container
                const inputs = Array.from(container.querySelectorAll('input[type="radio"], input[type="checkbox"], [role="radio"]'));
                if (inputs.length === 0) continue;
                
                // Determine container question text
                let questionText = '';
                
                // Try legend or aria-labelledby or heading
                const legend = container.querySelector('legend, [role="heading"], h1, h2, h3, h4, h5, .qtext, .question_text');
                if (legend) {
                    questionText = cleanText(legend.innerText || legend.textContent);
                } else if (container.hasAttribute('aria-label')) {
                    questionText = cleanText(container.getAttribute('aria-label'));
                } else {
                    // Fallback: extract text above the first radio input
                    const firstInput = inputs[0];
                    let prevNode = firstInput.parentElement;
                    while (prevNode && prevNode !== container) {
                        if (prevNode.innerText && prevNode.innerText.length > 10) {
                            questionText = cleanText(prevNode.innerText);
                            break;
                        }
                        prevNode = prevNode.previousElementSibling || prevNode.parentElement;
                    }
                }
                
                if (!questionText || questionText.length < 5) {
                    // Last resort: extract container's text excluding option labels
                    questionText = `Question ${idCounter}`;
                }

                // Clean up question text if it begins with Question metadata
                questionText = questionText.replace(/^Question\\s*\\d+[:.]?\\s*/i, '');

                // Assign or read a unique ID attribute for HUD targeting
                let hostId = container.id;
                if (!hostId) {
                    hostId = `__hypersolve_q_${idCounter}`;
                    container.setAttribute('data-hypersolve-id', hostId);
                }

                // Extract options
                const options = [];
                let isAnswered = false;

                inputs.forEach((input, optIdx) => {
                    let isChecked = false;
                    if (input.tagName === 'INPUT') {
                        isChecked = input.checked;
                    } else if (input.getAttribute('aria-checked') === 'true') {
                        isChecked = true;
                    }
                    if (isChecked) isAnswered = true;

                    // Locate option text
                    let optText = '';
                    let label = null;
                    if (input.id) {
                        label = document.querySelector(`label[for="${input.id}"]`);
                    }
                    if (!label) {
                        label = input.closest('label') || input.parentElement;
                    }

                    if (label) {
                        // Clone label to remove input text itself if nested
                        const clone = label.cloneNode(true);
                        const nestedInput = clone.querySelector('input');
                        if (nestedInput) nestedInput.remove();
                        optText = cleanText(clone.innerText || clone.textContent);
                    }

                    if (!optText) {
                        optText = cleanText(input.getAttribute('aria-label') || input.value || `Option ${optIdx + 1}`);
                    }

                    // Remove leading choice markers like "a. ", "b) ", etc.
                    optText = optText.replace(/^[a-dA-D][.)\\s-]+\\s*/, '').trim();

                    // Tag input for targeted injection
                    const inputMarker = `__hypersolve_opt_${idCounter}_${optIdx}`;
                    input.setAttribute('data-hypersolve-opt', inputMarker);

                    options.push({
                        index: optIdx,
                        text: optText,
                        is_checked: isChecked,
                        ref_id: inputMarker
                    });
                });

                if (options.length > 1) {
                    questions.push({
                        id: idCounter,
                        text: questionText,
                        dom_id: hostId,
                        is_answered: isAnswered,
                        options: options
                    });
                    idCounter++;
                }
            }

            return questions;
        }""")

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
