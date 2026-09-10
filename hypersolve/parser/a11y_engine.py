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
    Multi-Strategy Universal Question Detector.
    Uses targeted platform adapters (Moodle, Canvas, Aspirations, Google Forms)
    backed by semantic DOM clustering for 100% reliable detection.
    """

    @staticmethod
    async def parse_page(page: Page) -> List[QuizQuestion]:
        """
        Extracts questions and choices with deterministic accuracy.
        """
        extracted_data = await page.evaluate(r"""() => {
            const questions = [];

            function clean(s) {
                return (s || '').replace(/\s+/g, ' ').trim();
            }

            function stripChoicePrefix(s) {
                // Strips "A\n", "A.", "1.", "(A)", "A) "
                return s.replace(/^(\([A-Za-z0-9]\)|[A-Za-z0-9][.)\-:]+)\s*/i, '').trim();
            }

            function stripQuestionPrefix(s) {
                // Strips "Q1 / 25", "Question 1:", "1. "
                return s.replace(/^(Q\s*\d+\s*[\/:.]?\s*\d*|Question\s*\d+[:.]?|\d+[.)])\s*/i, '').trim();
            }

            // =========================================================
            // STRATEGY 1: Targeted Platform Adapters (100% Deterministic)
            // =========================================================

            // A. Aspirations Institute / QCard Portals
            const qcardContainers = Array.from(document.querySelectorAll('section.qcard, .qcard, div.qcard')).filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
            });

            if (qcardContainers.length > 0) {
                let qId = 1;
                for (const card of qcardContainers) {
                    const qTextEl = card.querySelector('.qtext, .question_text, [class*="qtext"]');
                    const qText = qTextEl ? clean(qTextEl.innerText) : '';
                    if (!qText) continue;

                    const optEls = Array.from(card.querySelectorAll('.opt, [role="radio"], [class*="opt-"]')).filter(el => {
                        const r = el.getBoundingClientRect();
                        return r.width > 0 && r.height > 0;
                    });

                    if (optEls.length < 2) continue;

                    let isAnswered = false;
                    const options = [];

                    optEls.forEach((optEl, idx) => {
                        const isChecked = optEl.getAttribute('aria-checked') === 'true' ||
                                          optEl.classList.contains('sel') ||
                                          optEl.classList.contains('selected') ||
                                          optEl.classList.contains('checked');
                        if (isChecked) isAnswered = true;

                        const rawText = clean(optEl.innerText || optEl.textContent);
                        const cleanedText = stripChoicePrefix(rawText) || rawText;
                        const refId = `__hypersolve_opt_${qId}_${idx}`;
                        optEl.setAttribute('data-hypersolve-opt', refId);

                        options.push({
                            index: idx,
                            text: cleanedText,
                            is_checked: isChecked,
                            ref_id: refId
                        });
                    });

                    let domId = card.getAttribute('data-hypersolve-id');
                    if (!domId) {
                        domId = `__hypersolve_q_${qId}`;
                        card.setAttribute('data-hypersolve-id', domId);
                    }

                    questions.push({
                        id: qId++,
                        text: stripQuestionPrefix(qText),
                        dom_id: domId,
                        is_answered: isAnswered,
                        options: options
                    });
                }

                if (questions.length > 0) return questions;
            }

            // B. Moodle / Jain Online / Coursera LMS
            const moodleContainers = Array.from(document.querySelectorAll('.que')).filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
            });

            if (moodleContainers.length > 0) {
                let qId = 1;
                for (const container of moodleContainers) {
                    const qTextEl = container.querySelector('.qtext');
                    const qText = qTextEl ? clean(qTextEl.innerText) : '';
                    if (!qText) continue;

                    const inputs = Array.from(container.querySelectorAll('input[type="radio"], input[type="checkbox"]'));
                    if (inputs.length < 2) continue;

                    let isAnswered = false;
                    const options = [];

                    inputs.forEach((input, idx) => {
                        const isChecked = input.checked;
                        if (isChecked) isAnswered = true;

                        let label = null;
                        if (input.id) label = document.querySelector(`label[for="${input.id}"]`);
                        if (!label) label = input.closest('label') || input.parentElement;

                        let optText = '';
                        if (label) {
                            const clone = label.cloneNode(true);
                            const nested = clone.querySelector('input');
                            if (nested) nested.remove();
                            optText = clean(clone.innerText || clone.textContent);
                        } else {
                            optText = clean(input.value);
                        }

                        const cleanedText = stripChoicePrefix(optText) || optText;
                        const refId = `__hypersolve_opt_${qId}_${idx}`;
                        input.setAttribute('data-hypersolve-opt', refId);

                        options.push({
                            index: idx,
                            text: cleanedText,
                            is_checked: isChecked,
                            ref_id: refId
                        });
                    });

                    let domId = container.getAttribute('data-hypersolve-id') || `__hypersolve_q_${qId}`;
                    container.setAttribute('data-hypersolve-id', domId);

                    questions.push({
                        id: qId++,
                        text: stripQuestionPrefix(qText),
                        dom_id: domId,
                        is_answered: isAnswered,
                        options: options
                    });
                }

                if (questions.length > 0) return questions;
            }

            // C. Google Forms
            const formItems = Array.from(document.querySelectorAll('div[role="listitem"]')).filter(el => {
                return el.querySelector('div[role="radiogroup"], div[role="radio"], div[role="checkbox"]');
            });

            if (formItems.length > 0) {
                let qId = 1;
                for (const item of formItems) {
                    const heading = item.querySelector('div[role="heading"], div[dir="auto"]');
                    const qText = heading ? clean(heading.innerText) : '';
                    if (!qText) continue;

                    const radios = Array.from(item.querySelectorAll('div[role="radio"], div[role="checkbox"]'));
                    if (radios.length < 2) continue;

                    let isAnswered = false;
                    const options = [];

                    radios.forEach((r, idx) => {
                        const isChecked = r.getAttribute('aria-checked') === 'true';
                        if (isChecked) isAnswered = true;

                        const rawText = clean(r.getAttribute('aria-label') || r.innerText);
                        const cleanedText = stripChoicePrefix(rawText) || rawText;
                        const refId = `__hypersolve_opt_${qId}_${idx}`;
                        r.setAttribute('data-hypersolve-opt', refId);

                        options.push({
                            index: idx,
                            text: cleanedText,
                            is_checked: isChecked,
                            ref_id: refId
                        });
                    });

                    let domId = item.getAttribute('data-hypersolve-id') || `__hypersolve_q_${qId}`;
                    item.setAttribute('data-hypersolve-id', domId);

                    questions.push({
                        id: qId++,
                        text: stripQuestionPrefix(qText),
                        dom_id: domId,
                        is_answered: isAnswered,
                        options: options
                    });
                }

                if (questions.length > 0) return questions;
            }

            // =========================================================
            // STRATEGY 3: Universal Structural Fallback (For Any Other Site)
            // =========================================================
            const allRadios = Array.from(document.querySelectorAll(
                'input[type="radio"], [role="radio"], .opt, [class*="option-item"], [class*="choice"]'
            )).filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
            });

            if (allRadios.length === 0) return [];

            const containerMap = new Map();
            for (const r of allRadios) {
                const container = r.closest('section, fieldset, [role="radiogroup"], div.question, div[class*="card"], div[class*="question"]') || r.parentElement.parentElement;
                if (!containerMap.has(container)) {
                    containerMap.set(container, []);
                }
                containerMap.get(container).push(r);
            }

            let fallbackId = 1;
            for (const [container, inputs] of containerMap.entries()) {
                if (inputs.length < 2) continue;

                // Grab prompt directly above first input
                const firstInput = inputs[0];
                let qText = '';
                const headingEl = container.querySelector('h1, h2, h3, h4, h5, [role="heading"], legend, p, strong');
                if (headingEl && clean(headingEl.innerText).length > 5) {
                    qText = clean(headingEl.innerText);
                } else {
                    qText = `Question ${fallbackId}`;
                }

                let isAnswered = false;
                const options = [];

                inputs.forEach((input, idx) => {
                    let isChecked = false;
                    if (input.tagName === 'INPUT') isChecked = input.checked;
                    else isChecked = input.getAttribute('aria-checked') === 'true' || input.classList.contains('sel') || input.classList.contains('selected');
                    if (isChecked) isAnswered = true;

                    const rawText = clean(input.innerText || input.textContent);
                    const cleanedText = stripChoicePrefix(rawText) || rawText;
                    const refId = `__hypersolve_opt_${fallbackId}_${idx}`;
                    input.setAttribute('data-hypersolve-opt', refId);

                    options.push({
                        index: idx,
                        text: cleanedText,
                        is_checked: isChecked,
                        ref_id: refId
                    });
                });

                let domId = container.getAttribute('data-hypersolve-id') || `__hypersolve_q_${fallbackId}`;
                container.setAttribute('data-hypersolve-id', domId);

                questions.push({
                    id: fallbackId++,
                    text: stripQuestionPrefix(qText),
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
