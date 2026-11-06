"""Real bundled-Chromium extension/native-bridge smoke; local quizzes and stub AI only."""
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import winreg
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.async_api import async_playwright
from hypersolve.companion.agents import AgentManager
from hypersolve.companion.config import EXTENSION_ID, HOST_NAME
from hypersolve.companion.server import CompanionServer

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'scratch/review'


class Fixture(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/settings':
            body='<title>Settings</title><fieldset><legend>Choose a colour</legend><label><input type="radio" name="color">Blue</label><label><input type="radio" name="color">Red</label></fieldset>'
        else:
            number='2' if 'page=1' in self.path else '1'
            name=self.path.split('?')[0]
            nav="<button onclick=\"localStorage.setItem('savedFirst',document.querySelectorAll('[aria-checked=true]').length);location.href='/quiz-multi?page=1'\">Next page</button>" if name=='/quiz-multi' and number=='1' else '<button onclick="window.submitted=true">Submit quiz</button>'
            body=f'''<title>Local quiz {name}</title><style>body{{font:16px Segoe UI;background:#e7edf7;padding:40px}}.qcard{{background:white;max-width:620px;padding:24px}}.opt{{border:1px solid #bbb;padding:15px;margin-top:12px;cursor:pointer}}.opt[aria-checked=true]{{background:#dce4ff}}</style>
            <section class="qcard"><div class="qtext">{name} page {number}: choose a colour?</div><div class="opt" role="radio" aria-checked="false">A. Blue sky</div><div class="opt" role="radio" aria-checked="false">B. Red</div></section>{nav}
            <script>document.querySelectorAll('.opt').forEach(el=>el.onclick=()=>{{el.parentElement.querySelectorAll('.opt').forEach(o=>o.setAttribute('aria-checked','false'));el.setAttribute('aria-checked','true')}})</script>'''
        self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body.encode())
    def log_message(self,*args):pass


async def until(predicate,timeout=25):
    for _ in range(int(timeout*10)):
        value=predicate()
        if value:return value
        await asyncio.sleep(.1)
    raise AssertionError('Timed out waiting for companion state')


