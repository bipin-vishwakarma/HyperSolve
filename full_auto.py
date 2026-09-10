import asyncio
import re
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from playwright.async_api import async_playwright

QUIZ_TAB_URL_PART = "learn.onlinejain.com/mod/quiz/attempt.php"
QUESTION_CONTAINER = ".que"               
QUESTION_TEXT = ".qtext"                  
OPTION_CONTAINER = ".answer > div"        
OPTION_TEXT = 'div[data-region="answer-label"]' 
RADIO_BUTTON = "input[type='radio']"      

def get_all_target_pages(browser):
    """Find ALL quiz tabs and ALL ChatGPT tabs."""
    quiz_pages = []
    chat_pages = []
    for ctx in browser.contexts:
        for page in ctx.pages:
            if QUIZ_TAB_URL_PART in page.url:
                quiz_pages.append(page)
            elif 'chatgpt.com' in page.url:
                chat_pages.append(page)
    return quiz_pages, chat_pages

async def solve_single_quiz(quiz_page, chat_page, pair_id):
    """Solve a single quiz using one quiz tab and one ChatGPT tab."""
    tag = f"[Pair {pair_id}]"
    print(f"\n{tag} === Starting Quiz Solve ===")
    
    quiz_data = []
    
    # PHASE 1: Scraping Phase
    print(f"{tag} --- Phase 1: Scraping All Questions ---")
    await quiz_page.bring_to_front()
    page_num = 1
    
    while True:
        print(f"{tag} Scraping Page {page_num}...")
        await quiz_page.wait_for_load_state('networkidle')
        try:
            await quiz_page.wait_for_selector(QUESTION_CONTAINER, state='visible', timeout=5000)
        except:
            print(f"{tag} No questions found on this page (might be summary page or slow load).")
            break
            
        question_elements = await quiz_page.locator(QUESTION_CONTAINER).all()
        for q_el in question_elements:
            q_text = await q_el.locator(QUESTION_TEXT).inner_text()
            
            # Check if already answered
            is_answered = False
            options_elements = await q_el.locator(OPTION_CONTAINER).all()
            for opt_el in options_elements:
                radio = opt_el.locator(RADIO_BUTTON)
                if await radio.count() > 0 and await radio.first.is_checked():
                    is_answered = True
                    break
                    
            if is_answered:
                print(f"{tag}   Skipping: {q_text[:30]}... (Already answered)")
                continue
                
            options = []
            for opt_el in options_elements:
                if await opt_el.locator(OPTION_TEXT).count() > 0:
                    opt_text = await opt_el.locator(OPTION_TEXT).inner_text()
                    options.append(opt_text.strip())
                
            quiz_data.append({
                "id": len(quiz_data) + 1,
                "question": q_text.strip(),
                "options": options
            })
            
        # Check for a 'Next' button
        next_btn = quiz_page.locator('input[value*="Next"], button:has-text("Next")').first
        if await next_btn.count() > 0:
            print(f"{tag} Clicking 'Next' to scrape next page...")
            await next_btn.click()
            page_num += 1
        else:
            print(f"{tag} Reached the end of the quiz pages.")
            break
            
    if not quiz_data:
        print(f"{tag} [INFO] No unanswered questions found!")
        return False
        
    # PHASE 2: Ask ChatGPT
    # Dynamic timeout: 60s base + 15s per question
    wait_timeout_ms = (60 + len(quiz_data) * 15) * 1000
    max_attempts = 5
    print(f"\n{tag} --- Phase 2: Asking ChatGPT ({len(quiz_data)} questions) ---")
    print(f"{tag}   Timeout set to {wait_timeout_ms // 1000}s based on {len(quiz_data)} questions")
    prompt = f"Solve this multiple choice quiz containing exactly {len(quiz_data)} questions. Reply ONLY with a valid JSON dictionary where the keys are the question numbers and the values are the EXACT text of the correct option. Ensure your JSON contains exactly {len(quiz_data)} keys. Do not include any other text or markdown formatting outside the JSON block.\n\n"
    for q in quiz_data:
        prompt += f"Question {q['id']}: {q['question']}\nOptions:\n"
        for opt in q['options']:
            prompt += f"- {opt}\n"
        prompt += "\n"
        
    success = False
    answers = {}
    prompt_sent = False
    for attempt in range(max_attempts):
        print(f"{tag} ChatGPT Attempt {attempt+1}/{max_attempts}...")
        await chat_page.bring_to_front()
        
        # On retries, first check if ChatGPT already finished responding
        if prompt_sent:
            print(f"{tag}   Checking if ChatGPT already has a response...")
            await asyncio.sleep(3)
            assistant_messages = await chat_page.locator('[data-message-author-role="assistant"]').all()
            if assistant_messages:
                ai_response = await assistant_messages[-1].inner_text()
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    try:
                        answers = json.loads(json_match.group(0))
                        if len(answers) >= len(quiz_data):
                            print(f"{tag}   [OK] Found valid response from previous attempt!")
                            success = True
                            break
                        else:
                            print(f"{tag}   Previous response only has {len(answers)}/{len(quiz_data)} answers. Re-sending...")
                    except:
                        print(f"{tag}   Previous response has invalid JSON. Re-sending...")
                else:
                    # Maybe it's still generating? Wait for it
                    still_generating = await chat_page.locator('button[aria-label="Stop generating"]').count()
                    if still_generating > 0:
                        print(f"{tag}   ChatGPT is still generating! Waiting...")
                        try:
                            await chat_page.wait_for_selector('button[aria-label="Stop generating"]', state='hidden', timeout=wait_timeout_ms)
                            assistant_messages = await chat_page.locator('[data-message-author-role="assistant"]').all()
                            if assistant_messages:
                                ai_response = await assistant_messages[-1].inner_text()
                                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                                if json_match:
                                    try:
                                        answers = json.loads(json_match.group(0))
                                        if len(answers) >= len(quiz_data):
                                            print(f"{tag}   [OK] Got valid response after waiting!")
                                            success = True
                                            break
                                    except:
                                        pass
                        except:
                            print(f"{tag}   Still timed out. Re-sending prompt...")
        
        # Send the prompt (first time or re-send after failed check)
        try:
            await chat_page.wait_for_selector('#prompt-textarea', state='visible', timeout=10000)
        except:
            print(f"{tag} Could not find prompt-textarea. Is ChatGPT open and logged in?")
            await asyncio.sleep(5)
            continue
            
        print(f"{tag} Injecting massive prompt instantly...")
        await chat_page.fill('#prompt-textarea', prompt)
        await asyncio.sleep(0.5)
        await chat_page.press('#prompt-textarea', 'Enter')
        prompt_sent = True
        
        # Smart waiting for response
        try:
            await chat_page.wait_for_selector('button[aria-label="Stop generating"]', state='visible', timeout=5000)
        except:
            pass
            
        try:
            await chat_page.wait_for_selector('button[aria-label="Stop generating"]', state='hidden', timeout=wait_timeout_ms)
        except:
            print(f"{tag} Timeout after {wait_timeout_ms // 1000}s waiting for ChatGPT.")
            continue  # Next attempt will CHECK first before re-sending
            
        # Scrape response
        assistant_messages = await chat_page.locator('[data-message-author-role="assistant"]').all()
        if not assistant_messages:
            print(f"{tag} No assistant messages found. Retrying...")
            continue
            
        ai_response = await assistant_messages[-1].inner_text()
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            try:
                answers = json.loads(json_match.group(0))
                if len(answers) >= len(quiz_data):
                    success = True
                    break
                else:
                    print(f"{tag} ChatGPT only returned {len(answers)} answers, but we sent {len(quiz_data)}. Retrying...")
            except:
                print(f"{tag} ChatGPT returned invalid JSON. Retrying...")
        else:
            print(f"{tag} ChatGPT did not output JSON. Retrying...")
            
    if not success:
        print(f"\n{tag} [ERROR] Failed to get valid answers from ChatGPT after {max_attempts} attempts.")
        print(f"{tag} Pausing for 30s so you can check ChatGPT, then auto-retrying...")
        await asyncio.sleep(30)
        return False
            
    print(f"{tag} Successfully got all answers from ChatGPT!")
    
    # PHASE 3: Smart Injection
    print(f"\n{tag} --- Phase 3: Injecting Answers ---")
    await quiz_page.bring_to_front()
    
    # Navigate back to page 0 to inject answers from the beginning
    u = urlparse(quiz_page.url)
    q = parse_qs(u.query)
    q['page'] = ['0']
    new_query = urlencode(q, doseq=True)
    new_path = u.path.replace('summary.php', 'attempt.php')
    first_page_url = urlunparse((u.scheme, u.netloc, new_path, u.params, new_query, u.fragment))
    
    print(f"{tag} Navigating back to Page 1...")
    await quiz_page.goto(first_page_url)
    
    answered_count = 0
    page_num = 1
    while True:
        await quiz_page.wait_for_load_state('networkidle')
        try:
            await quiz_page.wait_for_selector(QUESTION_CONTAINER, state='visible', timeout=5000)
        except:
            break
            
        question_elements = await quiz_page.locator(QUESTION_CONTAINER).all()
        for q_el in question_elements:
            q_text = await q_el.locator(QUESTION_TEXT).inner_text()
            
            # Find matching question in our batch
            matching_q = None
            for mq in quiz_data:
                if mq['question'] == q_text.strip():
                    matching_q = mq
                    break
                    
            if matching_q and str(matching_q['id']) in answers:
                correct_option_text = answers[str(matching_q['id'])]
                options_elements = await q_el.locator(OPTION_CONTAINER).all()
                
                for opt_el in options_elements:
                    if await opt_el.locator(OPTION_TEXT).count() > 0:
                        opt_text = await opt_el.locator(OPTION_TEXT).inner_text()
                        if correct_option_text.strip().lower() in opt_text.strip().lower():
                            radio = opt_el.locator(RADIO_BUTTON)
                            if await radio.count() > 0:
                                await radio.first.click(force=True)
                                print(f"{tag}   [INJECTED] Q{matching_q['id']}: {correct_option_text[:40]}...")
                                answered_count += 1
                            break
                            
        # Click next to inject the next page
        next_btn = quiz_page.locator('input[value*="Next"], button:has-text("Next")').first
        if await next_btn.count() > 0:
            await next_btn.click()
            page_num += 1
        else:
            break
            
    print(f"\n{tag} --- ALL PAGES COMPLETED ({answered_count}/{len(quiz_data)} injected) ---")
    return True

