"""Short, isolated spatial UI check. Software graphics only; no tenant processes.

Reads existing localhost API. UI error fixtures live only in the private browser.
No writes to application data, no owner tokens, no external pages or models.
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
    with tempfile.TemporaryDirectory(prefix='ai-spatial-chrome-', ignore_cleanup_errors=True) as profile:
        process = subprocess.Popen([
            '/usr/bin/google-chrome', '--headless', '--disable-gpu',
            '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
            '--disable-extensions', '--disable-background-networking', '--no-first-run',
            '--no-default-browser-check', '--remote-debugging-port=0',
            f'--user-data-dir={profile}', 'about:blank',
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
                    message = {'id':serial,'method':method,'params':params or {}}
                    if session: message['sessionId']=session
                    await ws.send(json.dumps(message))
                    while True:
                        reply=json.loads(await asyncio.wait_for(ws.recv(),15))
                        if reply.get('id')==serial:
                            if 'error' in reply: raise RuntimeError(reply['error'])
                            return reply.get('result',{})
                target=await call('Target.createTarget',{'url':'about:blank'})
                session=(await call('Target.attachToTarget',{'targetId':target['targetId'],'flatten':True}))['sessionId']
                await call('Page.enable',session=session)
                async def evaluate(js):
                    result=await call('Runtime.evaluate',{'expression':js,'returnByValue':True,'awaitPromise':True},session)
                    if 'exceptionDetails' in result: raise RuntimeError(result['exceptionDetails'])
                    return result['result'].get('value')
                async def wait(js):
                    for _ in range(100):
                        if await evaluate(js):return
                        await asyncio.sleep(.1)
                    raise AssertionError(js)
                async def capture(name):
                    result=await call('Page.captureScreenshot',{'format':'png'},session)
                    (output/name).write_bytes(base64.b64decode(result['data']))
                await call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False},session)
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/os/spatial?graphics=lite'},session)
                await call('Page.bringToFront',session=session)
                await wait("document.querySelectorAll('.spatial-window').length===12")
                await evaluate("document.querySelector('[data-stop=\"0\"]').click()")
                await wait("document.querySelector('#stage').dataset.position==='0.000'")
                await wait("Math.abs(document.querySelector('.scene-sticky').getBoundingClientRect().top-document.querySelector('.app-navigation').offsetHeight)<2")
                await evaluate("if(document.documentElement.dataset.theme!=='dark')document.querySelector('[data-theme-toggle]').click()")
                await capture('spatial-dark-lite.png')
                assert await evaluate("document.documentElement.scrollHeight<6000"), 'artificial scroll runway must be removed'
                assert await evaluate("document.querySelector('.view-switch a[aria-current]').getAttribute('href')==='/os/spatial'")
                far_width=await evaluate("document.querySelector('.spatial-window').getBoundingClientRect().width")
                orb_before=await evaluate("(()=>{const r=document.querySelector('#owner-orb').getBoundingClientRect();return [r.x,r.y,r.width]})()")
                assert await evaluate("[...document.querySelectorAll('.spatial-window')].every(e=>{const m=new DOMMatrix(getComputedStyle(e).transform);return [m.m12,m.m13,m.m21,m.m23,m.m31,m.m32].every(n=>Math.abs(n)<1e-6)})"), 'tilted windows'
                assert await evaluate("document.querySelector('#stage').dataset.renderer==='css3d'")
                await evaluate("window.originalCard=document.querySelector('.spatial-window');document.querySelector('#retry').click()")
                await wait("!document.querySelector('#retry').disabled")
                assert await evaluate("originalCard===document.querySelector('.spatial-window')")
                # Wait for CSS3D's scheduled layout and the browser hit-test compositor.
                await evaluate("new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
                # Trusted wheel over empty stage, not a child window.
                point=await evaluate("(()=>{const r=document.querySelector('#stage').getBoundingClientRect();return {x:Math.min(innerWidth-45,r.right-45),y:Math.min(innerHeight-100,Math.max(170,r.top+r.height/2))}})()")
                await evaluate("window.wheelSeen=[];document.addEventListener('wheel',e=>wheelSeen.push({x:e.clientX,y:e.clientY,target:e.target.id||e.target.className,delta:e.deltaY,prevented:e.defaultPrevented}),{passive:true})")
                await call('Input.dispatchMouseEvent',{'type':'mouseMoved',**point},session)
                await call('Input.dispatchMouseEvent',{'type':'mouseWheel',**point,'deltaX':0,'deltaY':180},session)
                await asyncio.sleep(.2)
                assert await evaluate("document.querySelector('#stage').dataset.position==='0.000'"), 'overview wheel must not pick a department'
                await evaluate("document.querySelector('.window-body h2').click()")
                await wait("document.querySelector('#stage').dataset.position==='1.000'")
                await asyncio.sleep(.4)
                near_width=await evaluate("document.querySelector('.spatial-window').getBoundingClientRect().width")
                assert near_width/far_width>2.5,(far_width,near_width)
                orb_after=await evaluate("(()=>{const r=document.querySelector('#owner-orb').getBoundingClientRect();return [r.x,r.y,r.width]})()")
                assert abs(orb_after[0]-orb_before[0])>10 and orb_after[2]>orb_before[2]*1.5
                frames=await evaluate("document.querySelector('#stage').dataset.frames")
                await asyncio.sleep(.2)
                assert frames==await evaluate("document.querySelector('#stage').dataset.frames"), 'idle frame loop'
                await capture('spatial-focus.png')
                for orb_id in ('owner-orb','brain-orb'):
                    point=await evaluate(f"(()=>{{const r=document.getElementById('{orb_id}').getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
                    await call('Input.dispatchMouseEvent',{'type':'mouseMoved',**point},session)
                    await wait(f"getComputedStyle(document.querySelector('#{orb_id} .orb-moon')).opacity==='1'")
                    first=await evaluate(f"document.querySelector('#{orb_id} .orb-moon').getAttribute('cx')")
                    await asyncio.sleep(.15)
                    assert first!=await evaluate(f"document.querySelector('#{orb_id} .orb-moon').getAttribute('cx')"), 'moon should orbit'
                    await capture(f'spatial-{orb_id}-moon.png')
                    await wait(f"(()=>{{const m=document.querySelector('#{orb_id} .orb-moon');return m.dataset.depth==='behind'&&m.hasAttribute('mask')&&Math.hypot(+m.getAttribute('cx'),+m.getAttribute('cy'))<40}})()")
                    await capture(f'spatial-{orb_id}-moon-behind.png')
                    assert await evaluate(f"document.querySelectorAll('#{orb_id} .planet-ring').length===1")
                    await call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':5,'y':100},session)
                    await wait(f"getComputedStyle(document.querySelector('#{orb_id} .orb-moon')).opacity==='0'")
                point=await evaluate("(()=>{const b=document.querySelector('.window-body');b.scrollTop=0;const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
                await evaluate("window.beforeInner={scrollY,position:document.querySelector('#stage').dataset.position};window.innerEvents=[];document.querySelector('.window-body').addEventListener('wheel',e=>innerEvents.push({prevented:e.defaultPrevented,cancelable:e.cancelable,ctrl:e.ctrlKey,meta:e.metaKey}),{passive:true})")
                await call('Input.dispatchMouseEvent',{'type':'mouseMoved',**point},session)
                await evaluate("new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
                await call('Input.dispatchMouseEvent',{'type':'mouseWheel',**point,'deltaX':0,'deltaY':130},session)
                await wait("Number(document.querySelector('#stage').dataset.zoom)<.9")
                assert await evaluate("document.querySelector('#stage').dataset.position==='1.000'&&scrollY===beforeInner.scrollY"), 'zoom must preserve selection and page position'
                assert await evaluate("[...document.querySelectorAll('.window-body')].every(b=>b.scrollTop===0 && b.scrollHeight<=b.clientHeight+1)"), 'summary cards must not scroll'
                await evaluate("document.querySelector('[data-stop=\"1\"]').click()")
                await wait("document.querySelector('#stage').dataset.position==='1.000'")
                await asyncio.sleep(.7)
                # Drag a header and verify the corresponding relation endpoint follows it.
                await evaluate("window.beforeX=document.querySelector('#fallback-lines line[data-to=\"strategy\"]').getAttribute('x2')")
                point=await evaluate("(()=>{const r=document.querySelector('.window-bar').getBoundingClientRect();return {x:r.x+55,y:r.y+15}})()")
                await call('Input.dispatchMouseEvent',{'type':'mousePressed',**point,'button':'left','clickCount':1},session)
                await call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':point['x']+50,'y':point['y']+25,'button':'left','buttons':1},session)
                await call('Input.dispatchMouseEvent',{'type':'mouseReleased','x':point['x']+50,'y':point['y']+25,'button':'left','clickCount':1},session)
                await wait("document.querySelector('#fallback-lines line[data-to=\"strategy\"]').getAttribute('x2')!==beforeX")
                await evaluate("document.querySelector('.bell').click()")
                assert await evaluate("document.querySelector('#inspector').open && document.querySelector('#inspector-title').textContent.includes('Strategia')")
                await evaluate("document.querySelector('#inspector').close()")
                await asyncio.sleep(.05)
                await evaluate("document.querySelector('#owner-orb').click()")
                assert await evaluate("document.querySelector('#inspector').getAnimations().length>0"), 'missing orb menu animation'
                await evaluate("Promise.all(document.querySelector('#inspector').getAnimations().map(a=>a.finished))")
                assert await evaluate("(()=>{const t=document.querySelector('#inspector-title'),r=t.getBoundingClientRect();return !!document.elementFromPoint(r.x+10,r.y+10).closest('#inspector')})()")
                await capture('spatial-owner.png')
                await evaluate("document.querySelector('#close-inspector').click()")
                assert await evaluate("document.querySelector('#inspector').getAnimations().length>0")
                await wait("!document.querySelector('#inspector').open")
                await evaluate("document.querySelector('#inspector').close();document.querySelector('.min').click()")
                assert await evaluate("document.querySelector('.window-body').hidden")
                await evaluate("document.querySelector('.max').click()")
                assert await evaluate("document.querySelector('#inspector').open")
                assert await evaluate("document.querySelector('#inspector-body').textContent.includes('Fundamenty w repozytorium')&&document.querySelector('#inspector-body').textContent.includes('Co zbudować teraz')"), 'department foundations missing'
                await wait("document.querySelector('#inspector').getAnimations().every(a=>a.playState!=='running')")
                await capture('spatial-department-foundations.png')
                await evaluate("document.querySelector('.tree-child').click()")
                assert await evaluate("document.querySelector('#inspector-title').textContent!=='Strategia i zarządzanie'"), 'subtree not navigable'
                await evaluate("document.querySelector('#inspector-back').click()")
                assert await evaluate("document.querySelector('#inspector-title').textContent==='Strategia i zarządzanie'"), 'back must restore parent view'
                await evaluate("document.querySelector('#inspector-menu').click()")
                assert await evaluate("document.querySelector('#inspector-title').textContent==='Centrum właściciela'"), 'owner menu missing'
                await evaluate("document.querySelector('#inspector').close();document.querySelector('.close').click()")
                assert await evaluate("document.querySelector('.spatial-window').hidden")
                await evaluate("document.querySelector('#reset').click()")
                await wait("document.querySelector('#stage').dataset.position==='0.000'")
                assert await evaluate("!document.querySelector('.spatial-window').hidden && !document.querySelector('.window-body').hidden")
                await evaluate("document.querySelector('[data-theme-toggle]').click()")
                await capture('spatial-light-lite.png')
                # All departments are reachable; native scrolling also exits the scene.
                await evaluate("document.querySelector('[data-stop=\"12\"]').click()")
                await wait("document.querySelector('#stage').dataset.position==='12.000'")
                await capture('spatial-last-department.png')
                await evaluate("document.querySelector('#directory').scrollIntoView()")
                assert await evaluate("document.querySelector('#directory').getBoundingClientRect().top<150")
                await evaluate("document.querySelector('#department-search').value='platforma';document.querySelector('#department-search').dispatchEvent(new Event('input'))")
                assert await evaluate("document.querySelectorAll('.directory-card:not([hidden])').length===1")
                await capture('spatial-directory.png')
                await call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]},session)
                await evaluate("document.querySelector('#owner-orb').focus()")
                assert await evaluate("getComputedStyle(document.querySelector('#owner-orb .orb-moon')).animationName==='none'")
                await evaluate("document.querySelector('[data-stop=\"2\"]').click()")
                await wait("document.querySelector('#stage').dataset.position==='2.000'")
                await call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True},session)
                await asyncio.sleep(.2)
                assert await evaluate("document.documentElement.scrollWidth<=390")
                await capture('spatial-mobile.png')
                # Data failure preserves visible windows and reports stale/unavailable sources.
                await evaluate("window.fetch=async()=>{throw Error('isolated smoke failure')};document.querySelector('#retry').click()")
                await wait("document.querySelector('#sync').textContent.includes('Niepełne')")
                assert await evaluate("document.querySelectorAll('.spatial-window').length===12")
                await call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False},session)
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/os/spatial'},session)
                await wait("document.querySelectorAll('.spatial-window').length===12")
                await evaluate("document.querySelector('[data-stop=\"0\"]').click()")
                mode=await evaluate("document.querySelector('#stage').dataset.renderer")
                await capture('spatial-renderer.png')
                if mode=='webgl':
                    # Verify actual WebGL context loss degrades without removing HTML controls.
                    await evaluate("document.querySelector('#gl-layer canvas').dispatchEvent(new Event('webglcontextlost',{cancelable:true}))")
                    await wait("document.querySelector('#stage').dataset.renderer==='css3d'")
                await evaluate("document.querySelector('#brain-orb').click()")
                assert await evaluate("document.querySelector('#inspector').open")
                await evaluate("document.querySelector('#inspector').close()")
                switch_bounds=await evaluate("(()=>{const r=document.querySelector('.view-switch').getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()")
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/os'},session)
                await wait("document.querySelectorAll('.os-window').length===12")
                assert await evaluate("document.querySelector('.view-switch a[aria-current]').getAttribute('href')==='/os'")
                desktop_bounds=await evaluate("(()=>{const r=document.querySelector('.view-switch').getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()")
                assert all(abs(a-b)<2 for a,b in zip(switch_bounds,desktop_bounds)), (switch_bounds,desktop_bounds)
                await capture('desktop-light.png')
                await evaluate("document.querySelector('[data-theme-toggle]').click()")
                await capture('desktop-dark.png')
                await evaluate("document.querySelector('#owner-orb').click()")
                assert await evaluate("document.querySelector('#owner-menu').open")
                # Fresh startup with unavailable APIs must expose recovery, not a spinner forever.
                await call('Page.addScriptToEvaluateOnNewDocument',{'source':"window.fetch=async()=>{throw Error('isolated initial API failure')}"},session)
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/os/spatial?graphics=lite'},session)
                try:
                    await wait("document.querySelector('#scene-loading')?.textContent.includes('Dane niedostępne')")
                except AssertionError:
                    print('Initial failure diagnostic:',await evaluate("({fetch:String(window.fetch),loader:document.querySelector('#scene-loading')?.textContent,sync:document.querySelector('#sync')?.textContent,hidden:document.hidden})"))
                    raise
                await evaluate("document.querySelector('#owner-shortcut').click()")
                assert await evaluate("document.querySelector('#inspector').open")
                print(json.dumps({'cards':12,'compact_atlas':True,'zoom_ratio':round(near_width/far_width,2),'upright_windows':True,'moving_orbs':True,'occluded_moons':True,'orb_menu_animation':True,'search_and_subtree':True,'selected_wheel_zoom':True,'summary_without_scroll':True,'dialog_back_and_home':True,'drag_links':True,'dialogs':True,'window_controls':True,'persistent_DOM':True,'idle_render_stops':True,'themes':True,'mobile':True,'reduced_motion':True,'API_failure':True,'initial_API_failure':True,'graphics':mode,'GPU':'disabled; SwiftShader only','screenshots':str(output)}))
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    asyncio.run(check(args.output))
