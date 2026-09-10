(() => {
    // Prevent duplicate injection
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
            font-family: 'JetBrains Mono', 'Segoe UI', 'Consolas', monospace;
            font-size: 13px;
            color: #e0f7fa;
            pointer-events: none;
            z-index: 2147483647;
        }
        .hypersolve-dock {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(10, 14, 23, 0.94);
            border: 1px solid #00f3ff;
            box-shadow: 0 0 16px rgba(0, 243, 255, 0.45), inset 0 0 12px rgba(0, 243, 255, 0.15);
            border-radius: 8px;
            padding: 12px 16px;
            width: 250px;
            pointer-events: auto;
            backdrop-filter: blur(8px);
            transition: transform 0.25s ease, opacity 0.25s ease;
            user-select: none;
            z-index: 2147483647;
        }
        .hypersolve-dock.vanished {
            opacity: 0;
            transform: translateY(-20px) scale(0.95);
            pointer-events: none;
        }
        .dock-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(0, 243, 255, 0.3);
            padding-bottom: 6px;
            margin-bottom: 8px;
        }
        .dock-title {
            font-weight: 700;
            letter-spacing: 1.5px;
            color: #00f3ff;
            text-shadow: 0 0 8px #00f3ff;
            font-size: 13px;
        }
        .dock-badge {
            background: rgba(5, 255, 161, 0.15);
            border: 1px solid #05ffa1;
            color: #05ffa1;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .dock-stats {
            display: flex;
            flex-direction: column;
            gap: 5px;
            font-size: 11px;
            color: #90caf9;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
        }
        .stat-val {
            color: #ffffff;
            font-weight: 600;
        }
        .dock-footer {
            margin-top: 8px;
            font-size: 9px;
            color: #546e7a;
            display: flex;
            justify-content: space-between;
        }
        .hotkey-tag {
            color: #00f3ff;
            font-weight: 600;
        }
    `;
    shadow.appendChild(styleEl);

    // 4. Build Floating Dock Element
    const dock = document.createElement('div');
    dock.className = 'hypersolve-dock';
    dock.innerHTML = `
        <div class="dock-header">
            <span class="dock-title">⚡ HYPERSOLVE</span>
            <span class="dock-badge" id="hs-status">ACTIVE</span>
        </div>
        <div class="dock-stats">
            <div class="stat-row">
                <span>Progress:</span>
                <span class="stat-val" id="hs-progress">0 / 0</span>
            </div>
            <div class="stat-row">
                <span>Active Brain:</span>
                <span class="stat-val" id="hs-brain">Neural Router</span>
            </div>
            <div class="stat-row">
                <span>Stealth Mode:</span>
                <span class="stat-val" style="color:#05ffa1;">ARMORED</span>
            </div>
        </div>
        <div class="dock-footer">
            <span>Panic Toggle:</span>
            <span class="hotkey-tag">Ctrl + Shift + X</span>
        </div>
    `;
    shadow.appendChild(dock);

    // 5. Global Hotkey for Instant Stealth Vanish (Ctrl + Shift + X)
    let isVanished = false;
    window.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && e.code === 'KeyX') {
            isVanished = !isVanished;
            if (isVanished) {
                dock.classList.add('vanished');
                // Remove visual badges and beams from DOM
                document.querySelectorAll('.hypersolve-scanline-beam, .hypersolve-confidence-pill').forEach(el => el.style.display = 'none');
            } else {
                dock.classList.remove('vanished');
                document.querySelectorAll('.hypersolve-scanline-beam, .hypersolve-confidence-pill').forEach(el => el.style.display = '');
            }
        }
    }, true);

    // 6. Public Control Interface on Window (called via Playwright evaluate)
    window.__hypersolve = {
        updateStats: (solved, total, status = 'ACTIVE', brain = 'ChatGPT-4o') => {
            const p = shadow.getElementById('hs-progress');
            const s = shadow.getElementById('hs-status');
            const b = shadow.getElementById('hs-brain');
            if (p) p.textContent = `${solved} / ${total}`;
            if (s) s.textContent = status;
            if (b) b.textContent = brain;
        },

        startScan: (domId) => {
            if (isVanished) return;
            const container = document.getElementById(domId) || document.querySelector(`[data-hypersolve-id="${domId}"]`);
            if (!container) return;

            container.classList.add('hypersolve-scanline-active');
            let beam = container.querySelector('.hypersolve-scanline-beam');
            if (!beam) {
                beam = document.createElement('div');
                beam.className = 'hypersolve-scanline-beam';
                container.style.position = 'relative';
                container.appendChild(beam);
            }
        },

        lockAnswer: (domId, optMarker, confidence = 98.4, brain = 'DeepSeek-R1') => {
            if (isVanished) return;
            const container = document.getElementById(domId) || document.querySelector(`[data-hypersolve-id="${domId}"]`);
            if (container) {
                // Remove beam
                const beam = container.querySelector('.hypersolve-scanline-beam');
                if (beam) beam.remove();
                container.classList.remove('hypersolve-scanline-active');

                // Inject floating confidence pill if not present
                if (!container.querySelector('.hypersolve-confidence-pill')) {
                    const pill = document.createElement('div');
                    pill.className = 'hypersolve-confidence-pill';
                    pill.innerHTML = `⚡ ${confidence}% Confidence • ${brain}`;
                    container.insertBefore(pill, container.firstChild);
                }
            }

            // Highlight choice
            const targetInput = document.querySelector(`[data-hypersolve-opt="${optMarker}"]`);
            if (targetInput) {
                const choiceWrapper = targetInput.closest('label') || targetInput.parentElement;
                if (choiceWrapper) {
                    choiceWrapper.classList.add('hypersolve-choice-locked');
                }
            }
        }
    };
})();
