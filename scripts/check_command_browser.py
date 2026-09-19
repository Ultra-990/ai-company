"""Read-only command-center check, private Chrome, software rendering, no tokens.

Live GETs load structure only. Error, XSS and workbench fixtures are confined to
this browser. No model calls, database writes, tenant access or production login.
"""
import argparse
import asyncio
import base64
import json
from pathlib import Path
import subprocess
import tempfile

import websockets


async def check(output):
    with tempfile.TemporaryDirectory(prefix='ai-command-chrome-', ignore_cleanup_errors=True) as profile:
        process = subprocess.Popen([
            '/usr/bin/google-chrome', '--headless', '--disable-gpu', '--disable-extensions',
            '--disable-background-networking', '--no-first-run', '--no-default-browser-check',
            '--remote-debugging-port=0', f'--user-data-dir={profile}', 'about:blank',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            port_file = Path(profile) / 'DevToolsActivePort'
            for _ in range(70):
                if port_file.exists(): break
                await asyncio.sleep(.1)
            port, path = port_file.read_text().splitlines()[:2]
            async with websockets.connect(f'ws://127.0.0.1:{port}{path}', max_size=8*1024*1024) as ws:
                serial = 0
                async def call(method, params=None, session=None):
                    nonlocal serial
                    serial += 1
                    message = {'id':serial, 'method':method, 'params':params or {}}
                    if session: message['sessionId'] = session
                    await ws.send(json.dumps(message))
                    while True:
                        reply = json.loads(await asyncio.wait_for(ws.recv(),15))
                        if reply.get('id') == serial:
                            if 'error' in reply: raise RuntimeError(reply['error'])
                            return reply.get('result',{})
                target = await call('Target.createTarget', {'url':'about:blank'})
                session = (await call('Target.attachToTarget',{'targetId':target['targetId'],'flatten':True}))['sessionId']
                await call('Page.enable',session=session)
                async def js(source):
                    result = await call('Runtime.evaluate',{'expression':source,'returnByValue':True,'awaitPromise':True},session)
                    if 'exceptionDetails' in result: raise RuntimeError(result['exceptionDetails'])
                    return result['result'].get('value')
                async def wait(source):
                    for _ in range(100):
                        if await js(source): return
                        await asyncio.sleep(.1)
                    raise AssertionError(source)
                async def screenshot(name):
                    data = await call('Page.captureScreenshot', {'format':'png'},session)
                    (output/name).write_bytes(base64.b64decode(data['data']))
                await call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False},session)
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/os'},session)
                await call('Page.bringToFront',session=session)
                await wait("document.querySelectorAll('.department-card').length===12 && !document.querySelector('#command-refresh').disabled")
                assert await js("document.querySelector('#command-error').hidden"), 'live API load failed'
                assert await js("document.querySelectorAll('.orb-moon-track').length===2")
                for palette in ('neutral','green','blue'):
                    for theme in ('light','dark'):
                        await js(f"document.querySelector('[data-palette-select]').value='{palette}';document.querySelector('[data-palette-select]').dispatchEvent(new Event('change'));if(document.documentElement.dataset.theme!=='{theme}')document.querySelector('[data-theme-toggle]').click()")
                        await wait("document.documentElement.scrollWidth<=innerWidth")
                        await screenshot(f'{palette}-{theme}.png')
                for orb in ('owner','brain'):
                    point = await js(f"(()=>{{const r=document.querySelector('#command-{orb}').getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
                    await call('Input.dispatchMouseEvent',{'type':'mouseMoved',**point},session)
                    await call('Input.dispatchMouseEvent',{'type':'mousePressed','button':'left','clickCount':1,**point},session)
                    await call('Input.dispatchMouseEvent',{'type':'mouseReleased','button':'left','clickCount':1,**point},session)
                    assert await js("document.querySelector('#command-menu').open")
                    assert await js("document.activeElement.closest('#command-menu')!==null")
                    await screenshot(f'menu-{orb}.png')
                    await call('Input.dispatchKeyEvent',{'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27},session)
                    await call('Input.dispatchKeyEvent',{'type':'keyUp','key':'Escape','code':'Escape','windowsVirtualKeyCode':27},session)
                    assert await js("!document.querySelector('#command-menu').open")
                await js("location.hash='departments'")
                await wait("!document.querySelector('#view-departments').hidden")
                await js("document.querySelector('#command-search').value='strony';document.querySelector('#command-search').dispatchEvent(new Event('input'))")
                assert await js("document.querySelectorAll('.department-card').length>=1 && document.querySelectorAll('.department-card').length<12")
                await js("location.hash='department/finance-legal'")
                await wait("document.querySelector('#department-detail .primary-button')!==null")
                assert await js("document.querySelector('#department-detail .primary-button').getAttribute('href')==='/os/work?unit=finance-legal.budget'")
                await screenshot('department.png')
                await js("history.back()")
                await wait("!document.querySelector('#view-departments').hidden")
                await js("location.hash='delivery'")
                await wait("!document.querySelector('#view-delivery').hidden")
                await screenshot('delivery.png')
                await js("location.hash='overview'")
                await wait("!document.querySelector('#view-overview').hidden")
                await call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True},session)
                assert await js("document.documentElement.scrollWidth<=innerWidth"), 'mobile overflow'
                await screenshot('mobile.png')
                # Error handling must not break menus or replace known data with fake zeroes.
                await js("window.realFetch=window.fetch;window.fetch=async()=>new Response('{}',{status:503});document.querySelector('#command-refresh').click()")
                await wait("!document.querySelector('#command-refresh').disabled")
                assert await js("!document.querySelector('#command-error').hidden && document.querySelector('#metric-projects').textContent==='—'")
                await js("document.querySelector('#command-owner').click()")
                assert await js("document.querySelector('#command-menu').open")
                await js("document.querySelector('#command-menu').close();window.fetch=realFetch;document.querySelector('#command-refresh').click()")
                await wait("!document.querySelector('#command-refresh').disabled")
                assert await js("document.querySelector('#command-error').hidden")
                # Hostile API text is literal, never HTML or an external action link.
                await js("document.querySelector('#command-search').value='';window.fetch=async(url)=>new Response(JSON.stringify(String(url).endsWith('/tree')?{nodes:[{children:[{key:'x',name:'<img src=x onerror=alert(1)>',operating_model:{mission:'test'}}]}]}:String(url).endsWith('/overview')?{projects:0,blocked_tasks:0}:String(url).endsWith('/alerts')?{alerts:[]}:{title:'Próba',reason:'Próba'}));document.querySelector('#command-refresh').click()")
                await wait("!document.querySelector('#command-refresh').disabled")
                assert await js("document.querySelector('#command-departments img')===null && document.querySelector('#command-departments').textContent.includes('<img')")
                await call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]},session)
                assert await js("matchMedia('(prefers-reduced-motion: reduce)').matches")
                for route, opener, dialog, closer in (
                    ('/os/review','open-delivery-center','delivery-center','delivery-close'),
                    ('/os/publishing','open-client-publishing','client-publishing','publishing-close'),
                ):
                    await call('Page.navigate',{'url':'http://127.0.0.1:8000'+route},session)
                    await wait(f"document.readyState==='complete'&&!!document.getElementById('{opener}')")
                    await js(f"document.getElementById('{opener}').click()")
                    assert await js(f"document.getElementById('{dialog}').open")
                    assert await js("document.documentElement.scrollWidth<=innerWidth")
                    await screenshot(dialog+'.png')
                    await js(f"document.getElementById('{closer}').click()")
                    assert await js(f"!document.getElementById('{dialog}').open")
                # Department deep link only preselects a valid option after owner login;
                # fixtures ensure no owner credentials or real work-order mutations.
                await call('Page.addScriptToEvaluateOnNewDocument',{'source':"window.fixtureCalls=[];window.fetch=async(url,opts={})=>{fixtureCalls.push({url,method:opts.method||'GET'});return new Response(JSON.stringify(String(url).endsWith('/options')?{units:[{id:77,key:'finance-legal.budget',name:'Budżet'}]}:{orders:[]} ),{status:200,headers:{'Content-Type':'application/json'}})}"},session)
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/os/work?unit=finance-legal.budget'},session)
                await wait("document.readyState==='complete'&&!!document.querySelector('#token')")
                await js("document.querySelector('#token').value='browser-fixture-only';document.querySelector('#access').dispatchEvent(new Event('submit',{cancelable:true}))")
                await wait("!document.querySelector('#workspace').hidden")
                assert await js("document.querySelector('#unit').value==='77' && fixtureCalls.every(x=>x.method==='GET')")
                print('PASS: 6 themes, 2 sphere menus, department workflow, history, mobile, errors, XSS, reduced motion, review/publishing tools, safe workbench preselection.')
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    output=Path(parser.parse_args().output);output.mkdir(parents=True,exist_ok=True)
    asyncio.run(check(output))
