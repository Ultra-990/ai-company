"""Check automatic local login against the running panel; only session writes and API reads."""
import asyncio
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

import websockets
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.web_trials.check_browser import Browser


async def main():
    env={k:v for k,v in os.environ.items() if k not in {'DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS'}}
    env['DBUS_SESSION_BUS_ADDRESS']='unix:path=/nonexistent'
    with tempfile.TemporaryDirectory(prefix='aic-local-login-',ignore_cleanup_errors=True) as profile:
        process=subprocess.Popen(['/usr/bin/google-chrome','--headless','--ozone-platform=headless',
            '--disable-gpu','--mute-audio','--disable-extensions','--disable-background-networking',
            '--no-first-run','--no-default-browser-check','--remote-debugging-port=0',
            '--user-data-dir='+profile,'about:blank'],env=env,start_new_session=True,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            active=Path(profile)/'DevToolsActivePort'
            for _ in range(100):
                if active.exists():break
                await asyncio.sleep(.1)
            port,path=active.read_text().splitlines()[:2]
            async with websockets.connect('ws://127.0.0.1:'+port+path,max_size=8*1024*1024) as ws:
                b=Browser(ws)
                target=(await b.call('Target.createTarget',{'url':'about:blank'}))['targetId']
                session=(await b.call('Target.attachToTarget',{'targetId':target,'flatten':True}))['sessionId']
                async def js(code):
                    r=await b.call('Runtime.evaluate',{'expression':code,'returnByValue':True,'awaitPromise':True},session)
                    if 'exceptionDetails' in r:raise AssertionError('Browser script exception')
                    return r.get('result',{}).get('value')
                async def wait(code):
                    for _ in range(100):
                        if await js(code):return
                        await asyncio.sleep(.1)
                    raise AssertionError(code)
                checks=[]
                for route in ('/os','/os/work','/os/build','/os/clients','/os/review','/os/publishing','/os/media','/os/upwork'):
                    await b.call('Page.navigate',{'url':'http://127.0.0.1:8000'+route},session)
                    await wait("window.OwnerSession?.active && document.body.dataset.ownerAccess==='local'")
                    assert await js("getComputedStyle(document.querySelector('#owner-session-button')).display==='none'&&document.querySelector('#owner-session-state').textContent==='Właściciel · ten komputer'")
                    assert await js("[...document.querySelectorAll('input[type=password]')].every(x=>!x.getClientRects().length)")
                    assert await js("!document.querySelector('#owner-session-dialog').open")
                    if route in ('/os/work','/os/build','/os/clients'):
                        await wait("!!document.querySelector('#workspace:not([hidden]),#history-workspace:not([hidden])')")
                    checks.append({'page':route,'automatic_local_session':True,'visible_password_fields':False})
                assert await js("(async()=>{const r=await OwnerSession.fetch('/api/owner-session');const s=await r.json();return r.ok&&s.authenticated&&s.mode==='local'&&!document.cookie.includes('ai_company_owner')})()")
                # Clear this browser's cookie to simulate a fresh visit; never print cookie/CSRF.
                await b.call('Network.clearBrowserCookies',session=session)
                await b.call('Page.navigate',{'url':'http://127.0.0.1:8000/os'},session)
                await wait("window.OwnerSession?.active && document.body.dataset.ownerAccess==='local'")
                assert await js("(async()=>{const r=await OwnerSession.fetch('/api/work-orders/options');return r.ok})()")
                print(json.dumps({'passed':True,'pages':checks,'fresh_visit_without_token':True,'protected_read':True,
                                  'httponly':True,'task_writes':False,'model_calls':False}),flush=True)
                await b.call('Browser.close')
                await asyncio.to_thread(process.wait,timeout=5)
        finally:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            await asyncio.sleep(.2)


if __name__=='__main__':asyncio.run(main())
