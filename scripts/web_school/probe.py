"""Independent browser examiner. Never imports or executes submitted JS on host."""
import asyncio
import base64
from hashlib import sha256
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time

import websockets
from scripts.web_trials.check_browser import Browser
from scripts.web_trials.serve import handler, TYPES
from scripts.web_school.contract import catalog


def examiner_hash():
    return sha256(Path(__file__).read_bytes() + Path(__file__).with_name('contract.py').read_bytes()).hexdigest()


class ExaminerBrowser(Browser):
    """Fail closed for all page requests outside the three exact local sources."""
    def __init__(self, ws, allowed):
        super().__init__(ws)
        self.allowed = allowed
        self.blocked = []

    async def call(self, method, params=None, session=None):
        self.serial += 1
        wanted = self.serial
        payload = {'id': wanted, 'method': method, 'params': params or {}}
        if session:
            payload['sessionId'] = session
        await self.ws.send(json.dumps(payload))
        while True:
            r = json.loads(await asyncio.wait_for(self.ws.recv(), 20))
            if r.get('method') == 'Fetch.requestPaused':
                p = r['params']; url = p['request']['url']
                allowed = url in self.allowed and p['request']['method'] == 'GET'
                # Chrome requests this even when the author supplied no favicon.
                # Block it, but do not count browser-generated housekeeping as a defect.
                favicon = url == next(iter(self.allowed)).split('/stamps/')[0]+'/favicon.ico'
                if not allowed and not favicon:
                    self.blocked.append(url[:180])
                self.serial += 1
                reply = {'id': self.serial, 'sessionId': r['sessionId'],
                         'method': 'Fetch.continueRequest' if allowed else 'Fetch.failRequest',
                         'params': {'requestId': p['requestId']}}
                if not allowed:
                    reply['params']['errorReason'] = 'BlockedByClient'
                await self.ws.send(json.dumps(reply))
            if r.get('method') == 'Runtime.executionContextCreated':
                self.contexts.append((r.get('sessionId'), r['params']['context']['id']))
            if r.get('method') == 'Runtime.exceptionThrown':
                self.errors.append(r['params']['exceptionDetails'])
            if r.get('id') == wanted:
                if 'error' in r:
                    raise RuntimeError(str(r['error']))
                return r.get('result', {})


