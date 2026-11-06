/* HyperSolve's non-modal glass panel. All page/model strings use textContent. */
(() => {
  if (window.top !== window) return;
  globalThis.HyperSolvePanel = function(onAction) {
    document.getElementById('__hypersolve_companion__')?.remove();
    const host = document.createElement('div'); host.id = '__hypersolve_companion__';
    host.style.cssText = 'position:fixed;inset:0;z-index:2147483647;pointer-events:none';
    document.documentElement.append(host);
    const shadow = host.attachShadow({mode:'open'});
    const style = document.createElement('style');
    style.textContent = `
      :host{all:initial;font:13px/1.5 "Segoe UI",system-ui,sans-serif;color:#202941;color-scheme:light}
      *{box-sizing:border-box}button,summary{-webkit-tap-highlight-color:transparent}
      .panel{position:fixed;top:20px;right:20px;width:min(360px,calc(100vw - 24px));max-height:calc(100vh - 24px);overflow:auto;pointer-events:auto;border:1px solid #ffffffcc;border-radius:20px;background:linear-gradient(135deg,#fffffff2,#edf2ffde);backdrop-filter:blur(24px) saturate(140%);box-shadow:0 12px 40px #192b4b26;animation:arrive 180ms cubic-bezier(.23,1,.32,1)}
      @keyframes arrive{from{opacity:0;transform:translateY(-6px) scale(.98)}to{opacity:1;transform:none}}
      header{padding:14px 16px;display:flex;align-items:center;gap:9px;cursor:grab;touch-action:none;user-select:none}
      header svg{color:#3759dc;flex:none}.brand{font-weight:650;font-size:15px;flex:1}.collapse{background:transparent!important;padding:5px 8px!important}
      button{font:600 12px/1.3 "Segoe UI",system-ui,sans-serif;cursor:pointer;border:1px solid #bbc7e3;background:#ffffffa6;color:#314365;border-radius:9px;padding:10px 12px;transition:background 140ms ease,transform 120ms ease}
      button:hover{background:#e4ebff}button:active{transform:scale(.98)}button:disabled{opacity:.55;cursor:default;transform:none}
      button:focus-visible,header:focus-visible,summary:focus-visible{outline:2px solid #3759dc;outline-offset:3px}
      .primary{background:#3759dc!important;color:white;border-color:#3759dc}.primary:hover{background:#2945b5!important}
      .body{padding:0 18px 16px}.phase{font-size:20px;font-weight:650;letter-spacing:-.4px}.detail{color:#586986;overflow-wrap:anywhere;margin:5px 0 12px}.count{font-size:12px;color:#586986;margin:6px 0}
      progress{width:100%;height:5px;accent-color:#3759dc;border:0}progress::-webkit-progress-bar{background:#dbe3f5;border-radius:4px}progress::-webkit-progress-value{background:#3759dc;border-radius:4px}
      .question{font-weight:600;margin:12px 0 5px;max-height:70px;overflow:auto;overflow-wrap:anywhere}
      .answers{max-height:180px;overflow:auto}.answer{padding:9px 0;border-bottom:1px solid #cad5ed;overflow-wrap:anywhere}.answer summary{cursor:pointer;list-style:none}.answer strong{color:#2945b5;margin-right:6px}.answer p{margin:6px 0;color:#586986}.review{color:#9d3543}
      .footer{display:flex;gap:8px;flex-wrap:wrap;padding:12px 16px;border-top:1px solid #cad5ed;background:#f7f9fff2;position:sticky;bottom:0;backdrop-filter:blur(12px)}.footer button{flex:1;white-space:nowrap}.aux{display:flex;gap:8px;margin-top:12px}.aux button{flex:1}
      .hint{font-size:11px;color:#586986;margin-top:10px}.compact{width:260px;border-radius:17px}.compact .body,.compact .footer{display:none}.compact header{padding:12px 14px}.compact .brand{font-size:13px}.compact .phase-mini{display:block}.phase-mini{display:none;font-size:11px;color:#586986}
      [hidden]{display:none!important}::selection{background:#cddaff;color:#182642}
      @supports not (backdrop-filter:blur(1px)){.panel{background:#f5f8ff}}
      @media(prefers-reduced-motion:reduce){.panel{animation:none}button{transition:background 100ms ease}button:active{transform:none}}
    `;
    shadow.append(style);
    const panel = document.createElement('section');panel.className='panel compact';panel.setAttribute('aria-label','HyperSolve browser agent');
    panel.innerHTML=`<header tabindex="0" aria-label="Drag or use arrow keys to move HyperSolve"><svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="6" width="16" height="14" rx="3"/><path d="M7 6V3h14v13M7 13l3 3 6-6"/></svg><span class="brand">HyperSolve<span class="phase-mini">Monitoring this tab</span></span><button class="collapse" type="button" aria-expanded="false">Expand</button></header><div class="body"><div class="phase" aria-live="polite">Monitoring</div><div class="detail" role="status"></div><progress max="1" value="0" aria-label="Session progress"></progress><div class="count"></div><div class="question"></div><div class="answers"></div><div class="aux"><button class="copy" type="button">Copy answers</button><button class="focus" type="button">Show question</button></div><div class="hint"></div></div><div class="footer"><button class="primary action" type="button">Start solving</button><button class="later" type="button">Later</button><button class="ignore" type="button">Ignore</button><button class="stop" type="button">Stop</button></div>`;
    shadow.append(panel);
    const $=s=>panel.querySelector(s);
    let state={mode:'monitor',answers:[]},compact=true,previousMode='',answerKey='';
    const move=(x,y)=>{panel.style.right='auto';panel.style.left=`${Math.max(8,Math.min(innerWidth-panel.offsetWidth-8,x))}px`;panel.style.top=`${Math.max(8,Math.min(innerHeight-panel.offsetHeight-8,y))}px`};
    const compactTo=value=>{compact=value;panel.classList.toggle('compact',compact);$('.collapse').textContent=compact?'Expand':'Collapse';$('.collapse').setAttribute('aria-expanded',String(!compact));const r=panel.getBoundingClientRect();move(r.left,r.top)};
    const action=name=>async event=>{if(!event.isTrusted)return;try{await onAction(name,state)}catch(error){$('.detail').textContent=error.message||String(error);compactTo(false)}};
    $('.collapse').addEventListener('click',e=>{if(e.isTrusted)compactTo(!compact)});
    $('.action').addEventListener('click',e=>action(state.mode==='detected'?'approve':state.paused?'resume':'pause')(e));
    $('.later').addEventListener('click',e=>{if(e.isTrusted)compactTo(true)});
    $('.ignore').addEventListener('click',action('ignore'));$('.stop').addEventListener('click',action('stop'));
    $('.copy').addEventListener('click',async e=>{if(!e.isTrusted)return;try{await navigator.clipboard.writeText((state.answers||[]).map(a=>`Q${a.id}: ${a.answer||'Needs review'}`).join('\n'));$('.copy').textContent='Copied'}catch{$('.copy').textContent='Select text to copy'}});
    $('.focus').addEventListener('click',action('focus'));
    let drag=null;const header=$('header');
    header.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;const r=panel.getBoundingClientRect();drag=[e.clientX-r.left,e.clientY-r.top];header.setPointerCapture(e.pointerId)});
    header.addEventListener('pointermove',e=>{if(drag)move(e.clientX-drag[0],e.clientY-drag[1])});
    header.addEventListener('pointerup',()=>drag=null);header.addEventListener('pointercancel',()=>drag=null);
    header.addEventListener('keydown',e=>{if(e.target!==header||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const r=panel.getBoundingClientRect(),n=e.shiftKey?24:8;move(r.left+(e.key==='ArrowRight'?n:e.key==='ArrowLeft'?-n:0),r.top+(e.key==='ArrowDown'?n:e.key==='ArrowUp'?-n:0))});
    new ResizeObserver(()=>{const r=panel.getBoundingClientRect();move(r.left,r.top)}).observe(panel);
    addEventListener('resize',()=>{const r=panel.getBoundingClientRect();move(r.left,r.top)});
    return {render(next){state=next;const mode=state.mode||'monitor';
      const terminal=['completed','review','error','cancelled','ignored'].includes(mode),working=!terminal&&mode!=='detected'&&mode!=='monitor';
      const names={monitor:'Monitoring',detected:'Quiz detected',harvesting:'Reading questions',queued:'Waiting for provider',solving:'Solving',ready:'Checking answers',selecting:'Selecting answers',completed:'Ready to review',review:'Some answers need review',cancelled:'Stopped',ignored:'Quiz ignored',error:'Needs attention'};
      const phase=state.paused?'Paused':names[mode]||mode;
      $('.phase').textContent=phase;$('.phase-mini').textContent=phase;
      $('.detail').textContent=state.detail||state.title||'Watching locally for supported quiz questions.';
      $('.count').textContent=mode==='detected'?(state.total?`${state.total} questions · ${state.visible} visible`:`${state.visible} questions visible · total not yet known`):state.total?`${state.selected||0} of ${state.total} selected${state.provider?' · '+state.provider:''}`:'';
      const progress=$('progress');progress.hidden=['monitor','detected'].includes(mode);progress.max=Math.max(1,state.total||1);if(['solving','harvesting','queued'].includes(mode)&&!state.paused)progress.removeAttribute('value');else progress.value=state.selected||0;
      $('.action').textContent=mode==='detected'?'Start solving':state.paused?'Resume':'Pause';$('.action').hidden=!(mode==='detected'||working);$('.action').disabled=state.connected===false;
      $('.later').hidden=mode!=='detected';$('.ignore').hidden=mode!=='detected';$('.stop').hidden=!working;
      $('.aux').hidden=!(state.answers?.length||state.focusId);$('.copy').disabled=!state.answers?.length;$('.focus').disabled=!state.focusId;
      $('.question').textContent=state.question||'';
      $('.hint').textContent=mode==='detected'?'Starts scanning, sends questions to AI, and selects validated answers after your approval.':working?'Pause holds the next action. Requests already sent may finish.':'Review the result in your browser. Nothing is submitted automatically.';
      const key=JSON.stringify(state.answers||[]);if(key!==answerKey){answerKey=key;$('.copy').textContent='Copy answers';$('.answers').replaceChildren(...(state.answers||[]).map(a=>{const row=document.createElement('details');row.className='answer';const summary=document.createElement('summary'),id=document.createElement('strong');id.textContent=`Q${a.id}`;summary.append(id,document.createTextNode(a.answer||'Needs review'));if(a.status==='review')summary.classList.add('review');const p=document.createElement('p');p.textContent=a.reason||'Matched an exact option.';row.append(summary,p);return row}))}
      if(mode!==previousMode){if(mode!=='monitor')compactTo(false);if(!matchMedia('(prefers-reduced-motion: reduce)').matches)$('.phase').animate([{opacity:.35,transform:'translateY(3px)'},{opacity:1,transform:'none'}],{duration:180,easing:'cubic-bezier(.23,1,.32,1)'});previousMode=mode}
      if(mode==='ignored')compactTo(true);
    },collapse(){compactTo(true)},destroy(){host.remove()}};
  };
})();
