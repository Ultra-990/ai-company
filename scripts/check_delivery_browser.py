"""Browser audit of a synthetic delivery report, no production DB writes.

Generated Python runs only in PreviewRunner; HTML/JS only in the existing
opaque sandbox frame. Own loopback bridge and Chrome profile are temporary.
"""
import argparse
import asyncio
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from threading import Thread
from uuid import uuid4
import websockets

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE_ROOT=Path('/home/marcin/ai-company-workspaces')
sys.path.insert(0,str(ROOT))
from app.main import application_frame
from app.services.application_profile import parse_sources
from app.services.application_preview import PreviewRunner,preview_configuration,validate_path


def load_sources(path):
    path=path.resolve()
    base=WORKSPACE_ROOT.resolve()
    if base not in path.parents or path.stat().st_size>2*1024*1024:
        raise ValueError('Expected bounded synthetic workspace report')
    raw=path.read_bytes();report=json.loads(raw)
    if report.get('quality',{}).get('state')!='passed' or not report.get('candidate_created'):
        raise ValueError('Delivery pilot has not passed')
    files=parse_sources(json.dumps({'files':report['final_sources']}))
    return files,sha256(raw).hexdigest()


async def check(source_report,output):
    files,checksum=load_sources(source_report)
    token=secrets.token_urlsafe(24)
    observed=[]
    report={'passed':False,'source_report_sha256':checksum,'requests':observed,
            'production_database_used':False,'owner_accepted':False,
            'binding_kind':'synthetic-report-sha256-not-production-package'}
    class Handler(BaseHTTPRequestHandler):
        def send(self,body,status=200,headers=None):
            self.send_response(status)
            for key,value in (headers or {}).items(): self.send_header(key,value)
            self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/os/application-frame':
                response=application_frame();self.send(response.body,headers=dict(response.headers))
            elif self.path=='/preview.js':
                self.send((ROOT/'app/static/organization-os/application-preview.js').read_bytes(),headers={'Content-Type':'text/javascript'})
            elif self.path=='/':
                html='''<!doctype html><title>Synthetic delivery audit</title>
<p id="message"></p><section id="application-preview" hidden><button id="close-application">Close</button>
<div id="application-host"></div></section><style>iframe{width:100%;height:800px;border:0}</style>
<script src="/preview.js"></script><script>
window.preview=createApplicationPreview({message:t=>document.getElementById('message').textContent=t,
request:async(path,options={})=>{const r=await fetch(path,{...options,headers:{'X-Test-Token':TOKEN,'Content-Type':'application/json'}});if(!r.ok)throw Error('Test bridge '+r.status);return r.json()}});
preview.open({task_id:1,package_id:1,package_checksum:CHECKSUM}).catch(e=>document.getElementById('message').textContent=e.message);
</script>'''.replace('TOKEN',json.dumps(token)).replace('CHECKSUM',json.dumps(checksum))
                self.send(html.encode(),headers={'Content-Type':'text/html; charset=utf-8',
                    'Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; frame-src 'self'; object-src 'none'"})
            elif self.path=='/api/tasks/1/workspace-packages/1' and self.headers.get('X-Test-Token')==token:
                self.send(json.dumps({'checksum':checksum,'files':[{'path':p} for p in files]}).encode(),headers={'Content-Type':'application/json'})
            else:self.send(b'{}',404)
        def do_POST(self):
            if (self.path!='/api/package-runs/preview' or self.headers.get('X-Test-Token')!=token
                    or self.headers.get('Origin')!=base or len(observed)>=8):
                self.send(b'{}',403);return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4096:raise ValueError('size')
                body=json.loads(self.rfile.read(size))
                if (body['task_id'],body['package_id'],body['package_checksum'])!=(1,1,checksum):raise ValueError('binding')
                path=validate_path(body['path'])
                result=PreviewRunner(path).run(files,preview_configuration(),'aic-package-'+uuid4().hex)
                observed.append({'path':path,'run':result})
                if result['exit_code']!=0 or result['reason'] or not result['cleanup_confirmed']:raise ValueError('runner')
                response=json.loads(result['log'])['response']
                self.send(json.dumps({'source_checksum':checksum,'response':response,
                    'assets':{k:v for k,v in files.items() if k in ('app.js','style.css')}}).encode(),headers={'Content-Type':'application/json'})
            except Exception:self.send(b'{"detail":"Preview test failed"}',409,{'Content-Type':'application/json'})
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    base=f'http://127.0.0.1:{server.server_port}'
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    browser=None
    try:
        with tempfile.TemporaryDirectory(prefix='chrome-',dir=output) as profile:
            browser=subprocess.Popen(['/usr/bin/google-chrome','--headless','--disable-gpu',
                '--disable-extensions','--disable-background-networking','--no-first-run',
                '--no-default-browser-check','--remote-debugging-port=0',f'--user-data-dir={profile}',
                'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                for _ in range(100):
                    if (Path(profile)/'DevToolsActivePort').exists():break
                    await asyncio.sleep(.1)
                port,path=(Path(profile)/'DevToolsActivePort').read_text().splitlines()[:2]
                async with websockets.connect(f'ws://127.0.0.1:{port}{path}',max_size=4*1024*1024) as ws:
                    serial=0;events=[]
                    async def call(method,params=None,sid=None):
                        nonlocal serial
                        serial+=1;payload={'id':serial,'method':method,'params':params or {}}
                        if sid:payload['sessionId']=sid
                        await ws.send(json.dumps(payload))
                        while True:
                            reply=json.loads(await asyncio.wait_for(ws.recv(),50))
                            if 'method' in reply:events.append(reply)
                            if reply.get('id')==serial:
                                if 'error' in reply:raise RuntimeError('CDP error')
                                return reply.get('result',{})
                    target=await call('Target.createTarget',{'url':'about:blank'})
                    sid=(await call('Target.attachToTarget',{'targetId':target['targetId'],'flatten':True}))['sessionId']
                    await call('Page.enable',sid=sid);await call('Runtime.enable',sid=sid)
                    await call('Page.navigate',{'url':base+'/'},sid)
                    frame_sid=None;context=None
                    for _ in range(200):
                        targets=(await call('Target.getTargets'))['targetInfos']
                        frame=next((t for t in targets if t['type']=='iframe' and t['url']==base+'/os/application-frame'),None)
                        if frame:
                            frame_sid=(await call('Target.attachToTarget',{'targetId':frame['targetId'],'flatten':True}))['sessionId']
                            await call('Runtime.enable',sid=frame_sid);break
                        tree=await call('Page.getFrameTree',sid=sid)
                        children=tree['frameTree'].get('childFrames',[])
                        if children:
                            frameid=children[0]['frame']['id']
                            contexts=[e['params']['context'] for e in events if e.get('method')=='Runtime.executionContextCreated' and e.get('sessionId')==sid]
                            match=next((c for c in contexts if c.get('auxData',{}).get('frameId')==frameid and c.get('auxData',{}).get('isDefault')),None)
                            if match:frame_sid=sid;context=match['id'];break
                        await asyncio.sleep(.1)
                    assert frame_sid,'No application frame'
                    async def js(expression,frame=True):
                        params={'expression':expression,'returnByValue':True,'awaitPromise':True}
                        if frame and context:params['contextId']=context
                        value=await call('Runtime.evaluate',params,frame_sid if frame else sid)
                        assert 'exceptionDetails' not in value,'Browser expression failed'
                        return value['result'].get('value')
                    async def until(expression):
                        for _ in range(250):
                            if await js(expression):return
                            await asyncio.sleep(.1)
                        raise AssertionError('Browser condition timeout: '+expression)
                    await until("!!document.getElementById('hours') && !!document.getElementById('rate') && !!document.getElementById('discount')")
                    assert await js("(()=>{try{return !parent.document}catch{return true}})()")
                    assert await js("(()=>{try{localStorage.setItem('x','y');return false}catch{return true}})()")
                    for discount,expected in [('10','2318.40'),('','2576.00')]:
                        await js("document.getElementById('hours').value='8';document.getElementById('rate').value='322';document.getElementById('discount').value="+json.dumps(discount)+";document.querySelector('button[type=submit]').click()")
                        await until("document.body.innerText.replaceAll(',','.').includes("+json.dumps(expected)+")")
                    count=len(observed)
                    await js("document.getElementById('hours').value='-1';document.querySelector('button[type=submit]').click()")
                    assert await js("!document.querySelector('form').checkValidity()")
                    assert len(observed)==count,'Invalid form sent request'
                    assert await js("fetch('https://example.invalid/').then(()=>false,()=>true)")
                    await js('preview.close()',False)
                    assert await js("!document.querySelector('iframe')",False)
                    report.update(passed=True,valid_discount_result=True,empty_optional_discount=True,
                        invalid_input_blocked=True,opaque_frame=True,storage_blocked=True,
                        external_fetch_blocked=True,close_removes_frame=True)
            finally:
                browser.terminate()
                try:browser.wait(timeout=5)
                except subprocess.TimeoutExpired:browser.kill();browser.wait(timeout=5)
    except Exception as exc:
        report['error_type']=type(exc).__name__
        raise
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        (output/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report['passed']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    output=Path(tempfile.mkdtemp(prefix='delivery-browser-',dir='/home/marcin/ai-company-workspaces'))
    print(json.dumps({'output':str(output)}),flush=True)
    return 0 if asyncio.run(check(args.report,output)) else 1


if __name__=='__main__':raise SystemExit(main())