async def inspect(url, out, variant):
    checks = []
    report = {'checks': checks, 'passed': False, 'examiner_sha256': examiner_hash(),
              'visual_accepted': False, 'test_kind': 'development_feedback_not_holdout'}
    env = {k:v for k,v in os.environ.items() if k not in {'DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS'}}
    env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=/nonexistent'
    with tempfile.TemporaryDirectory(prefix='chrome-', dir=out, ignore_cleanup_errors=True) as profile:
        process = subprocess.Popen(['/usr/bin/google-chrome', '--headless', '--ozone-platform=headless',
            '--disable-gpu', '--mute-audio', '--disable-extensions', '--disable-background-networking',
            '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0',
            '--user-data-dir='+profile, 'about:blank'], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            active = Path(profile)/'DevToolsActivePort'
            for _ in range(100):
                if active.exists(): break
                await asyncio.sleep(.1)
            port, path = active.read_text().splitlines()[:2]
            async with websockets.connect('ws://127.0.0.1:'+port+path, max_size=8*1024*1024) as ws:
                b = ExaminerBrowser(ws, {url+'/stamps/'+n for n in ('index.html','style.css','app.js')})
                target = (await b.call('Target.createTarget', {'url':'about:blank'}))['targetId']
                session = (await b.call('Target.attachToTarget', {'targetId':target, 'flatten':True}))['sessionId']
                await b.call('Runtime.enable', session=session)
                await b.call('Page.enable', session=session)
                await b.call('Fetch.enable', {'patterns':[{'urlPattern':'*'}]}, session)
                await b.call('Emulation.setDeviceMetricsOverride', {'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False}, session)
                await b.call('Page.navigate', {'url':url+'/stamps/index.html'}, session)
                ctx = None
                for _ in range(80):
                    await asyncio.sleep(.1)
                    await b.call('Runtime.evaluate', {'expression':'1'}, session)
                    for candidate in reversed(b.contexts):
                        try:
                            if await b.js('document.readyState==="complete" && !!document.querySelector("h1")', candidate):
                                ctx = candidate; break
                        except RuntimeError: pass
                    if ctx: break
                if ctx is None: raise RuntimeError('No loaded document with h1')
                async def check(name, expression):
                    try:
                        actual = await b.js(expression, ctx)
                        checks.append({'name':name, 'passed':actual is True, 'actual':actual})
                    except RuntimeError as exc:
                        checks.append({'name':name, 'passed':False, 'error':str(exc)[:700]})
                async def do(expression):
                    # Failed actions do not silently skip assertions or end the suite.
                    # A real SELECT commit emits both input and change, bubbling.
                    # Accept implementations listening to either native event.
                    expression = re.sub(r"(document\.querySelector\('[^']+'\))\.dispatchEvent\(new Event\('change'\)\)",
                        r"(()=>{const el=\1;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));})()",
                        expression)
                    try: await b.js(expression, ctx)
                    except RuntimeError as exc:
                        checks.append({'name':'runtime-action', 'passed':False, 'error':str(exc)[:700]})
                async def shot(name):
                    r = await b.call('Page.captureScreenshot', {'format':'png','captureBeyondViewport':False}, session)
                    (out/name).write_bytes(base64.b64decode(r['data']))
                data = catalog(variant)
                required = ['menu-toggle','site-menu','country','category','search','sort','clear','empty',
                            'products','gallery','detail','prev','next','close-gallery','add','cart-count',
                            'cart-total','cart','checkout','receipt']
                await check('catalog-required-controls', '(()=>{const missing='+json.dumps(required)+
                            '.filter(id=>!document.getElementById(id));return missing.length?{missing}:true})()')
                await check('catalog-all-cards', '''(()=>{const expected='''+json.dumps(data)+''';const cards=[...document.querySelectorAll('#products .product')];return cards.length===expected.length&&expected.every(p=>{const c=cards.find(x=>x.dataset.id===p.id);return c&&Number(c.dataset.price)===p.price&&c.dataset.country===p.country&&c.dataset.category===p.category&&c.textContent.includes(p.title)&&c.textContent.includes(String(p.price))&&c.querySelector('[data-open="'+p.id+'"]')})})()''')
                await check('catalog-labels', "[...document.querySelectorAll('input,select')].every(x=>x.labels?.length||x.getAttribute('aria-label'))")
                await shot('desktop.png')
                for country in ['Polska','Kanada','Japonia']:
                    await do("document.querySelector('#country').value="+json.dumps(country)+";document.querySelector('#country').dispatchEvent(new Event('change'))")
                    ids = [p['id'] for p in data if p['country']==country]
                    await check('filters-country-'+country, "JSON.stringify([...document.querySelectorAll('#products .product')].map(x=>x.dataset.id))==="+json.dumps(json.dumps(ids,separators=(',',':'))))
                # Intersect two controls with one match, then an empty intersection/search.
                category = data[1]['category']
                await do("document.querySelector('#category').value="+json.dumps(category)+";document.querySelector('#category').dispatchEvent(new Event('change'))")
                ids = [p['id'] for p in data if p['country']=='Japonia' and p['category']==category]
                await check('filters-intersection', "JSON.stringify([...document.querySelectorAll('#products .product')].map(x=>x.dataset.id))==="+json.dumps(json.dumps(ids,separators=(',',':'))))
                await do("document.querySelector('#clear').click();document.querySelector('#search').value='  kAnAdA  ';document.querySelector('#search').dispatchEvent(new Event('input'))")
                await check('search-trim-case', "document.querySelectorAll('#products .product').length===2&&[...document.querySelectorAll('#products .product')].every(x=>x.dataset.country==='Kanada')")
                await do("document.querySelector('#search').value='NO-MATCH-987';document.querySelector('#search').dispatchEvent(new Event('input'))")
                await check('search-empty-state', "document.querySelectorAll('#products .product').length===0&&!document.querySelector('#empty').hidden&&getComputedStyle(document.querySelector('#empty')).display!=='none'")
                await do("document.querySelector('#clear').click()")
                await check('search-clear', "document.querySelectorAll('#products .product').length===12&&['country','category','search'].every(id=>document.getElementById(id).value==='')&&document.querySelector('#empty').hidden")
                for direction in ['asc','desc']:
                    await do("document.querySelector('#sort').value='price-"+direction+"';document.querySelector('#sort').dispatchEvent(new Event('change'))")
                    ids = [p['id'] for p in sorted(data,key=lambda p:p['price'], reverse=direction=='desc')]
                    await check('filters-sort-'+direction, "JSON.stringify([...document.querySelectorAll('#products .product')].map(x=>x.dataset.id))==="+json.dumps(json.dumps(ids,separators=(',',':'))))
                await do("document.querySelector('#country').value='Polska';document.querySelector('#country').dispatchEvent(new Event('change'));document.querySelector('#products [data-open]').click()")
                ordered = sorted([p for p in data if p['country']=='Polska'], key=lambda p:p['price'],reverse=True)
                for i in range(3):
                    p = ordered[i%len(ordered)]
                    await check('gallery-filtered-cycle-'+str(i), "document.querySelector('#gallery').open&&document.querySelector('#gallery').dataset.id==="+json.dumps(p['id'])+"&&document.querySelector('#detail').textContent.includes("+json.dumps(p['title'])+")")
                    if i<2: await do("document.querySelector('#next').click()")
                await do("document.querySelector('#prev').click()")
                await check('gallery-prev', "document.querySelector('#gallery').dataset.id==="+json.dumps(ordered[1]['id']))
                await do("document.querySelector('#close-gallery').click();document.querySelector('#clear').click();document.querySelector('[data-open=s01]').click();document.querySelector('#add').click();document.querySelector('#add').click()")
                await check('cart-single-stock', "document.querySelector('#cart-count').textContent.trim()==='1'&&Number(document.querySelector('#cart-total').textContent)==="+str(data[0]['price']))
                await do("if(document.querySelector('#gallery').open)document.querySelector('#close-gallery').click();document.querySelector('[data-open=s04]').click();document.querySelector('#add').click();if(document.querySelector('#gallery').open)document.querySelector('#close-gallery').click()")
                await check('cart-two-items', "document.querySelectorAll('#cart .cart-row').length===2&&document.querySelector('#cart-count').textContent.trim()==='2'&&Number(document.querySelector('#cart-total').textContent)==="+str(data[0]['price']+data[3]['price']))
                await do("document.querySelector('#checkout').click()")
                await check('receipt-demo', "(()=>{const r=document.querySelector('#receipt');return !r.hidden&&/nie.*(pobr|pobier)|bez.*płat/i.test(r.textContent)&&/nie.*wys[łl]|bez.*wys/i.test(r.textContent)?true:{receipt_hidden:r.hidden,receipt_text:r.textContent,clicked_checkout_tag:document.querySelector('#checkout').tagName}})()")
                await do("document.querySelector('[data-remove=s01]').click()")
                await check('cart-remove-recalculate', "document.querySelector('#cart-count').textContent.trim()==='1'&&Number(document.querySelector('#cart-total').textContent)==="+str(data[3]['price']))
                await check('receipt-invalidated', "document.querySelector('#receipt').hidden")
                await do("document.querySelector('[data-remove=s04]').click()")
                await check('cart-empty-disables-checkout', "(()=>{const e=document.querySelector('#checkout');return document.querySelector('#cart-count').textContent.trim()==='0'&&Number(document.querySelector('#cart-total').textContent)===0&&e.disabled===true?true:{checkout_tag:e.tagName,checkout_disabled:e.disabled??null,count:document.querySelector('#cart-count').textContent,total:document.querySelector('#cart-total').textContent}})()")
                for width in [390,768,320]:
                    await b.call('Emulation.setDeviceMetricsOverride', {'width':width,'height':844,'deviceScaleFactor':1,'mobile':False}, session)
                    await do("scrollTo({top:0,behavior:'instant'})")
                    await asyncio.sleep(.15)
                    await check('overflow-'+str(width), 'document.documentElement.scrollWidth<=innerWidth+1')
                    if width==390: await shot('mobile.png')
                await check('menu-initially-closed', "document.querySelector('#menu-toggle').getAttribute('aria-expanded')==='false'")
                await do("document.querySelector('#menu-toggle').click()")
                await check('menu-open', "(()=>{const n=document.querySelector('#site-menu'),s=getComputedStyle(n),expanded=document.querySelector('#menu-toggle').getAttribute('aria-expanded');return expanded==='true'&&!!n.getClientRects().length&&s.visibility!=='hidden'?true:{expanded,nav_class:n.className,header_class:n.closest('header')?.className,display:s.display,visibility:s.visibility}})()")
                await do("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
                await check('menu-escape', "document.querySelector('#menu-toggle').getAttribute('aria-expanded')==='false'&&(!document.querySelector('#site-menu').getClientRects().length||getComputedStyle(document.querySelector('#site-menu')).visibility==='hidden')")
                await b.call('Emulation.setEmulatedMedia', {'features':[{'name':'prefers-reduced-motion','value':'reduce'}]}, session)
                await check('motion-reduced', "matchMedia('(prefers-reduced-motion:reduce)').matches&&getComputedStyle(document.documentElement).scrollBehavior==='auto'&&[...document.querySelectorAll('*')].every(x=>parseFloat(getComputedStyle(x).animationDuration)<=.01)")
                report['browser_exceptions'] = b.errors
                report['blocked_requests'] = b.blocked
                checks.append({'name':'runtime-clean','passed':not b.errors and not b.blocked,
                               'exceptions':b.errors,'blocked_requests':b.blocked})
                await b.call('Browser.close')
                await asyncio.to_thread(process.wait, timeout=5)
        except Exception as exc:
            checks.append({'name':'runtime-examiner','passed':False,'error':str(exc)[:700]})
        finally:
            # Only the process group created above, never the desktop browser.
            try: os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
            await asyncio.sleep(.2)
    report['temporary_profile_removed'] = not Path(profile).exists()
    report['passed'] = bool(checks) and all(c['passed'] for c in checks)
    return report


def examine(files, out, variant=0):
    contents = {'/stamps/'+n:(s.encode(), TYPES[Path(n).suffix]) for n,s in files.items()}
    server = ThreadingHTTPServer(('127.0.0.1',0), handler({}, 'unused'))
    server.RequestHandlerClass = handler(contents, f'127.0.0.1:{server.server_port}')
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        result = asyncio.run(asyncio.wait_for(inspect(f'http://127.0.0.1:{server.server_port}',out,variant), 120))
        result['source_sha256'] = {n:sha256(s.encode()).hexdigest() for n,s in files.items()}
        return result
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
