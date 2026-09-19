"""Opt-in browser helper: temporary loopback bridge, private Chrome, synthetic API.

No production DB, owner secrets, host application execution or tenant processes.
"""
import asyncio
import json
from pathlib import Path
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import uuid4

import websockets


async def check(client, body, headers, *, cases=None, expected_color='rgb(0, 0, 255)'):
    cases = cases if cases is not None else [dict(inputs={}, result='2576', path='/api/total')]
    allowed_paths = {case['path'] for case in cases if case['path'] is not None}
    opened = client.post('/api/package-runs/preview', headers=headers, json=body | {'request_id':str(uuid4()),'path':'/'})
    assert opened.status_code == 200, opened.text
    data = opened.json()
    init = json.dumps({'kind':'application-init', 'html':data['response']['body'], 'files':data['assets']}).replace('<','\\u003c')
    parent = ('''<!doctype html><title>Synthetic browser pilot</title>
<iframe id="app" src="/os/application-frame" sandbox="allow-scripts allow-forms"></iframe>
<script>
const frame=document.querySelector('#app');
window.addEventListener('message',async e=>{
 if(e.source!==frame.contentWindow||e.origin!=='null')return;
 if(e.data?.kind==='application-ready'){frame.contentWindow.postMessage(INIT,'*');return;}
 if(e.data?.kind==='application-request'){
  const r=await fetch('/probe',{method:'POST',body:JSON.stringify({path:e.data.path})});
  const reply=await r.json();frame.contentWindow.postMessage({kind:'application-reply',id:e.data.id,...reply},'*');
 }
});</script>''').replace('INIT', init).encode()
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def send(self, content, status=200, extra=None):
            self.send_response(status)
            for key,value in (extra or {}).items():
                if key.lower() not in {'content-length', 'transfer-encoding', 'connection'}:
                    self.send_header(key,value)
            self.send_header('Content-Length',str(len(content)))
            self.end_headers();self.wfile.write(content)
        def do_GET(self):
            if self.path == '/':
                self.send(parent,extra={'Content-Type':'text/html; charset=utf-8'})
            elif self.path == '/os/application-frame':
                response=client.get(self.path)
                self.send(response.content,response.status_code,dict(response.headers))
            else:self.send(b'',404)
        def do_POST(self):
            if self.path!='/probe':self.send(b'{}',404);return
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=1024:self.send(b'{}',413);return
            path=json.loads(self.rfile.read(length)).get('path')
            if path not in allowed_paths:self.send(b'{}',403);return
            response=client.post('/api/package-runs/preview',headers=headers,
                json=body|{'request_id':str(uuid4()),'path':path})
            calls.append(response.status_code)
            self.send(response.content,response.status_code,{'Content-Type':'application/json'})
        def log_message(self,*args):pass

    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix='aic-multifile-browser-') as profile:
            process=subprocess.Popen(['/usr/bin/google-chrome','--headless','--disable-gpu',
                '--disable-extensions','--disable-background-networking','--no-first-run',
                '--no-default-browser-check','--remote-debugging-port=0',f'--user-data-dir={profile}','about:blank'],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                portfile=Path(profile)/'DevToolsActivePort'
                for _ in range(100):
                    if portfile.exists():break
                    await asyncio.sleep(.1)
                port,path=portfile.read_text().splitlines()[:2]
                async with websockets.connect(f'ws://127.0.0.1:{port}{path}') as ws:
                    counter=0;contexts=[]
                    async def call(method,params=None,session=None):
                        nonlocal counter
                        counter+=1;request={'id':counter,'method':method,'params':params or {}}
                        if session:request['sessionId']=session
                        await ws.send(json.dumps(request))
                        while True:
                            reply=json.loads(await asyncio.wait_for(ws.recv(),30))
                            if reply.get('method')=='Runtime.executionContextCreated':
                                contexts.append((reply.get('sessionId'),reply['params']['context']['id']))
                            elif reply.get('method')=='Runtime.executionContextsCleared':
                                contexts[:]=[c for c in contexts if c[0]!=reply.get('sessionId')]
                            elif reply.get('method')=='Runtime.executionContextDestroyed':
                                contexts[:]=[c for c in contexts if c!=(reply.get('sessionId'),reply['params']['executionContextId'])]
                            if reply.get('id')==counter:
                                assert 'error' not in reply,reply
                                return reply.get('result',{})
                    target=(await call('Target.createTarget',{'url':'about:blank'}))['targetId']
                    session=(await call('Target.attachToTarget',{'targetId':target,'flatten':True}))['sessionId']
                    await call('Runtime.enable',session=session)
                    await call('Page.navigate',{'url':f'http://127.0.0.1:{server.server_port}/'},session)
                    async def evaluate(expression, context):
                        reply=await call('Runtime.evaluate',{'expression':expression,'contextId':context[1],'returnByValue':True},context[0])
                        return reply.get('result',{}).get('value')
                    attached={target}
                    context=None
                    for _ in range(100):
                        await asyncio.sleep(.1)
                        # Drain context-created events while requesting a harmless state.
                        await call('Runtime.evaluate',{'expression':'1'},session)
                        # Sandboxed frames may get a separate renderer. Inspect via
                        # DevTools without disabling browser origin/site isolation.
                        targets=(await call('Target.getTargets'))['targetInfos']
                        for info in targets:
                            if info['type']=='iframe' and info['targetId'] not in attached and info.get('url')==f'http://127.0.0.1:{server.server_port}/os/application-frame':
                                child=(await call('Target.attachToTarget',{'targetId':info['targetId'],'flatten':True}))['sessionId']
                                attached.add(info['targetId'])
                                await call('Runtime.enable',session=child)
                        for candidate in reversed(list(contexts)):
                            if await evaluate("!!document.querySelector('#calculate')",candidate):
                                context=candidate;break
                        if context is not None:break
                    assert context is not None,'Application frame not initialized'
                    if expected_color is not None:
                        assert await evaluate("getComputedStyle(document.body).color",context)==expected_color
                    assert await evaluate("(()=>{try{return parent.document.title}catch{return 'isolated'}})()",context)=='isolated'
                    for case in cases:
                        for selector,value in case['inputs'].items():
                            await evaluate(f'document.querySelector({json.dumps(selector)}).value={json.dumps(value)}',context)
                        await evaluate("document.querySelector('#calculate').click()",context)
                        for _ in range(100):
                            await asyncio.sleep(.1)
                            if await evaluate("document.querySelector('#result').textContent",context)==case['result']:break
                        else:raise AssertionError('Browser did not display expected result: '+case['result'])
                    assert calls==[200 for case in cases if case['path'] is not None],calls
                    # Let Chrome flush and close its own renderer/profile processes
                    # before TemporaryDirectory removes the private profile.
                    await ws.send(json.dumps({'id':counter+1,'method':'Browser.close'}))
                    await asyncio.to_thread(process.wait,timeout=5)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
