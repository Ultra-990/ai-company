"""Scoped CDP/browser checks for the pinned LICZNIK LITER full revision."""
import argparse,asyncio,base64,json,os,signal,subprocess,sys,tempfile
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import websockets

from app.services.application_profile import parse_sources
from scripts.check_business_website_browser import WebsiteBrowser,checked_report,evidence_output

SOURCE_SCHEMA='filewise-production-canary-revision.v1'
SOURCE_REPORT_SHA256='859a8d426510d348889ef37b24dd6b4d05f377d6cbcebc0dd776805ef01e8da8'
PACKAGE_ID=10
PACKAGE_CHECKSUM='f54fce4f08227b96b7e2e103f25080aa74224f2254c996145ef5e25f3a47c4b7'
HARNESS_SHA256='f0bdbed665f3cbccea72cf441b226e3ae619e3cf4b084bfd0a0120a11de86d8d'
ORIGIN='https://business-website.test'
DEADLINE=180
VISIBLE_WARNING="""(() => {const e=document.querySelector('.note');if(!e)return false;
 const s=getComputedStyle(e),r=e.getBoundingClientRect(),t=e.innerText;
 return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0
   &&t.includes('file://')&&t.includes('zewnętrznych');})()"""


def checked_sources(report,report_sha256=None):
    revision=report.get('revision',{})
    source=report.get('source',{})
    passed=next((item for item in report.get('tests',[]) if item.get('id')==2),{})
    run=passed.get('result',{})
    try:harness_result=json.loads(run.get('log',''))
    except (TypeError,ValueError,json.JSONDecodeError):harness_result={}
    if (report_sha256 is not None and report_sha256!=SOURCE_REPORT_SHA256
            or report.get('schema')!=SOURCE_SCHEMA or report.get('state')!='awaiting_review'
            or report.get('owner_accepted') is not False or report.get('deployed') is not False
            or report.get('candidate_created') is not False
            or report.get('isolated_test')!={'run_id':2,'state':'passed'}
            or revision.get('new_package_id')!=PACKAGE_ID
            or revision.get('new_package_checksum')!=PACKAGE_CHECKSUM
            or revision.get('test_state')!='passed' or revision.get('accepted') is not False
            or source.get('harness_sha256')!=HARNESS_SHA256
            or passed.get('state')!='passed' or passed.get('package_id')!=PACKAGE_ID
            or run.get('cleanup_confirmed') is not True or run.get('exit_code')!=0
            or run.get('cli_exit_code')!=0 or run.get('reason') is not None
            or run.get('profile',{}).get('harness_checksum')!=HARNESS_SHA256
            or harness_result.get('tests_ok') is not True or harness_result.get('http_ok') is not True
            or harness_result.get('source_not_exposed') is not True or harness_result.get('errors')!=[]):
        raise ValueError('unsupported_canary_revision_report')
    files=report.get('new_sources')
    parse_sources(json.dumps({'files':files},ensure_ascii=False))
    return files


def matching_count_response(requests,start,text,letters):
    matches=[]
    for item in requests[start:]:
        parsed=urlsplit(item.get('path',''))
        if parsed.path!='/api/count' or parse_qs(parsed.query,keep_blank_values=True)!={'text':[text]}:
            continue
        try:
            response=json.loads(item['run']['log'])['response']
            body=json.loads(response['body'])
        except (KeyError,TypeError,ValueError,json.JSONDecodeError):continue
        if response.get('status')==200 and body=={'letters':letters}:matches.append(item)
    return len(matches)==1


def mark_timeout(report):
    report.update(status='incomplete',error_type='TimeoutError',error='bounded_browser_timeout')


