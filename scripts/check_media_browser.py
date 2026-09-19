"""Private Chrome UI check, all APIs mocked, no GPU/model/real database changes."""
import asyncio
import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import tempfile
from threading import Thread
import websockets

ROOT = Path(__file__).resolve().parents[1]


async def main():
    out = Path(tempfile.mkdtemp(prefix='ai-media-browser-'))
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            if self.path.split('?')[0] == '/os/media':
                self.path = '/templates/organization-os/media.html'
            super().do_GET()
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / 'app')))
    Thread(target=server.serve_forever, daemon=True).start()
    proc = subprocess.Popen(['/usr/bin/google-chrome', '--headless', '--disable-gpu', '--disable-extensions',
        '--disable-background-networking', '--no-first-run', '--no-default-browser-check',
        '--remote-debugging-port=0', f'--user-data-dir={out / "profile"}', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = {'passed': False, 'api_mocked': True, 'gpu': False}
    try:
        path = out / 'profile/DevToolsActivePort'
        for _ in range(80):
            if path.exists(): break
            await asyncio.sleep(.1)
        port, ws_path = path.read_text().splitlines()[:2]
        async with websockets.connect(f'ws://127.0.0.1:{port}{ws_path}', max_size=8*1024*1024) as ws:
            serial = 0
            async def call(method, params=None, session=None):
                nonlocal serial
                serial += 1
                msg = {'id':serial, 'method':method, 'params':params or {}}
                if session: msg['sessionId'] = session
                await ws.send(json.dumps(msg))
                while True:
                    data = json.loads(await asyncio.wait_for(ws.recv(), 15))
                    if data.get('id') == serial:
                        if 'error' in data: raise RuntimeError(data['error'])
                        return data.get('result', {})
            target = await call('Target.createTarget', {'url':'about:blank'})
            session = (await call('Target.attachToTarget', {'targetId':target['targetId'], 'flatten':True}))['sessionId']
            async def js(code):
                data = await call('Runtime.evaluate', {'expression':code, 'returnByValue':True, 'awaitPromise':True}, session)
                if 'exceptionDetails' in data: raise RuntimeError(data['exceptionDetails'])
                return data['result'].get('value')
            async def wait(code):
                for _ in range(100):
                    if await js(code): return
                    await asyncio.sleep(.1)
                raise AssertionError(code)
            await call('Page.enable', session=session)
            await call('Page.addScriptToEvaluateOnNewDocument', {'source':r'''
window.calls=[];window.jobs=[];
const nativeFetch=window.fetch.bind(window);
window.fetch=async(path,options={})=>{
 if(!String(path).startsWith('/api/'))return nativeFetch(path,options);
 calls.push([path,options.method||'GET']);
 if(path==='/api/owner-session')return Response.json({authenticated:true,csrf:'fixture-csrf',expires_at:Date.now()/1000+3600});
 if(path==='/api/tasks/1')return Response.json({id:1,title:'Grafika demonstracyjna',status:'pending',approval_status:'approved'});
 if(path==='/api/tasks/1/images'){
   if(options.method==='POST'){const input=JSON.parse(options.body);jobs.push({id:1,state:'queued',inputs:input,review:'pending',artifact_id:null});return Response.json(jobs[0]);}
   return Response.json({jobs});
 }
 if(path.endsWith('/refresh')){jobs[0].state='succeeded';jobs[0].artifact_id=7;return Response.json(jobs[0]);}
 if(path.endsWith('/report'))return Response.json({artifact_checksum:'a'.repeat(64),image_sha256:'b'.repeat(64),checks:{png_dimensions:true},visual_reviewed:false});
 if(path.endsWith('/download')){const canvas=document.createElement('canvas');canvas.width=768;canvas.height=512;const c=canvas.getContext('2d');c.fillStyle='#eef2ee';c.fillRect(0,0,768,512);c.fillStyle='#1d64bb';c.beginPath();c.arc(384,250,130,0,Math.PI*2);c.fill();return new Response(await new Promise(r=>canvas.toBlob(r,'image/png')));}
 if(path.endsWith('/review')){jobs[0].review=JSON.parse(options.body).decision;return Response.json(jobs[0]);}
 return Response.json({detail:'fixture route absent'},{status:404});
};
'''}, session)
            await call('Emulation.setDeviceMetricsOverride', {'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False}, session)
            await call('Page.navigate', {'url':f'http://127.0.0.1:{server.server_port}/os/media?task=1'}, session)
            await wait('window.OwnerSession?.active')
            await js("document.querySelector('#select-task').requestSubmit()")
            await wait("!document.querySelector('#generate').hidden&&!document.querySelector('#refresh').disabled")
            await js("document.querySelector('#prompt').value='<img onerror=alert(1)> blue sphere';document.querySelector('#confirm').checked=true;document.querySelector('#generate').requestSubmit()")
            await wait("document.querySelector('#jobs').textContent.includes('Obraz zapisany')&&!document.querySelector('#refresh').disabled")
            assert await js("calls.filter(([p,m])=>p==='/api/tasks/1/images'&&m==='POST').length===1&&!document.querySelector('#jobs img')")
            await js("document.querySelector('#jobs button').click()")
            await wait("!document.querySelector('#result').hidden&&document.querySelector('#image').naturalWidth===768")
            await js("document.querySelector('#reason').value='Sprawdzono zgodność z briefem';document.querySelector('#review').requestSubmit()")
            await wait("document.querySelector('#jobs').textContent.includes('accepted')&&!document.querySelector('#refresh').disabled")
            assert await js("document.querySelector('#review').hidden")
            for theme in ('light', 'dark'):
                await js(f"if(document.documentElement.dataset.theme!=='{theme}')document.querySelector('[data-theme-toggle]').click();document.querySelector('#result').scrollIntoView()")
                shot = await call('Page.captureScreenshot', {'format':'png'}, session)
                (out / f'media-{theme}.png').write_bytes(base64.b64decode(shot['data']))
            for width in (390, 768):
                await call('Emulation.setDeviceMetricsOverride', {'width':width,'height':900,'deviceScaleFactor':1,'mobile':width==390}, session)
                assert await js('document.documentElement.scrollWidth<=innerWidth'), width
            report.update(passed=True, login_session=True, single_submit=True, image_preview=True,
                          review=True, text_safety=True, responsive=True, light_dark=True)
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
        server.shutdown(); server.server_close()
        (out / 'report.json').write_text(json.dumps(report, indent=2))
        print(json.dumps({'report':str(out / 'report.json'), **report}))


if __name__ == '__main__': asyncio.run(main())
