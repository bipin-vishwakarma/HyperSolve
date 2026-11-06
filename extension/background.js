/* Independent agents; all page actions pass a fresh manager checkpoint. */
const HOST='com.hypersolve.desktop',terminal=new Set(['completed','review','cancelled','error','ignored']);
const agents=new Map(),pending=new Map(),providerQueues=new Map(),ownedProviderTabs=new Set();
const providerOwners=new Map();
let port=null,client=null,monitoring=true,polling=false,connecting=null;
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const initialized=(async()=>{
  const saved=await chrome.storage.local.get(['client','monitoring']);
  client=saved.client||crypto.randomUUID();monitoring=saved.monitoring!==false;
  await chrome.storage.local.set({client});
  const previous=await chrome.storage.session.get('agents');
  for(const a of previous.agents||[])agents.set(a.tab,{...a,running:false,interrupted:true});
})();
const persist=()=>chrome.storage.session.set({agents:[...agents.values()].map(a=>({id:a.id,tab:a.tab,scope:a.scope,origin:a.origin,document:a.document}))});
function native(op,data={}){
  if(!port)return Promise.reject(Error('Open HyperSolve and connect the browser companion.'));
  return new Promise((resolve,reject)=>{
    const request=crypto.randomUUID(),timer=setTimeout(()=>{pending.delete(request);reject(Error('Windows manager did not respond.'))},12000);
    pending.set(request,{resolve,reject,timer});
    try{port.postMessage({request,client,browser:navigator.userAgent.includes('Edg/')?'Edge':'Chrome',op,...data})}catch(error){clearTimeout(timer);pending.delete(request);reject(error)}
  });
}
async function connect(){
  await initialized;if(port)return;if(connecting)return connecting;
  connecting=(async()=>{
    port=chrome.runtime.connectNative(HOST);
    port.onMessage.addListener(reply=>{const p=pending.get(reply.request);if(!p)return;clearTimeout(p.timer);pending.delete(reply.request);reply.error?p.reject(Error(reply.error)):p.resolve(reply.data)});
    port.onDisconnect.addListener(()=>{const reason=chrome.runtime.lastError?.message||'Windows manager disconnected';port=null;for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error(reason))}pending.clear();for(const a of agents.values())notify(a,{...(a.job||{}),phase:'error',offline:true,detail:reason})});
    await native('hello');
    for(const a of [...agents.values()])if(a.interrupted){
      try{let job=await native('get',{id:a.id});if(!terminal.has(job.phase))job=await native('control',{id:a.id,action:'stop'});await notify(a,job);a.interrupted=false}
      catch{agents.delete(a.tab)}
    }
    await persist();
  })();
  try{await connecting}finally{connecting=null}
}
async function tabMessage(tab,message){
  const result=await chrome.tabs.sendMessage(tab,message,{frameId:0});
  if(result?.error)throw Error(result.error);return result;
}
function notify(a,job){job={...job,results:job.results||a.job?.results};a.job=job;return tabMessage(a.tab,{type:'state',job}).catch(()=>{})}
function quizScope(url){const value=new URL(url);value.searchParams.delete('page');if(!value.hash.startsWith('#/')&&!value.hash.startsWith('#!'))value.hash='';return value.href}
async function checkpoint(a){
  while(true){
    const job=await native('get',{id:a.id});await notify(a,job);
    if(terminal.has(job.phase))throw Error(job.detail||'Session stopped');
    const tab=await chrome.tabs.get(a.tab);
    if(new URL(tab.url).origin!==a.origin||quizScope(tab.url)!==a.scope)throw Error('Tab left the approved quiz');
    if(!job.paused)return job;await delay(350);
  }
}
async function phase(a,value,detail,total,provider){await native('progress',{id:a.id,phase:value,detail,total,provider});return checkpoint(a)}
async function capture(a){
  const deadline=Date.now()+18000;let last;
  while(Date.now()<deadline){await checkpoint(a);try{const data=await tabMessage(a.tab,{type:'capture'});if(data?.questions?.length)return data}catch(e){last=e}await delay(250)}
  throw Error(last?.message||'No supported questions found after navigation');
}
const fingerprint=data=>JSON.stringify(data.questions.map(q=>q.signature));
async function changed(a,before){
  const deadline=Date.now()+18000;
  while(Date.now()<deadline){const data=await capture(a);if(fingerprint(data)!==fingerprint(before))return data;await delay(300)}
  throw Error('Next page did not change the questions. Stopped to avoid repeating actions.');
}
async function browserSolve(a,prompt){
  const providers=[{name:'ChatGPT',host:'chatgpt.com',url:'https://chatgpt.com/'},{name:'Gemini',host:'gemini.google.com',url:'https://gemini.google.com/app'},{name:'Claude',host:'claude.ai',url:'https://claude.ai/new'}];
  const tabs=await chrome.tabs.query({});
  const provider=providers.find(p=>tabs.some(t=>!ownedProviderTabs.has(t.id)&&(()=>{try{return new URL(t.url).hostname===p.host}catch{return false}})()));
  if(!provider)throw Error('Open and sign in to ChatGPT, Gemini or Claude, or configure an API key in Windows.');
  const previous=providerQueues.get(provider.name)||Promise.resolve();
  const task=previous.catch(()=>{}).then(async()=>{
    await phase(a,'solving','Opening a separate AI conversation',undefined,provider.name);
    const tab=await chrome.tabs.create({url:provider.url,active:false});ownedProviderTabs.add(tab.id);providerOwners.set(tab.id,a.id);
    try{
      let ready=false;
      for(let n=0;n<80;n++){await checkpoint(a);const t=await chrome.tabs.get(tab.id);if(t.status==='complete'){ready=true;break}await delay(250)}
      if(!ready)throw Error('AI provider did not finish loading');await delay(1000);await checkpoint(a);
      const result=await tabMessage(tab.id,{type:'provider_solve',id:a.id,prompt});
      if(!result?.raw)throw Error('AI provider returned no answer');
      await checkpoint(a);await native('response',{id:a.id,raw:result.raw,provider:provider.name});
    }finally{
      // Keep the owned conversation visible for inspection; never reuse it for another quiz.
      ownedProviderTabs.add(tab.id);
    }
  });
  providerQueues.set(provider.name,task);await task;
}
async function run(a){
  if(a.running)return;a.running=true;
  try{
    await phase(a,'harvesting','Reading this quiz; nothing is submitted');
    const pages=[],questions=[],seen=new Set();let data=await capture(a);
    for(let page=0;page<50;page++){
      const key=fingerprint(data);if(seen.has(key))throw Error('Question page repeated; stopped scanning');seen.add(key);
      if(new URL(data.url).origin!==a.origin)throw Error('Quiz navigation left the approved site');
      const items=data.questions.map(q=>({...q,id:questions.length+1+data.questions.indexOf(q)}));
      questions.push(...items.map(q=>({id:q.id,text:q.text,options:q.options})));
      if(questions.length>500)throw Error('Quiz exceeds 500 questions; split it into smaller sessions');
      pages.push({...data,items});
      await phase(a,'harvesting',`${questions.length} questions found across ${pages.length} pages`,questions.length);
      if(!data.hasNext)break;
      if(page===49)throw Error('Quiz exceeds the 50-page scan limit');
      await checkpoint(a);await tabMessage(a.tab,{type:'next'});data=await changed(a,data);
    }
    await checkpoint(a);
    let job=await native('solve',{id:a.id,questions});
    if(job.execution==='web'){job=await checkpoint(a);await browserSolve(a,job.prompt)}
    while(true){job=await checkpoint(a);if(job.phase==='ready')break;await delay(500)}
    const results=new Map(job.results.map(r=>[r.id,r]));
    await phase(a,'selecting','Applying exact matches; uncertain answers are left for review');
    if(pages.length>1){
      await checkpoint(a);await chrome.tabs.update(a.tab,{url:pages[0].url});
      const deadline=Date.now()+18000;
      while(fingerprint(await capture(a))!==fingerprint(pages[0])){if(Date.now()>deadline)throw Error('Could not return to the first question page');await delay(250)}
    }
    for(let index=0;index<pages.length;index++){
      const page=pages[index],ready=page.items.filter(q=>results.get(q.id)?.status==='ready');
      await checkpoint(a);let current=await capture(a);
      if(fingerprint(current)!==fingerprint(page))throw Error('Question page changed before selection. Review the quiz in your browser.');
      for(const item of ready){
        await checkpoint(a);
        const report=await tabMessage(a.tab,{type:'select',document:current.document,items:[{...item,option:results.get(item.id).option}]});
        await native('report',{id:a.id,...report});
      }
      // Next saves common multi-page quiz forms; raw GET navigation can discard checked answers.
      if(index<pages.length-1){await checkpoint(a);await tabMessage(a.tab,{type:'next'});await changed(a,current)}
    }
    await checkpoint(a);await native('report',{id:a.id,finish:true});await notify(a,await native('get',{id:a.id}));
  }catch(error){
    await native('progress',{id:a.id,phase:'error',detail:error.message}).catch(()=>{});
    if(port)await native('get',{id:a.id}).then(job=>notify(a,job)).catch(()=>{});
  }finally{a.running=false;await persist()}
}
async function poll(){
  if(polling||!port)return;polling=true;
  try{const snapshot=await native('poll');for(const job of snapshot.sessions){const a=agents.get(job.tab);if(!a||a.id!==job.id)continue;await notify(a,job);if(job.approved&&!terminal.has(job.phase)&&!a.running)run(a)}}catch{}finally{polling=false}
}
setInterval(poll,1000);
chrome.alarms.create('companion-health',{periodInMinutes:1});chrome.alarms.onAlarm.addListener(()=>poll());
chrome.tabs.onRemoved.addListener(tab=>{ownedProviderTabs.delete(tab);providerOwners.delete(tab);const a=agents.get(tab);if(a){native('control',{id:a.id,action:'stop'}).catch(()=>{});agents.delete(tab);persist()}});
chrome.runtime.onStartup.addListener(()=>connect().catch(()=>{}));
chrome.runtime.onInstalled.addListener(()=>connect().catch(()=>{}));
chrome.runtime.onMessage.addListener((message,sender,respond)=>{
  if(sender.id!==chrome.runtime.id)return;
  const handle=async()=>{
    await initialized;
    if(message.type==='popup_state')return {monitoring,connected:!!port,sessions:[...agents.values()].map(a=>a.job).filter(Boolean)};
    if(message.type==='monitor'){
      monitoring=!!message.enabled;await chrome.storage.local.set({monitoring});
      for(const tab of await chrome.tabs.query({}))tabMessage(tab.id,{type:'monitor',enabled:monitoring}).catch(()=>{});
      return {ok:true};
    }
    if(message.type==='connect'){await connect();return {ok:true}}
    if(message.type==='rescan'){
      await connect();const tabs=await chrome.tabs.query({active:true,currentWindow:true});
      if(tabs[0]){const a=agents.get(tabs[0].id);if(a&&!terminal.has(a.job?.phase))throw Error('Stop the active session before scanning again');agents.delete(tabs[0].id);await persist();await tabMessage(tabs[0].id,{type:'rescan'})}
      return {ok:true};
    }
    if(message.type==='save_workspace'){
      const tabs=(await chrome.tabs.query({currentWindow:true})).filter(t=>/^https?:\/\//.test(t.url));
      await chrome.storage.local.set({workspace:tabs.map(t=>({url:t.url,pinned:t.pinned}))});return {count:tabs.length};
    }
    if(message.type==='restore_workspace'){
      const saved=(await chrome.storage.local.get('workspace')).workspace||[];
      if(!saved.length)throw Error('Save a workspace first.');
      const window=await chrome.windows.create({url:saved.map(t=>t.url),focused:true});
      const restored=await chrome.tabs.query({windowId:window.id});
      for(let index=0;index<saved.length;index++)if(saved[index].pinned&&restored[index])await chrome.tabs.update(restored[index].id,{pinned:true});
      return {count:saved.length};
    }
    if(!sender.tab||sender.frameId!==0)throw Error('Only a top-level browser tab can register a quiz');
    const tab=sender.tab.id;
    if(message.type==='provider_checkpoint'){
      if(providerOwners.get(tab)!==message.id)throw Error('Provider conversation is not owned by this agent');
      const job=await native('get',{id:message.id});
      if(terminal.has(job.phase))throw Error('Agent stopped before sending to AI');
      return {paused:job.paused};
    }
    if(message.type==='content_ready'){
      let a=agents.get(tab);
      if(a&&(!a.job?.approved||quizScope(sender.tab.url)!==a.scope)){
        await native('control',{id:a.id,action:'stop'}).catch(()=>{});agents.delete(tab);await persist();a=null;
      }
      if(a)a.document=message.document;
      return {monitoring,job:a?.job};
    }
    await connect();
    if(message.type==='detected'){
      if(!monitoring)return {};
      const old=agents.get(tab);if(old&&(!terminal.has(old.job?.phase)||old.scope===message.summary.scope))return {job:old.job};
      const a={id:crypto.randomUUID(),tab,document:message.document,scope:message.summary.scope,origin:new URL(sender.tab.url).origin};
      if(new URL(message.summary.url).origin!==a.origin)throw Error('Quiz origin changed');
      a.job=await native('detect',{...message.summary,id:a.id,tab,document:a.document});agents.set(tab,a);await persist();return {job:a.job};
    }
    if(message.type==='action'){
      const a=agents.get(tab);if(!a||a.id!==message.id||a.document!==message.document)throw Error('This quiz session belongs to a different page');
      const action=message.action==='start'?'approve':message.action;
      if(!['approve','pause','resume','stop','ignore'].includes(action))throw Error('Unknown action');
      const job=await native('control',{id:a.id,action});await notify(a,job);if(job.approved&&!terminal.has(job.phase)&&!a.running)run(a);return {job};
    }
    throw Error('Unknown browser companion request');
  };
  handle().then(respond,error=>respond({error:error.message}));return true;
});