def source_assessment(files):
    tests=files['test_app.py']
    return {'six_files':set(files)=={'app.py','test_app.py','index.html','style.css','app.js','README.md'},
        'real_http_server_tests':"ThreadingHTTPServer(('127.0.0.1', 0), app.H)" in tests,
        'test_methods':tests.count('    def test_'),'none_handler_constructor':'H(None' in tests,
        'api_contract':all(value in files['app.py'] for value in
            ('/api/count','keep_blank_values=True','isalpha()','/health','/style.css','/app.js')),
        'ui_contract':all(value in files['index.html']+files['app.js'] for value in
            ('id="text"','id="calculate"','aria-live="polite"','encodeURIComponent','textContent','file://')),
        'characters':{name:len(value) for name,value in files.items()},
        'bytes':{name:len(value.encode('utf-8')) for name,value in files.items()}}


class CanaryBrowser(WebsiteBrowser):
    pass


async def inspect(source,output_name='browser-canary'):
    source=checked_report(source);raw=source.read_bytes();original=json.loads(raw)
    files=checked_sources(original,sha256(raw).hexdigest())
    out=evidence_output(source,output_name);out.mkdir(mode=0o700)
    report={'schema':'filewise-production-canary-browser.v1','status':'running',
        'source_report_sha256':sha256(raw).hexdigest(),'source_assessment':source_assessment(files),
        'checks':[],'requests':[],'blocked_requests':[],'file_mode_requests':[],
        'accepted':False,'visual_assessment':'pending','deployed':False}
    def persist():(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    persist();env={k:v for k,v in os.environ.items() if k not in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS')}
    env['DBUS_SESSION_BUS_ADDRESS']='unix:path=/nonexistent'
    with tempfile.TemporaryDirectory(prefix='browser-',dir=out,ignore_cleanup_errors=True) as profile:
        chrome=subprocess.Popen(['/usr/bin/google-chrome','--headless','--ozone-platform=headless','--hide-scrollbars',
            '--disable-gpu','--disable-extensions','--disable-background-networking','--no-first-run',
            '--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],
            env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        try:
            active=Path(profile)/'DevToolsActivePort'
            for _ in range(100):
                if active.exists():break
                await asyncio.sleep(.1)
            port,path=active.read_text().splitlines()[:2]
            async with websockets.connect('ws://127.0.0.1:'+port+path,max_size=8*1024*1024) as ws:
                scenario={'api_path':'/api/count'}
                b=CanaryBrowser(ws,files,report,persist,scenario)
                target=(await b.call('Target.createTarget',{'url':'about:blank'}))['targetId']
                session=(await b.call('Target.attachToTarget',{'targetId':target,'flatten':True}))['sessionId']
                for method in ('Runtime.enable','Page.enable'):await b.call(method,session=session)
                await b.call('Fetch.enable',{'patterns':[{'urlPattern':'*'}]},session)
                async def size(width):await b.call('Emulation.setDeviceMetricsOverride',
                    {'width':width,'height':900,'deviceScaleFactor':1,'mobile':False},session)
                await size(1440);await b.call('Page.navigate',{'url':ORIGIN+'/'},session)
                ctx=None
                for _ in range(100):
                    await b.call('Runtime.evaluate',{'expression':'1'},session)
                    for candidate in reversed(b.contexts):
                        try:
                            if await b.js('document.readyState==="complete"&&!!document.getElementById("text")',candidate):ctx=candidate;break
                        except RuntimeError:pass
                    if ctx:break
                    await asyncio.sleep(.1)
                if ctx is None:raise ValueError('document_not_loaded')
                async def check(name,expression):
                    actual=await b.js(expression,ctx);report['checks'].append({'name':name,'passed':actual is True,'actual':actual});persist()
                async def shot(name):
                    snap=await b.call('Page.captureScreenshot',{'format':'png'},session)
                    (out/name).write_bytes(base64.b64decode(snap['data']))
                await check('desktop-contract','!!document.querySelector("label[for=text]")&&document.getElementById("result").getAttribute("aria-live")==="polite"&&document.documentElement.scrollWidth<=innerWidth')
                await check('visible-local-warning',VISIBLE_WARNING)
                before=len(report['requests'])
                await b.js("document.getElementById('text').value='Zażółć 123!';document.getElementById('calculate').click()",ctx)
                ok=await b.wait("document.getElementById('result').textContent==='Liczba liter: 6'",ctx,12)
                semantic=matching_count_response(report['requests'],before,'Zażółć 123!',6)
                report['checks'].append({'name':'unicode-encoded-form','passed':ok and semantic});persist()
                before=len(report['requests'])
                await b.js("document.getElementById('text').value='';document.getElementById('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))",ctx)
                await check('empty-client-error',"document.getElementById('result').textContent.includes('Błąd')")
                report['checks'].append({'name':'empty-no-request','passed':len(report['requests'])==before});persist()
                before=len(report['requests'])
                await b.js("document.getElementById('text').value='123-!';document.getElementById('calculate').click()",ctx)
                zero=await b.wait("document.getElementById('result').textContent==='Liczba liter: 0'",ctx,12)
                semantic=matching_count_response(report['requests'],before,'123-!',0)
                report['checks'].append({'name':'nonletters-zero','passed':zero and semantic});persist()
                await shot('desktop.png');await size(390)
                await check('mobile-no-overflow','document.documentElement.scrollWidth<=innerWidth')
                await shot('mobile.png')
                with tempfile.TemporaryDirectory(prefix='file-',dir=out) as local:
                    local=Path(local)
                    for name in ('index.html','style.css','app.js'):(local/name).write_text(files[name],encoding='utf-8')
                    b.file_allowlist={(local/name).resolve().as_uri() for name in ('index.html','style.css','app.js')};b.contexts.clear()
                    ft=(await b.call('Target.createTarget',{'url':'about:blank'}))['targetId']
                    fs=(await b.call('Target.attachToTarget',{'targetId':ft,'flatten':True}))['sessionId']
                    await b.call('Runtime.enable',session=fs);await b.call('Page.enable',session=fs)
                    await b.call('Fetch.enable',{'patterns':[{'urlPattern':'*'}]},fs)
                    await b.call('Page.navigate',{'url':(local/'index.html').resolve().as_uri()},fs)
                    file_ctx=None
                    for _ in range(100):
                        await b.call('Runtime.evaluate',{'expression':'1'},fs)
                        for candidate in reversed(b.contexts):
                            try:
                                if await b.js('document.readyState==="complete"&&!!document.querySelector(".note")',candidate):file_ctx=candidate;break
                            except RuntimeError:pass
                        if file_ctx:break
                        await asyncio.sleep(.1)
                    visible=file_ctx and await b.js(VISIBLE_WARNING,file_ctx)
                    report['checks'].append({'name':'file-warning','passed':visible is True})
                    snap=await b.call('Page.captureScreenshot',{'format':'png'},fs)
                    (out/'file-mode.png').write_bytes(base64.b64decode(snap['data']))
                    persist();b.file_allowlist=None
                report['runtime_errors']=b.errors
                report['status']='passed' if all(item['passed'] for item in report['checks']) and not b.errors and not report['blocked_requests'] else 'failed'
        except asyncio.CancelledError:
            mark_timeout(report);raise
        except Exception as exc:report.update(status='incomplete',error_type=type(exc).__name__,error=str(exc)[:350])
        finally:
            try:os.killpg(chrome.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:chrome.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(chrome.pid,signal.SIGKILL);chrome.wait(timeout=5)
            persist()
    print(json.dumps({'report':str(out/'report.json'),'status':report['status']},ensure_ascii=False));return int(report['status']!='passed')


async def bounded(source,output_name):
    try:return await asyncio.wait_for(inspect(source,output_name),DEADLINE)
    except TimeoutError:return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);parser.add_argument('--output-name',default='browser-canary')
    args=parser.parse_args();raise SystemExit(asyncio.run(bounded(args.report,args.output_name)))
