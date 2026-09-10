import re
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
    Universal Zero-Selector Parser.
    Extracts structured quiz questions across Moodle, Canvas, Blackboard,
    Google Forms, Aspirations Institute, and custom portal DOM trees.
    """

    @staticmethod
    async def parse_page(page: Page) -> List[QuizQuestion]:
        """
        Extracts questions and choices using intelligent container grouping
        and semantic radio/option extraction without relying on brittle class names.
        """
        extracted_data = await page.evaluate(r"""() => {
            const questions = [];

            // 1. Gather all choice elements: inputs or custom divs with role='radio' or .opt
            const allRadios = Array.from(document.querySelectorAll(
                'input[type="radio"], input[type="checkbox"], [role="radio"], .opt, [class*="option-item"]'
            )).filter(el => {
                // Filter out invisible elements
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
            });

            if (allRadios.length === 0) return [];

            // 2. Group options by their parent question card or container
            const containerMap = new Map();
            for (const r of allRadios) {
                const container = r.closest(
                    'section.qcard, .qcard, .que, fieldset, [role="radiogroup"], [role="group"], div.question, div[data-region="question"]'
                ) || r.parentElement.parentElement;

                if (!containerMap.has(container)) {
                    containerMap.set(container, []);
                }
                containerMap.get(container).push(r);
            }

            function cleanText(str) {
                if (!str) return '';
                return str.replace(/\s+/g, ' ').trim();
            }

            let qId = 1;
            for (const [container, inputs] of containerMap.entries()) {
                if (inputs.length < 2) continue; // Not a multiple choice group

                // A. Extract question text
                let qText = '';
                const qTextEl = container.querySelector(
                    '.qtext, .question_text, legend, h1, h2, h3, h4, [role="heading"], .prompt'
                );

                if (qTextEl && cleanText(qTextEl.innerText).length > 5) {
                    qText = cleanText(qTextEl.innerText);
                } else {
                    // Fallback: examine text in container before the first option
                    const firstInput = inputs[0];
                    let textParts = [];
                    for (const node of container.childNodes) {
                        if (node.contains && node.contains(firstInput)) break;
                        if (node.innerText) textParts.push(cleanText(node.innerText));
                        else if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                            textParts.push(cleanText(node.textContent));
                        }
                    }
                    qText = textParts.join(' ').trim();
                }

                if (!qText || qText.length < 4) {
                    qText = `Question ${qId}`;
                }

                // Strip question numbering prefixes like "Q1 / 25", "1. ", "Question 1:"
                qText = qText.replace(/^(Q\s*\d+\s*[\/:.]?\s*\d*|Question\s*\d+[:.]?|\d+[.)])\s*/i, '').trim();

                // Tag container for visual HUD scanline beam
                let domId = container.getAttribute('data-hypersolve-id');
                if (!domId) {
                    domId = `__hypersolve_q_${qId}`;
                    container.setAttribute('data-hypersolve-id', domId);
                }

                // B. Extract options
                const options = [];
                let isAnswered = false;

                inputs.forEach((input, idx) => {
                    let isChecked = false;
                    if (input.tagName === 'INPUT') {
                        isChecked = input.checked;
                    } else {
                        isChecked = input.getAttribute('aria-checked') === 'true' ||
                                    input.classList.contains('sel') ||
                                    input.classList.contains('selected') ||
                                    input.classList.contains('checked');
                    }
                    if (isChecked) isAnswered = true;

                    // Option text extraction
                    let optText = '';
                    if (input.tagName === 'INPUT') {
                        let label = null;
                        if (input.id) label = document.querySelector(`label[for="${input.id}"]`);
                        if (!label) label = input.closest('label') || input.parentElement;
                        if (label) {
                            const clone = label.cloneNode(true);
                            const nested = clone.querySelector('input');
                            if (nested) nested.remove();
                            optText = cleanText(clone.innerText || clone.textContent);
                        }
                    } else {
                        // Custom div or span option
                        optText = cleanText(input.innerText || input.textContent);
                    }

                    // Clean choice markers like "A\nbecause" or "A. because" or "(A) because"
                    let cleanedOpt = optText.replace(/^(\([A-Za-z0-9]\)|[A-Za-z0-9][.)\-:]+)\s*/i, '').trim();
                    if (!cleanedOpt) cleanedOpt = optText;

                    // Tag input for targeted injection
                    const refId = `__hypersolve_opt_${qId}_${idx}`;
                    input.setAttribute('data-hypersolve-opt', refId);

                    options.push({
                        index: idx,
                        text: cleanedOpt,
                        is_checked: isChecked,
                        ref_id: refId
                    });
                });

                questions.push({
                    id: qId++,
                    text: qText,
                    dom_id: domId,
                    is_answered: isAnswered,
                    options: options
                });
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
