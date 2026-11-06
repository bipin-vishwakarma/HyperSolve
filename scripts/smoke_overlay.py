"""Interactive overlay smoke on local multi-page quiz fixtures and stub AI."""
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import sys
import threading
from unittest.mock import AsyncMock, MagicMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.async_api import async_playwright
from hypersolve.desktop.runtime import find_chrome
from hypersolve.core.daemon import HyperSolveDaemon
from hypersolve.hud.injector import HUDInjector
from hypersolve.hud.controls import OverlayControls
from hypersolve.injector.synthetic_events import SyntheticInjector

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/summary'):
            html = '<title>Review</title><h1>Review selected answers</h1><iframe src="/frame"></iframe>'
        elif self.path == '/frame':
            html = '<h1>Embedded content</h1>'
        else:
            second = 'page=1' in self.path
            navigate = '<button onclick="location.href=\'/summary\'">Finish attempt</button>' if second else '<button onclick="location.href=\'/quiz?page=1\'">Next page</button>'
            html = f'<title>Local quiz</title><style>body{{font:16px Segoe UI;padding:40px;background:#f3f4f8}}.qcard{{padding:24px;background:white;max-width:600px}}.opt{{padding:14px;border:1px solid #ddd;margin:8px 0}}</style><section class="qcard"><div class="qtext">Practice question {2 if second else 1}?</div><div class="opt" role="radio" aria-checked="false">A. First</div><div class="opt" role="radio" aria-checked="false">B. Second</div></section>{navigate}<iframe src="/frame"></iframe>'
        self.send_response(200)
        self.send_header('Content-Type','text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    def log_message(self,*args):
        pass

async def main():
    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    output = Path(__file__).resolve().parents[1] / 'scratch/review'
    output.mkdir(parents=True,exist_ok=True)
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(executable_path=str(find_chrome()),headless=True,args=[f'--remote-debugging-port={port}'])
            context = await browser.new_context(viewport={"width":1280,"height":800},permissions=['clipboard-read','clipboard-write'])
            page = await context.new_page()
            await page.goto(base + '/quiz?page=0')
            waiting = asyncio.Event()
            release = asyncio.Event()
            async def solve(*args):
                waiting.set()
                await release.wait()
                return {"1":"Second","2":"First"}, 'Local stub AI'
            brain = MagicMock()
            brain.session_pool.get_active_providers = AsyncMock(return_value={"chatgpt":[object()]})
            brain.solve_batch = solve
            daemon = HyperSolveDaemon(cdp_url=f'http://127.0.0.1:{port}',target_url=page.url)
            with patch('hypersolve.core.daemon.BrainRouter',return_value=brain):
                task = asyncio.create_task(daemon.start())
                await asyncio.wait_for(waiting.wait(),20)
                assert 'page=1' in page.url
                await page.locator('#__hypersolve_host__ .phase').filter(has_text='Solving').wait_for()
                assert await page.locator('#__hypersolve_host__').is_visible()
                assert await page.frames[1].locator('#__hypersolve_host__').count() == 0
                await page.screenshot(path=str(output / 'overlay-solving.png'))
                await page.get_by_role('button',name='Pause',exact=True).click()
                await page.locator('#__hypersolve_host__ .phase').filter(has_text='Paused').wait_for()
                release.set()
                await asyncio.sleep(.2)
                assert 'page=1' in page.url
                assert await page.locator('[aria-checked="true"]').count() == 0
                await page.screenshot(path=str(output / 'overlay-paused.png'))
                await page.get_by_role('button',name='Resume',exact=True).click()
                await asyncio.wait_for(task,25)
            assert '/summary' in page.url
            await page.locator('#__hypersolve_host__ .phase').filter(has_text='Completed').wait_for()
            assert await page.locator('.answers li').count() == 2
            await page.get_by_role('button',name='Copy answers',exact=True).click()
            assert 'Q1: Second' in await page.evaluate('navigator.clipboard.readText()')
            await page.get_by_role('button',name='Collapse',exact=True).click()
            assert await page.get_by_role('button',name='Expand',exact=True).is_visible()
            await page.get_by_role('button',name='Expand',exact=True).click()
            header = page.locator('#__hypersolve_host__ header')
            before = await page.locator('#__hypersolve_host__ .panel').bounding_box()
            await header.focus()
            await header.press('ArrowDown')
            after = await page.locator('#__hypersolve_host__ .panel').bounding_box()
            assert after['y'] == before['y'] + 8
            header_box = await header.bounding_box()
            await page.mouse.move(header_box['x'] + 80,header_box['y'] + 20)
            await page.mouse.down()
            await page.mouse.move(header_box['x'] + 120,header_box['y'] + 60,steps=4)
            await page.mouse.up()
            moved = await page.locator('#__hypersolve_host__ .panel').bounding_box()
            assert moved['y'] > after['y']
            await page.screenshot(path=str(output / 'overlay-completed.png'))
            # Restart with a new binding; stale initialization scripts must never win.
            await page.goto(base + '/quiz?page=0')
            waiting.clear()
            release.clear()
            daemon2 = HyperSolveDaemon(cdp_url=f'http://127.0.0.1:{port}',target_url=page.url)
            with patch('hypersolve.core.daemon.BrainRouter',return_value=brain):
                task2 = asyncio.create_task(daemon2.start())
                await asyncio.wait_for(waiting.wait(),20)
                await page.get_by_role('button',name='Stop',exact=True).click()
                try:
                    await asyncio.wait_for(task2,5)
                    raise AssertionError('Overlay Stop did not cancel the running session')
                except asyncio.CancelledError:
                    pass
            await page.locator('#__hypersolve_host__ .phase').filter(has_text='Stopped').wait_for()
            # Force old init script to run after latest one and assert active generation survives.
            latest = await page.evaluate('window.__hypersolve_generation')
            stale = HUDInjector._get_overlay_script().replace('__HYPERSOLVE_BINDING__','"stale"').replace('__HYPERSOLVE_GENERATION__','"000"')
            await page.evaluate(stale)
            assert await page.evaluate('window.__hypersolve_generation') == latest
            # An option directly beneath Stop must not receive a physical click on the panel.
            controls = OverlayControls()
            controls.owner = asyncio.current_task()
            await controls.attach(page)
            await HUDInjector.start_scan(page,'missing')
            box = await page.get_by_role('button',name='Stop',exact=True).bounding_box()
            await page.evaluate("""box => {
                const option=document.createElement('div'); option.setAttribute('data-hypersolve-opt','overlap');
                option.style.cssText=`position:fixed;left:${box.x}px;top:${box.y}px;width:${box.width}px;height:${box.height}px`;
                option.setAttribute('role','radio');option.textContent='Covered choice';document.body.appendChild(option);
            }""",box)
            assert await SyntheticInjector.select_option(page,'overlap')
            assert await page.get_by_role('button',name='Stop',exact=True).is_enabled()
            await page.set_viewport_size({"width":390,"height":500})
            await page.evaluate("""() => {
                window.__hypersolve.updateStats(0,20,'SELECTING');
                for(let i=1;i<=20;i++) window.__hypersolve.lockAnswer('missing','missing',null,'Local stub',i,'Long selected answer '.repeat(4));
            }""")
            await asyncio.sleep(.1)
            stop_box = await page.get_by_role('button',name='Stop',exact=True).bounding_box()
            assert stop_box['y'] >= 0 and stop_box['y'] + stop_box['height'] <= 500
            await page.screenshot(path=str(output / 'overlay-small.png'))
            # A new quiz on the same watched Page must not retain prior quiz answers.
            await controls.attach(page)
            assert await page.locator('#__hypersolve_host__ .answers li').count() == 0
            controls.owner = None
            await controls.finish()
            await browser.close()
            print('PASS: persistent harvesting/solving/selection overlay, pause gate, resume, copy, collapse, Stop, restart binding, no iframe duplicates, click overlap protection, small viewport controls')
    finally:
        server.shutdown()
        server.server_close()

if __name__ == '__main__':
    asyncio.run(main())
