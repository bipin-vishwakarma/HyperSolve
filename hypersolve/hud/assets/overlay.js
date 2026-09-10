(() => {
    if (window.__hypersolve_initialized) return;
    window.__hypersolve_initialized = true;

    // 1. Create Host Element
    const host = document.createElement('div');
    host.id = '__hypersolve_host__';
    document.documentElement.appendChild(host);

    // 2. Attach Closed Shadow Root for 100% Anti-Detection Isolation
    const shadow = host.attachShadow({ mode: 'closed' });

    // 3. Inject Scoped Stylesheet into Shadow Root
    const styleEl = document.createElement('style');
    styleEl.textContent = `
        :host {
            all: initial;
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            font-size: 12px;
            color: #f1f5f9;
            pointer-events: none;
            z-index: 2147483647;
        }
        .hypersolve-island {
            position: fixed;
            top: 14px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(13, 17, 23, 0.88);
            border: 1px solid rgba(255, 255, 255, 0.14);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05);
            border-radius: 9999px;
            padding: 5px 14px;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            pointer-events: auto;
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            user-select: none;
            z-index: 2147483647;
        }
        .hypersolve-island.vanished {
            opacity: 0;
            transform: translateX(-50%) translateY(-24px) scale(0.9);
            pointer-events: none;
        }
        .island-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 8px #10b981;
            animation: pulse-dot 2s infinite ease-in-out;
        }
        @keyframes pulse-dot {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 12px #10b981; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }
        .island-title {
            font-weight: 600;
            letter-spacing: 0.3px;
            color: #ffffff;
            font-size: 11.5px;
        }
        .island-sep {
            width: 1px;
            height: 12px;
            background: rgba(255, 255, 255, 0.18);
        }
        .island-info {
            color: #94a3b8;
            font-size: 11px;
            font-weight: 500;
        }
        .island-info strong {
            color: #38bdf8;
        }
        .island-badge {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.35);
            color: #34d399;
            font-size: 10px;
            font-weight: 600;
            padding: 1px 7px;
            border-radius: 9999px;
            text-transform: uppercase;
        }
    `;
    shadow.appendChild(styleEl);

    // 4. Build Minimalist Dynamic Island Pill
    const island = document.createElement('div');
    island.className = 'hypersolve-island';
    island.innerHTML = `
        <div class="island-dot" id="hs-dot"></div>
        <span class="island-title">⚡ HyperSolve</span>
        <div class="island-sep"></div>
        <span class="island-info" id="hs-info">Monitoring</span>
        <div class="island-sep"></div>
        <span class="island-badge" id="hs-badge">ARMORED</span>
    `;
    shadow.appendChild(island);

    // 5. Global Hotkey for Instant Stealth Vanish (Ctrl + Shift + X)
    let isVanished = false;
    window.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && e.code === 'KeyX') {
            isVanished = !isVanished;
            if (isVanished) {
                island.classList.add('vanished');
                document.querySelectorAll('.hypersolve-choice-locked, .hypersolve-confidence-pill').forEach(el => el.style.display = 'none');
            } else {
                island.classList.remove('vanished');
                document.querySelectorAll('.hypersolve-choice-locked, .hypersolve-confidence-pill').forEach(el => el.style.display = '');
            }
        }
    }, true);

    // 6. Public Control Interface on Window (called via Playwright evaluate)
    window.__hypersolve = {
        updateStats: (solved, total, status = 'ACTIVE', brain = 'ChatGPT-4o') => {
            const info = shadow.getElementById('hs-info');
            const badge = shadow.getElementById('hs-badge');
            const dot = shadow.getElementById('hs-dot');
            if (info) {
                if (total > 0) {
                    info.innerHTML = `Q <strong>${solved}</strong> of <strong>${total}</strong> • ${status}`;
                } else {
                    info.innerHTML = `${status}`;
                }
            }
            if (badge) badge.textContent = brain ? brain.split('-')[0] : 'ACTIVE';
            if (dot) {
                if (status === 'COMPLETED') dot.style.background = '#38bdf8';
                else if (status.includes('RETRY') || status.includes('ERR')) dot.style.background = '#f59e0b';
                else dot.style.background = '#10b981';
            }
        },

        startScan: (domId) => {
            // Non-intrusive: subtle indicator
        },

        lockAnswer: (domId, optMarker, confidence = 98.4, brain = 'ChatGPT-4o') => {
            if (isVanished) return;
            const targetInput = document.querySelector(`[data-hypersolve-opt="${optMarker}"]`);
            if (targetInput) {
                const choiceWrapper = targetInput.closest('label') || targetInput;
                if (choiceWrapper) {
                    choiceWrapper.classList.add('hypersolve-choice-locked');
                }
            }
        }
    };
})();