async def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    release=threading.Event()
    calls=[]
    def solve(questions):
        calls.append(questions)
        if '/quiz-first' in questions[0]['text']:release.wait(30)
        return json.dumps({str(q['id']):{'answer':q['options'][0],'reason':'Local fixture answer','needs_review':False} for q in questions}),'Fixture API'
    manager=AgentManager(solve)
    fixture=ThreadingHTTPServer(('127.0.0.1',0),Fixture)
    threading.Thread(target=fixture.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{fixture.server_port}'
    key_path=rf'Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}'
    prior=None;existed=False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key_path) as key:
            existed=True
            try:prior=winreg.QueryValueEx(key,'')[0]
            except FileNotFoundError:pass
    except FileNotFoundError:pass
    with tempfile.TemporaryDirectory(prefix='hypersolve-companion-') as temp:
        server=CompanionServer(manager,Path(temp)/'data');server.start()
        manifest=Path(temp)/'native-host.json'
        bridge=ROOT/'dist/HyperSolve/HyperSolveBridge.exe'
        assert bridge.is_file(),'Build the Windows app before this smoke'
        manifest.write_text(json.dumps({'name':HOST_NAME,'description':'HyperSolve isolated test','path':str(bridge),'type':'stdio','allowed_origins':[f'chrome-extension://{EXTENSION_ID}/']}))
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,key_path) as key:winreg.SetValueEx(key,'',0,winreg.REG_SZ,str(manifest))
        try:
            async with async_playwright() as pw:
                extension=str(ROOT/'dist/HyperSolve/browser-extension')
                context=await pw.chromium.launch_persistent_context(str(Path(temp)/'profile'),channel='chromium',headless=True,viewport={'width':1280,'height':800},env={**os.environ,'HYPERSOLVE_DATA_DIR':str(Path(temp)/'data')},args=[f'--disable-extensions-except={extension}',f'--load-extension={extension}'])
                try:
                    worker=context.service_workers[0] if context.service_workers else await context.wait_for_event('serviceworker')
                    assert EXTENSION_ID in worker.url,worker.url
                    first=await context.new_page();await first.goto(base+'/quiz-first')
                    host=first.locator('#__hypersolve_companion__')
                    await host.get_by_role('button',name='Start solving',exact=True).wait_for(timeout=20000)
                    assert not calls,'Detection must not call AI before approval'
                    await first.screenshot(path=str(OUTPUT/'companion-detected.png'))
                    # A web page cannot approve with a synthetic click.
                    await host.get_by_role('button',name='Start solving',exact=True).evaluate('el=>el.click()')
                    await asyncio.sleep(.3);assert not calls
                    await host.get_by_role('button',name='Start solving',exact=True).click()
                    await until(lambda:len(calls)==1)
                    await host.get_by_role('button',name='Pause',exact=True).click()
                    await host.locator('.phase').filter(has_text='Paused').wait_for()
                    second=await context.new_page();await second.goto(base+'/quiz-second')
                    second_host=second.locator('#__hypersolve_companion__')
                    await second_host.get_by_role('button',name='Start solving',exact=True).click()
                    await second_host.locator('.phase').filter(has_text='Ready to review').wait_for(timeout=20000)
                    assert await second.locator('.opt[aria-checked=true]').count()==1
                    assert await first.locator('.opt[aria-checked=true]').count()==0
                    release.set();await asyncio.sleep(.8)
                    assert await first.locator('.opt[aria-checked=true]').count()==0,'Paused agent applied an answer'
                    await host.get_by_role('button',name='Resume',exact=True).click()
                    await host.locator('.phase').filter(has_text='Ready to review').wait_for(timeout=15000)
                    assert await first.locator('.opt[aria-checked=true]').count()==1
                    await asyncio.sleep(1.3)
                    assert await host.locator('.answer').count()==1,'Poll erased answer details'
                    assert not await first.evaluate('!!window.submitted')
                    await first.screenshot(path=str(OUTPUT/'companion-completed.png'))
                    settings=await context.new_page();await settings.goto(base+'/settings');await asyncio.sleep(1)
                    assert not any('/settings' in j['url'] for j in manager.snapshot()['sessions'])
                    multi=await context.new_page();await multi.goto(base+'/quiz-multi?page=0')
                    await multi.locator('#__hypersolve_companion__').get_by_role('button',name='Start solving',exact=True).click()
                    await multi.locator('#__hypersolve_companion__ .phase').filter(has_text='Ready to review').wait_for(timeout=30000)
                    assert await multi.evaluate("localStorage.getItem('savedFirst')")=='1','Next did not save first-page selections'
                    assert await multi.locator('.opt[aria-checked=true]').count()==1
                    assert not await multi.evaluate('!!window.submitted')
                    # A new quiz on the same host gets its own unapproved session.
                    await first.goto(base+'/quiz-other')
                    await first.locator('#__hypersolve_companion__').get_by_role('button',name='Start solving',exact=True).wait_for()
                    assert len(calls)==3
                    assert manager.snapshot()['stats']['selected']==4
                    before=await context.new_page();await before.goto(base+'/quiz-before')
                    await before.locator('#__hypersolve_companion__').get_by_role('button',name='Start solving',exact=True).wait_for()
                    old=next(j for j in manager.snapshot()['sessions'] if j['url'].endswith('/quiz-before'))
                    await before.goto(base+'/quiz-after')
                    await before.locator('#__hypersolve_companion__').get_by_role('button',name='Start solving',exact=True).wait_for()
                    assert manager.get(old['client'],old['id'])['phase']=='cancelled'
                    assert len(calls)==3,'Same-origin navigation reused old approval'
                    # Hidden SPA pages retain no refs that can steal a fresh option click.
                    await second.evaluate("""() => {const old=document.querySelector('.qcard').cloneNode(true);old.id='old-hidden';old.style.display='none';old.querySelectorAll('.opt').forEach(el=>el.setAttribute('aria-checked','false'));document.body.prepend(old)}""")
                    await worker.evaluate("""async () => {const a=[...agents.values()].find(a=>a.job?.url.endsWith('/quiz-second'));const data=await tabMessage(a.tab,{type:'capture'});await tabMessage(a.tab,{type:'select',document:data.document,items:[{...data.questions[0],id:1,option:0}]})}""")
                    assert await second.locator('#old-hidden [aria-checked=true]').count()==0
                    assert await second.locator('#old-hidden [data-hypersolve-opt]').count()==0
                    # Exercise the web-provider queue using a local intercepted provider UI.
                    provider_html='''<title>Fixture ChatGPT</title><textarea id="prompt-textarea"></textarea><button data-testid="send-button">Send</button><script>document.querySelector('button').onclick=()=>{const q=JSON.parse(document.querySelector('textarea').value.split('\\n').at(-1));const result=Object.fromEntries(q.map(x=>[x.id,{answer:x.options[0],reason:'Fixture web answer',needs_review:false}]));const el=document.createElement('div');el.dataset.messageAuthorRole='assistant';el.textContent=JSON.stringify(result);document.body.append(el)}</script>'''
                    await context.route('https://chatgpt.com/**',lambda route:route.fulfill(body=provider_html,content_type='text/html'))
                    provider=await context.new_page();await provider.goto('https://chatgpt.com/')
                    # Extension-created tabs navigate before Playwright attaches routing.
                    # Hold only their initial creation so this fixture never contacts a provider.
                    await worker.evaluate("""() => {
                      const create=chrome.tabs.create.bind(chrome.tabs);
                      chrome.tabs.create=async options=>{
                        if(options.url!=='https://chatgpt.com/')return create(options);
                        const tab=await create({...options,url:'about:blank#hypersolve-provider-fixture-'+crypto.randomUUID()});
                        for(let n=0;n<100;n++){const current=await chrome.tabs.get(tab.id);if(current.url.startsWith('https://chatgpt.com/')&&current.status==='complete')return current;await new Promise(r=>setTimeout(r,100))}
                        throw Error('Fixture provider did not load');
                      };
                    }""")
                    async def serve_provider_fixtures():
                        while True:
                            for page in context.pages:
                                if page.url.startswith('about:blank#hypersolve-provider-fixture-'):
                                    await page.goto('https://chatgpt.com/')
                            await asyncio.sleep(.1)
                    fixture_task=asyncio.create_task(serve_provider_fixtures())
                    manager.api_solver=manager._api_solve
                    with patch.dict(os.environ,{'OPENAI_API_KEY':'','GEMINI_API_KEY':''}):
                        web_pages=[]
                        for index in range(2):
                            page=await context.new_page();await page.goto(base+f'/quiz-web-{index}');web_pages.append(page)
                            await page.locator('#__hypersolve_companion__').get_by_role('button',name='Start solving',exact=True).click()
                        for page in web_pages:
                            try:
                                await page.locator('#__hypersolve_companion__ .phase').filter(has_text='Ready to review').wait_for(timeout=35000)
                            except Exception:
                                print(json.dumps(manager.snapshot(),indent=2),flush=True)
                                for debug_page in context.pages:
                                    if 'chatgpt.com' in debug_page.url:
                                        print('PROVIDER',debug_page.url,(await debug_page.content())[:2000],flush=True)
                                await page.screenshot(path=str(OUTPUT/'companion-provider-failure.png'))
                                raise
                            assert await page.locator('.opt[aria-checked=true]').count()==1
                    assert await provider.locator('textarea').input_value()=='','Existing conversation was modified'
                    provider_pages=[p for p in context.pages if p.url=='https://chatgpt.com/']
                    assert len(provider_pages)==3,'Each web agent needs an owned conversation'
                    provider_html='''<title>Delayed fixture provider</title><script>setTimeout(()=>{document.body.innerHTML='<textarea id="prompt-textarea"></textarea><button data-testid="send-button">Send</button>';document.querySelector('button').onclick=()=>{window.sentAfterStop=true}},4000)</script>'''
                    stopped=await context.new_page();await stopped.goto(base+'/quiz-web-stop')
                    stopped_host=stopped.locator('#__hypersolve_companion__')
                    with patch.dict(os.environ,{'OPENAI_API_KEY':'','GEMINI_API_KEY':''}):
                        await stopped_host.get_by_role('button',name='Start solving',exact=True).click()
                        await stopped_host.locator('.phase').filter(has_text='Solving').wait_for(timeout=15000)
                        await asyncio.sleep(.6)
                        await stopped_host.get_by_role('button',name='Stop',exact=True).click()
                        await stopped_host.locator('.phase').filter(has_text='Stopped').wait_for()
                        await asyncio.sleep(5)
                    delayed=[p for p in context.pages if p.url=='https://chatgpt.com/' and await p.title()=='Delayed fixture provider']
                    assert delayed,'Delayed provider conversation was not created'
                    assert not await delayed[0].evaluate('!!window.sentAfterStop'),'Cancelled session sent a new prompt'
                    assert await delayed[0].locator('textarea').input_value()==''
                    fixture_task.cancel()
                    print('PASS: real native bridge; detection/approval; synthetic approval rejected; two-tab pause isolation; strict selection; multi-page Next save; no submit; persistent answer details; settings ignored; same-origin approval isolation; hidden SPA refs cleared; web queue with separate conversations; stopping during provider load prevents Send (local provider fixtures).')
                finally:await context.close()
        finally:
            release.set();server.close();fixture.shutdown()
            if existed:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,key_path) as key:
                    if prior is None:
                        try:winreg.DeleteValue(key,'')
                        except FileNotFoundError:pass
                    else:winreg.SetValueEx(key,'',0,winreg.REG_SZ,prior)
            else:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER,key_path)


if __name__=='__main__':asyncio.run(main())
