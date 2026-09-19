"""Real calculator UI + container RPC. No generated Python runs on the host.

Serves only trusted UI on a random loopback port, uses an ephemeral test token,
reads the existing demo package, records real preview runs (no task acceptance).
"""
import asyncio
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import uuid4
import websockets

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.main import app, application_frame, isolated_build_page
from fastapi.testclient import TestClient
from app.api.organization_os import get_organization_session
from app.models.package_run import PackageRun
from app.core.config import load_settings
from app.core.database import create_database_engine, create_session_factory
from app.services.workspace_packages import read_package


async def check():
    factory=create_session_factory(create_database_engine(load_settings().database.url))
    with factory() as session:
        artifact,payload=read_package(session,45,5)
        package={'task_id':45,'artifact_id':5,'checksum':artifact.checksum,'files':payload['files']}
    token=secrets.token_urlsafe(24)
    os.environ['OWNER_API_TOKEN']=token  # This test process only; never printed.
    def sessions():
        with factory() as session:yield session
    app.dependency_overrides[get_organization_session]=sessions
    # Real route serialization, validation, authorization and middleware.
    # No lifespan: do not seed/migrate the live database for a browser test.
    api=TestClient(app)
    observed=[]
    class Handler(BaseHTTPRequestHandler):
        def send(self,body,status=200,headers=None):
            self.send_response(status)
            for k,v in (headers or {}).items():self.send_header(k,v)
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            path=self.path.split('?')[0]
            if path=='/os/build':
                response=isolated_build_page();self.send(Path(response.path).read_bytes(),headers=dict(response.headers))
            elif path=='/os/application-frame':
                response=application_frame();self.send(response.body,headers=dict(response.headers))
            elif path.startswith('/static/organization-os/') and path.rsplit('/',1)[1] in {
                'theme.js','theme.css','work.css','build.js','application-preview.js','application-revisions.js','application-quality.js'}:
                self.send((ROOT/'app'/path.lstrip('/')).read_bytes(),headers={'Content-Type':'text/javascript' if path.endswith('.js') else 'text/css'})
            elif self.headers.get('Authorization')!='Bearer '+token:self.send(b'{}',401)
            elif path in ('/api/package-runs','/api/tasks/45/workspace-packages/5'):
                reply=api.get(path,headers={'Authorization':'Bearer '+token})
                self.send(reply.content,reply.status_code,{'Content-Type':'application/json'})
            else:self.send(b'{}',404)
        def do_POST(self):
            if self.path!='/api/package-runs/preview' or self.headers.get('Authorization')!='Bearer '+token:
                self.send(b'{}',403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<4096:raise ValueError('Request size')
                body=json.loads(self.rfile.read(length));path=body['path']
                if (body['task_id'],body['package_id'],body['package_checksum'])!=(45,5,package['checksum']):raise ValueError('Binding')
                reply=api.post(self.path,json=body,headers={'Authorization':'Bearer '+token})
                if reply.status_code!=200:
                    self.send(reply.content,reply.status_code,{'Content-Type':'application/json'});return
                data=reply.json()
                with factory() as session:
                    run=session.get(PackageRun,data['run_id'])
                    observed.append({'path':path,'run_id':run.id,'state':run.state,'response':data['response'],
                                     'cleanup_confirmed':run.result['cleanup_confirmed']})
                self.send(reply.content,reply.status_code,{'Content-Type':'application/json'})
            except Exception as exc:self.send(json.dumps({'detail':str(exc)}).encode(),409,{'Content-Type':'application/json'})
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    with tempfile.TemporaryDirectory(prefix='aic-app-browser-') as profile:
        browser=subprocess.Popen(['/usr/bin/google-chrome','--headless','--disable-gpu','--disable-extensions',
            '--disable-background-networking','--no-first-run','--no-default-browser-check',
            '--remote-debugging-port=0',f'--user-data-dir={profile}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            port_file=Path(profile)/'DevToolsActivePort'
            for _ in range(100):
                if port_file.exists():break
                await asyncio.sleep(.1)
            port,path=port_file.read_text().splitlines()[:2]
            async with websockets.connect(f'ws://127.0.0.1:{port}{path}',max_size=4*1024*1024) as ws:
                counter=0;events=[]
                async def call(method,params=None,sid=None):
                    nonlocal counter
                    counter+=1;message={'id':counter,'method':method,'params':params or {}}
                    if sid:message['sessionId']=sid
                    await ws.send(json.dumps(message))
                    while True:
                        r=json.loads(await asyncio.wait_for(ws.recv(),70))
                        if 'method' in r:events.append(r)
                        if r.get('id')==counter:
                            if 'error' in r:raise RuntimeError(r['error'])
                            return r.get('result',{})
                target=await call('Target.createTarget',{'url':'about:blank'})
                sid=(await call('Target.attachToTarget',{'targetId':target['targetId'],'flatten':True}))['sessionId']
                await call('Page.enable',sid=sid);await call('Runtime.enable',sid=sid)
                await call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False},sid)
                async def js(source,context=None,session_id=None):
                    params={'expression':source,'returnByValue':True,'awaitPromise':True}
                    if context:params['contextId']=context
                    r=await call('Runtime.evaluate',params,session_id or sid)
                    if 'exceptionDetails' in r:raise RuntimeError(r['exceptionDetails'])
                    return r['result'].get('value')
                async def wait(source):
                    for _ in range(150):
                        if await js(source):return
                        await asyncio.sleep(.1)
                    raise AssertionError(await js("document.querySelector('#message')?.textContent"))
                await call('Page.navigate',{'url':base+'/os/build'},sid)
                await wait("!!document.getElementById('access') && typeof createApplicationPreview==='function'")
                await js("document.getElementById('token').value="+json.dumps(token)+";document.getElementById('access').requestSubmit()")
                await wait("!document.getElementById('workspace').hidden")
                await js("[...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Otwórz aplikację w izolacji').click()")
                await wait("!!document.querySelector('#application-host iframe')")
                frame_context=None;frame_session=sid
                for _ in range(80):
                    tree=await call('Page.getFrameTree',sid=sid)
                    children=tree['frameTree'].get('childFrames',[])
                    if children:
                        frame_id=children[0]['frame']['id']
                        for event in events:
                            if event.get('method')=='Runtime.executionContextCreated':
                                context=event['params']['context']
                                if context.get('auxData',{}).get('frameId')==frame_id and context.get('auxData',{}).get('isDefault'):
                                    frame_context=context['id'];frame_session=event.get('sessionId',sid)
                        if frame_context:break
                    # Opaque sandbox frames can move into a separate renderer and
                    # disappear from the parent Page frame tree (OOPIF).
                    targets=(await call('Target.getTargets'))['targetInfos']
                    for info in targets:
                        if info['type']=='iframe' and '/os/application-frame' in info['url']:
                            fs=(await call('Target.attachToTarget',{'targetId':info['targetId'],'flatten':True}))['sessionId']
                            await call('Runtime.enable',sid=fs)
                            for event in events:
                                if event.get('sessionId')==fs and event.get('method')=='Runtime.executionContextCreated':
                                    context=event['params']['context']
                                    if context.get('auxData',{}).get('isDefault'):
                                        frame_context=context['id'];frame_session=fs
                    if frame_context:break
                    await asyncio.sleep(.1)
                if not frame_context:
                    print(json.dumps({'tree':tree,'targets':(await call('Target.getTargets'))['targetInfos'],
                        'contexts':[e for e in events if e.get('method')=='Runtime.executionContextCreated'],
                        'frame_events':[e for e in events if e.get('method','').startswith('Page.frame')],
                        'message':await js("document.getElementById('message').textContent")},indent=2))
                assert frame_context,'No frame execution context'
                async def frame_js(source):return await js(source,frame_context,frame_session)
                for _ in range(80):
                    if await frame_js("!!document.getElementById('hours')"):break
                    await asyncio.sleep(.1)
                assert await frame_js("!!document.getElementById('hours')"),'No application form'
                assert await frame_js("(()=>{try{return !parent.document}catch{return true}})()"),'Parent DOM accessible'
                assert await frame_js("(()=>{try{localStorage.setItem('x','y');return false}catch{return true}})()"),'Storage accessible'
                await frame_js("document.getElementById('hours').value='8';document.getElementById('rate').value='322';document.querySelector('button[type=submit]').click()")
                for _ in range(300):
                    value=await frame_js("document.getElementById('result').textContent")
                    if '2576' in value:break
                    await asyncio.sleep(.1)
                if value!='Łączny koszt: 2576 zł':
                    print(json.dumps({'observed':observed,'frame':await frame_js("({scripts:[...document.scripts].map(s=>({length:s.textContent.length,src:s.src})),fetch:String(fetch).slice(0,400),form:document.getElementById('estimate-form').outerHTML})"),
                        'exceptions':[e for e in events if e.get('method')=='Runtime.exceptionThrown'],
                        'parent_message':await js("document.getElementById('message').textContent")},indent=2))
                assert value=='Łączny koszt: 2576 zł',value
                # Real invalid-input click: UI must display a useful error, not hang.
                await frame_js("document.getElementById('hours').value='-1';document.querySelector('button[type=submit]').click()")
                for _ in range(300):
                    value=await frame_js("document.getElementById('result').textContent")
                    if 'Błąd:' in value:break
                    await asyncio.sleep(.1)
                assert 'Błąd:' in value,value
                assert await frame_js("fetch('https://example.invalid/').then(()=>false,()=>true)")
                assert await frame_js("fetch('/api/estimate',{method:'POST'}).then(()=>false,()=>true)")
                await js("document.getElementById('logout').click()")
                assert await js("!document.querySelector('#application-host iframe') && document.getElementById('application-preview').hidden")
                assert len(observed)==3 and all(r['cleanup_confirmed'] for r in observed)
                print(json.dumps({'passed':True,'source_checksum':package['checksum'],
                    'scenario':'8 × 322 → Oblicz → Łączny koszt: 2576 zł',
                    'negative_input':True,'opaque_frame':True,'logout_cleans_frame':True,'runs':observed},ensure_ascii=False,indent=2))
        finally:
            browser.terminate()
            try:browser.wait(timeout=5)
            except subprocess.TimeoutExpired:browser.kill();browser.wait(timeout=5)
            server.shutdown();server.server_close();thread.join(timeout=5);api.close()
            app.dependency_overrides.pop(get_organization_session,None)


if __name__=='__main__':asyncio.run(check())
