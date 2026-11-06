(() => {
  if(window.top!==window)return;
  const providerHosts=['chatgpt.com','chat.openai.com','gemini.google.com','claude.ai'];
  if(providerHosts.includes(location.hostname)){ setupProvider(); return; }
  const documentId=crypto.randomUUID();let session=null,scanTimer=null,monitoring=true,lastDetection='',captureCache=[];
  const send=message=>chrome.runtime.sendMessage({...message,document:documentId});
  const normal=s=>String(s||'').replace(/\s+/g,' ').trim();
  const signature=q=>JSON.stringify([normal(q.text),q.options.map(o=>normal(o.text))]);
  const scope=()=>{const u=new URL(location.href);u.searchParams.delete('page');if(!u.hash.startsWith('#/')&&!u.hash.startsWith('#!'))u.hash='';return u.href};
  const evidence=()=>!!document.querySelector('.qcard .qtext,.que .qtext,.question .question_text,[data-question-id]')||((/\b(quiz|assessment|exam|practice test)\b/i.test(document.title)||/(?:^|[\/_.-])(quiz|assessment|exam|test)(?:[\/_.-]|$)/i.test(location.pathname))&&!!document.querySelector('.question,.question-container,[role=listitem]'));
  const capture=()=>{
    const parsed=globalThis.HyperSolveParser().filter(q=>normal(q.text)&&!/^question\s*\d+$/i.test(normal(q.text))&&q.options.length>=2&&q.options.every(o=>normal(o.text)));
    captureCache=parsed;
    const navigation=[...document.querySelectorAll('button,input[type=submit],a')].find(el=>/^(next|next page|next question)$/i.test(normal(el.value||el.textContent))&&!el.disabled&&el.getBoundingClientRect().width>0);
    const total=document.querySelectorAll('.qnbutton,[data-question-number]').length;
    return {url:location.href,title:document.title,document:documentId,scope:scope(),questions:parsed.map(q=>({localId:q.dom_id,text:q.text,options:q.options.map(o=>o.text),signature:signature(q)})),hasNext:!!navigation,total:total>=parsed.length&&total>0?total:null};
  };
  const panel=globalThis.HyperSolvePanel(async(action,state)=>{
    if(action==='focus'){const q=[...document.querySelectorAll('[data-hypersolve-id]')].find(el=>el.dataset.hypersolveId===state.focusId);if(q)q.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});return}
    if(!session?.id)throw Error('No quiz session is available yet.');
    const result=await send({type:'action',id:session.id,action});
    if(result?.error)throw Error(result.error);
  });
  const render=job=>{session=job;panel.render({mode:job.phase,paused:job.paused,title:job.title,detail:job.detail,visible:job.visible,total:job.total,selected:job.selected?.length||0,provider:job.provider,answers:job.results||[],focusId:job.focusId,question:job.question,connected:!job.offline})};
  async function scan(){
    if(!monitoring||session?.approved&&!['completed','review','cancelled','error'].includes(session.phase))return;
    if(!evidence())return;
    let data;try{data=capture()}catch{return}
    if(!data.questions.length)return;
    const key=JSON.stringify([data.scope,data.questions.map(q=>q.signature)]);
    if(lastDetection===key)return;lastDetection=key;
    try{const reply=await send({type:'detected',summary:{url:data.url,title:data.title,visible:data.questions.length,total:data.total,scope:data.scope}});if(reply?.job)render(reply.job);else if(reply?.error){panel.render({mode:'error',detail:reply.error,connected:false})}}catch{panel.render({mode:'error',detail:'Browser companion disconnected. Reload this tab after reconnecting.'})}
  }
  const observer=new MutationObserver(()=>{clearTimeout(scanTimer);scanTimer=setTimeout(scan,600)});
  observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true});
  chrome.runtime.onMessage.addListener((message,sender,respond)=>{
    if(sender.id!==chrome.runtime.id)return;
    const work=async()=>{
      if(message.type==='state'){if(message.job)render(message.job);return {ok:true}}
      if(message.type==='monitor'){monitoring=message.enabled;if(monitoring){lastDetection='';await scan()}else if(!session?.approved)panel.render({mode:'monitor',detail:'Monitoring paused in the browser companion.'});return {ok:true}}
      if(message.type==='capture')return capture();
      if(message.type==='next'){
        const el=[...document.querySelectorAll('button,input[type=submit],a')].find(el=>/^(next|next page|next question)$/i.test(normal(el.value||el.textContent))&&!el.disabled&&el.getBoundingClientRect().width>0);
        if(!el)throw Error('Next page is not available');
        if(el.href&&new URL(el.href,location.href).origin!==location.origin)throw Error('Next page leaves the approved quiz site');
        setTimeout(()=>el.click(),30);return {ok:true};
      }
      if(message.type==='select'){
        if(message.document!==documentId)throw Error('Page changed before answer selection');
        const fresh=globalThis.HyperSolveParser();const selected=[],failed=[];
        for(const item of message.items){
          const exact=fresh.filter(q=>signature(q)===item.signature);
          const q=exact.find(q=>q.dom_id===item.localId)||(exact.length===1?exact[0]:null);
          if(!q||!Number.isInteger(item.option)||!q.options[item.option]){failed.push(item.id);continue}
          const marker=q.options[item.option].ref_id;
          const option=[...document.querySelectorAll('[data-hypersolve-opt]')].find(el=>el.getAttribute('data-hypersolve-opt')===marker);
          if(!option||!option.isConnected||option.disabled){failed.push(item.id);continue}
          option.click();
          if(option.tagName==='INPUT'){option.checked=true;option.dispatchEvent(new Event('input',{bubbles:true}));option.dispatchEvent(new Event('change',{bubbles:true}))}
          await new Promise(resolve=>setTimeout(resolve,80));
          if(option.checked||option.getAttribute('aria-checked')==='true'||option.classList.contains('sel')||option.classList.contains('selected')||option.classList.contains('checked'))selected.push(item.id);else failed.push(item.id);
          if(session)render({...session,focusId:q.dom_id,question:q.text});
        }
        return {selected,failed};
      }
      if(message.type==='rescan'){lastDetection='';session=null;await scan();return {ok:true}}
      throw Error('Unknown companion action');
    };
    work().then(respond,error=>respond({error:error.message}));return true;
  });
  send({type:'content_ready'}).then(reply=>{monitoring=reply?.monitoring!==false;if(reply?.job)render(reply.job);else panel.render({mode:'monitor',detail:'Watching locally for supported quizzes.'});scan()}).catch(()=>{});

  function setupProvider(){
    let busy=false;
    chrome.runtime.onMessage.addListener((message,sender,respond)=>{
      if(sender.id!==chrome.runtime.id||message.type!=='provider_solve')return;
      if(busy){respond({error:'Provider conversation is already busy'});return}
      busy=true;
      const solve=async()=>{
        const permit=async()=>{
          while(true){const reply=await chrome.runtime.sendMessage({type:'provider_checkpoint',id:message.id});if(reply?.error)throw Error(reply.error);if(!reply?.paused)return;await new Promise(r=>setTimeout(r,250))}
        };
        const editorSelector='#prompt-textarea,textarea[data-id="root"],rich-textarea [contenteditable=true],div.ql-editor,div[contenteditable=true],textarea';
        let editor=null;
        for(let n=0;n<60;n++){await permit();editor=document.querySelector(editorSelector);if(editor)break;await new Promise(r=>setTimeout(r,250))}
        if(!editor)throw Error('Sign in to this AI provider, then retry the quiz.');
        const responseSelector=location.hostname.includes('gemini')?'message-content,.model-response-text':location.hostname==='claude.ai'?'[class*=font-claude-message]':'[data-message-author-role=assistant]';
        const initial=document.querySelectorAll(responseSelector).length;
        await permit();
        editor.focus();
        if(editor.tagName==='TEXTAREA'){Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(editor,message.prompt)}else{editor.textContent=message.prompt}
        editor.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:message.prompt}));
        await new Promise(r=>setTimeout(r,350));
        const sendButton=document.querySelector('button[data-testid="send-button"],button[aria-label="Send prompt"],button[aria-label="Send message"],button[aria-label="Send Message"],button[aria-label="Send"],button[aria-label="Submit"],button.send-button');
        if(!sendButton||sendButton.disabled)throw Error('Could not find an enabled Send button. Check the provider tab.');
        await permit();
        sendButton.click();
        let last='',stable=0;const deadline=Date.now()+120000;
        while(Date.now()<deadline){
          await new Promise(r=>setTimeout(r,900));
          const messages=[...document.querySelectorAll(responseSelector)];
          if(messages.length<=initial)continue;
          const text=messages.at(-1).innerText.trim();
          const generating=!!document.querySelector('button[data-testid="stop-button"],button[aria-label*="Stop generating"],button[aria-label="Stop"],.streaming');
          if(text&&text===last&&!generating){if(++stable>=3)return {raw:text}}else stable=0;
          last=text;
        }
        throw Error('AI response timed out. Check usage limits and the provider conversation.');
      };
      solve().then(value=>{busy=false;respond(value)},error=>{busy=false;respond({error:error.message})});return true;
    });
  }
})();