async def full_auto_solve():
    print("Starting Fully Automated PARALLEL Quiz Solver...")
    p = await async_playwright().start()
    try:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    except Exception as e:
        print("[ERROR] Could not connect to Chrome! Make sure start_all.bat launched Chrome.")
        return

    # INFINITE LOOP: Never close, keep looking for quizzes
    while True:
        print("\n--- Monitoring Mode ---")
        print("Waiting for Quiz tab(s) and ChatGPT tab(s)...")
        
        while True:
            quiz_pages, chat_pages = get_all_target_pages(browser)
            if quiz_pages and chat_pages:
                break
            await asyncio.sleep(2)
        
        num_quizzes = len(quiz_pages)
        num_chats = len(chat_pages)
        print(f"\n[OK] Found {num_quizzes} Quiz tab(s) and {num_chats} ChatGPT tab(s)!")
        
        # Pair them up: min of quiz tabs and chat tabs
        num_pairs = min(num_quizzes, num_chats)
        if num_quizzes != num_chats:
            print(f"[WARNING] Unequal tabs! Using {num_pairs} pairs (need equal quiz & ChatGPT tabs for full parallel).")
        
        if num_pairs == 1:
            # Single quiz mode — run directly
            print("[MODE] Single Quiz Mode")
            result = await solve_single_quiz(quiz_pages[0], chat_pages[0], 1)
            if result:
                print("\nQuiz finished! Waiting for you to submit or navigate away...")
                while QUIZ_TAB_URL_PART in quiz_pages[0].url:
                    await asyncio.sleep(2)
                print("\nQuiz submitted! Looping back to Monitoring Mode...")
        else:
            # PARALLEL mode — run all pairs simultaneously
            print(f"[MODE] PARALLEL Mode — Solving {num_pairs} quizzes simultaneously!")
            print("=" * 60)
            for i in range(num_pairs):
                print(f"  Pair {i+1}: Quiz [{quiz_pages[i].url[:60]}...] <-> ChatGPT Tab {i+1}")
            print("=" * 60)
            
            # Launch all quiz solvers in parallel
            tasks = []
            for i in range(num_pairs):
                tasks.append(solve_single_quiz(quiz_pages[i], chat_pages[i], i + 1))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Report results
            print("\n" + "=" * 60)
            print("PARALLEL RESULTS:")
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"  Pair {i+1}: CRASHED — {result}")
                elif result:
                    print(f"  Pair {i+1}: SUCCESS ✓")
                else:
                    print(f"  Pair {i+1}: FAILED (no answers or no questions)")
            print("=" * 60)
            
            # Wait for user to submit/navigate away from all quizzes
            print("\nWaiting for you to submit all quizzes...")
            for i in range(num_pairs):
                try:
                    while QUIZ_TAB_URL_PART in quiz_pages[i].url:
                        await asyncio.sleep(2)
                except:
                    pass  # Tab might have been closed
            print("\nAll quizzes done! Looping back to Monitoring Mode...")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(full_auto_solve())
