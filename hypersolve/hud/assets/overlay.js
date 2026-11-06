(() => {
    if (window.top !== window) return;
    const binding = __HYPERSOLVE_BINDING__;
    const generation = __HYPERSOLVE_GENERATION__;
    if (window.__hypersolve_generation && window.__hypersolve_generation > generation) return;
    window.__hypersolve_generation = generation;
    const mount = () => {
        if (window.__hypersolve_generation !== generation) return;
        if (window.__hypersolve?.version === 3 && document.getElementById('__hypersolve_host__')) {
            window.__hypersolve.setControlBinding(binding);
            return;
        }
        document.getElementById('__hypersolve_host__')?.remove();
        const host = document.createElement('div');
        host.id = '__hypersolve_host__';
        host.style.cssText = 'position:fixed;inset:0;z-index:2147483647;pointer-events:none';
        document.documentElement.appendChild(host);
        const root = host.attachShadow({ mode: 'open' });
        const style = document.createElement('style');
        style.textContent = __HYPERSOLVE_CSS__;
        root.appendChild(style);
        const panel = document.createElement('section');
        panel.className = 'panel';
        panel.setAttribute('aria-label', 'HyperSolve session controls');
        panel.innerHTML = `
            <header tabindex="0" aria-label="Move overlay with arrow keys or drag">
                <span class="brand"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><rect x="3" y="5" width="17" height="15" rx="3"/><path d="M7 5V3h14v14M7 13l3 3 6-6"/></svg>HyperSolve</span>
                <button type="button" class="collapse" aria-expanded="true">Collapse</button>
            </header>
            <div class="status">
                <div class="phase-row"><span class="phase" aria-live="polite">Preparing</span><span class="elapsed">0:00</span></div>
                <div class="message" role="status">Connecting session controls…</div>
                <ol class="steps"><li data-step="harvest">Read</li><li data-step="solve">Solve</li><li data-step="select">Select</li></ol>
                <progress max="1" value="0" aria-label="Session progress"></progress>
                <div class="counts">Waiting for questions</div>
                <div class="provider"></div>
            </div>
            <div class="body">
                <div class="question"></div>
                <ul class="answers" aria-label="Selected answers"></ul>
                <div class="tools"><button type="button" class="focus">Show question</button><button type="button" class="copy" disabled>Copy answers</button></div>
                <details><summary>Activity</summary><ol class="log"></ol></details>
                <div class="hint">Pause holds the next page action. An AI request already sent may finish.</div>
            </div>
            <div class="controls"><button type="button" class="pause">Pause</button><button type="button" class="stop">Stop</button></div>`;
        root.appendChild(panel);
        const $ = selector => panel.querySelector(selector);
        let controlBinding = binding;
        let state;
        const initial = () => ({ status: 'Preparing', done: 0, total: 0, found: 0, brain: '', paused: false, stopped: false, disconnected: false, error: '', question: '', domId: '', answers: [], log: [], started: Date.now(), ended: null });
        const read = key => { try { return JSON.parse(sessionStorage.getItem(key)); } catch { return null; } };
        const store = (key, value) => { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch {} };
        state = Object.assign(initial(), read('__hs_panel_state') || {});
        if (!Array.isArray(state.answers)) state.answers = [];
        if (!Array.isArray(state.log)) state.log = [];
        const layout = read('__hs_panel_layout') || {};
        const position = (left, top) => {
            const maxLeft = Math.max(8, innerWidth - panel.offsetWidth - 8);
            const maxTop = Math.max(8, innerHeight - panel.offsetHeight - 8);
            panel.style.left = `${Math.min(maxLeft, Math.max(8, Number(left) || 8))}px`;
            panel.style.top = `${Math.min(maxTop, Math.max(8, Number(top) || 8))}px`;
            panel.style.right = 'auto';
            store('__hs_panel_layout', { left: parseFloat(panel.style.left), top: parseFloat(panel.style.top), compact: panel.classList.contains('compact') });
        };
        const elapsed = () => {
            const seconds = Math.max(0, Math.floor(((state.ended || Date.now()) - state.started) / 1000));
            $('.elapsed').textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
        };
        const record = text => {
            if (state.log.at(-1) !== text) state.log.push(text);
            state.log = state.log.slice(-20);
        };
        const render = () => {
            const harvest = /SURVEY|HARVEST/.test(state.status);
            const solve = /AI|SOLV/.test(state.status) && !state.error;
            const complete = /COMPLETE/.test(state.status);
            $('.phase').textContent = state.paused ? 'Paused' : state.error ? 'Needs attention' : state.stopped ? (complete ? 'Completed' : 'Stopped') : harvest ? 'Harvesting questions' : solve ? 'Solving' : complete ? 'Completed' : /INJECT|SELECT/.test(state.status) ? 'Selecting answers' : state.status;
            const page = /P\.(\d+)/.exec(state.status);
            $('.message').textContent = state.error || (state.paused ? 'No further page actions until you resume.' : state.stopped ? (complete ? 'Review the selected answers in your browser.' : 'Session stopped. Your page has been left open.') : harvest ? `Reading ${page ? 'page ' + page[1] : 'questions'} from this quiz.` : solve ? 'Waiting for the AI response…' : complete ? 'Review the selected answers in your browser.' : 'Session is running on this tab.');
            $('.counts').textContent = harvest ? `${state.found} question${state.found === 1 ? '' : 's'} found` : `${state.done} of ${state.total} answers selected`;
            $('.provider').textContent = state.brain ? `Provider: ${state.brain}` : '';
            const progress = $('progress');
            progress.max = Math.max(1, state.total);
            if ((solve || harvest) && !state.stopped && !state.paused) progress.removeAttribute('value');
            else progress.value = Math.min(state.done, progress.max);
            for (const step of panel.querySelectorAll('[data-step]')) {
                if (step.dataset.step === (harvest ? 'harvest' : solve ? 'solve' : 'select')) step.setAttribute('aria-current', 'step');
                else step.removeAttribute('aria-current');
            }
            $('.question').textContent = state.question;
            $('.answers').replaceChildren(...state.answers.map(answer => {
                const row = document.createElement('li');
                const number = document.createElement('strong');
                number.textContent = `Q${answer.id}`;
                row.append(number, document.createTextNode(answer.text));
                return row;
            }));
            $('.log').replaceChildren(...state.log.map(text => { const item = document.createElement('li'); item.textContent = text; return item; }));
            $('.pause').textContent = state.paused ? 'Resume' : 'Pause';
            $('.pause').disabled = state.stopped || state.disconnected;
            $('.stop').disabled = state.stopped || state.disconnected;
            $('.copy').disabled = !state.answers.length;
            $('.focus').disabled = !state.domId;
            panel.classList.toggle('error', !!state.error);
            store('__hs_panel_state', state);
            elapsed();
        };
        const act = async action => {
            if (state.stopped || state.disconnected) return;
            try {
                if (typeof window[controlBinding] !== 'function') throw new Error('Session is no longer connected');
                const result = await window[controlBinding](action);
                if (!result?.accepted) throw new Error('Control handler is no longer active');
                if (action === 'stop') { state.stopped = true; state.paused = false; state.ended = Date.now(); record('Stopped'); render(); }
            } catch {
                if (state.stopped) return;
                state.disconnected = true;
                state.error = 'Control request could not be confirmed. Use Stop in the desktop app.';
                render();
            }
        };
        $('.pause').addEventListener('click', () => act(state.paused ? 'resume' : 'pause'));
        $('.stop').addEventListener('click', () => act('stop'));
        const setCompact = compact => {
            panel.classList.toggle('compact', compact);
            $('.collapse').textContent = compact ? 'Expand' : 'Collapse';
            $('.collapse').setAttribute('aria-expanded', String(!compact));
            const rect = panel.getBoundingClientRect();
            position(rect.left, rect.top);
        };
        $('.collapse').addEventListener('click', () => setCompact(!panel.classList.contains('compact')));
        $('.focus').addEventListener('click', () => {
            const question = [...document.querySelectorAll('[data-hypersolve-id]')].find(el => el.getAttribute('data-hypersolve-id') === state.domId);
            if (question) question.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
            else $('.message').textContent = 'That question is on another page. Return to it in the browser.';
        });
        $('.copy').addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(state.answers.map(answer => `Q${answer.id}: ${answer.text}`).join('\n'));
                $('.copy').textContent = 'Copied';
            } catch { $('.copy').textContent = 'Select answer text to copy'; }
        });
        const header = $('header');
        let drag;
        header.addEventListener('pointerdown', event => {
            if (event.target.closest('button')) return;
            const rect = panel.getBoundingClientRect();
            drag = { x: event.clientX - rect.left, y: event.clientY - rect.top };
            header.setPointerCapture(event.pointerId);
        });
        header.addEventListener('pointermove', event => { if (drag) position(event.clientX - drag.x, event.clientY - drag.y); });
        header.addEventListener('pointerup', () => { drag = null; });
        header.addEventListener('pointercancel', () => { drag = null; });
        header.addEventListener('keydown', event => {
            if (event.target !== header || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
            event.preventDefault();
            const rect = panel.getBoundingClientRect();
            const amount = event.shiftKey ? 24 : 8;
            position(rect.left + (event.key === 'ArrowLeft' ? -amount : event.key === 'ArrowRight' ? amount : 0), rect.top + (event.key === 'ArrowUp' ? -amount : event.key === 'ArrowDown' ? amount : 0));
        });
        addEventListener('resize', () => { const rect = panel.getBoundingClientRect(); position(rect.left, rect.top); });
        window.__hypersolve = {
            version: 3,
            setControlBinding: value => { controlBinding = value; },
            reset: () => { state = initial(); $('.copy').textContent = 'Copy answers'; setCompact(false); render(); },
            updateStats: (done, total, status, brain = '') => {
                state.status = String(status); state.done = done; state.total = total; state.brain = brain;
                if (/SURVEY|HARVEST/.test(state.status)) state.found = done;
                record(state.status); render();
            },
            setPaused: value => { state.paused = value; record(value ? 'Paused' : 'Resumed'); render(); },
            finish: error => { state.stopped = true; state.paused = false; state.error = error || ''; state.ended = Date.now(); record(error || (/COMPLETE/.test(state.status) ? 'Completed' : 'Stopped')); render(); },
            startScan: domId => {
                state.domId = domId;
                const question = [...document.querySelectorAll('[data-hypersolve-id]')].find(el => el.getAttribute('data-hypersolve-id') === domId);
                state.question = question?.querySelector('.qtext, .question_text, legend, h1, h2, h3, p')?.textContent?.trim() || '';
                render();
            },
            lockAnswer: (domId, marker, confidence, brain, questionId, answerText) => {
                state.domId = domId; state.brain = brain || '';
                const option = [...document.querySelectorAll('[data-hypersolve-opt]')].find(el => el.getAttribute('data-hypersolve-opt') === marker);
                const id = questionId || domId;
                const answer = { id, text: answerText || option?.textContent?.trim() || 'Selected option' };
                const index = state.answers.findIndex(row => row.id === id);
                if (index < 0) state.answers.push(answer); else state.answers[index] = answer;
                render();
            },
        };
        if (Number.isFinite(layout.left) && Number.isFinite(layout.top)) position(layout.left, layout.top);
        if (layout.compact) setCompact(true);
        render();
        new ResizeObserver(() => { const rect = panel.getBoundingClientRect(); position(rect.left, rect.top); }).observe(panel);
        setInterval(elapsed, 1000);
    };
    if (document.documentElement) mount();
    else document.addEventListener('DOMContentLoaded', mount, { once: true });
})();
