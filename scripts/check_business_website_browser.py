"""Headless checks of exact model sources; Python runs only via container RPC."""
import argparse
import asyncio
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import websockets
from scripts.web_trials.check_browser import Browser
from scripts.compare_local_models import check_idle
from app.services.application_preview import PreviewRunner, preview_configuration
from scripts.workshop_catalog_case import SESSIONS as WORKSHOP_SESSIONS

ORIGIN = 'https://business-website.test'
WORKSPACE = Path('/home/marcin/ai-company-workspaces')
BROWSER_DEADLINE_SECONDS = 180
RUNTIME_NOTE_VISIBLE = """(() => {
    const e=document.getElementById('runtime-note');
    if (!e) return false;
    const style=getComputedStyle(e), box=e.getBoundingClientRect();
    return style.display!=='none' && style.visibility!=='hidden'
        && box.width>0 && box.height>0 && e.innerText.includes('python app.py');
})()"""
SCENARIOS = {
    'business-website-delivery.v1': {
        'name': 'rowerownia', 'report_schema': 'business-website-browser.v1',
        'api_path': '/api/estimate', 'brand_pattern': 'rowerownia',
        'section_ids': ('services', 'estimate', 'faq', 'contact'),
        'field_ids': ('service', 'bikes', 'express'), 'faq_id': 'faq-service',
        'result_prefix': 'Wycena', 'file_mode': False,
        'quotes': (('basic', '1', False, 90), ('full', '3', True, 690),
                   ('basic', '8', True, 1120))},
    'service-quote-transfer-delivery.v1': {
        'name': 'service-crema', 'report_schema': 'service-quote-transfer-browser.v1',
        'api_path': '/api/quote', 'brand_pattern': 'serwis crema',
        'section_ids': ('services', 'quote', 'faq', 'contact'),
        'field_ids': ('plan', 'machines', 'onsite'), 'faq_id': 'faq-process',
        'result_prefix': 'Szacunkowo', 'file_mode': True, 'viewport_menu_checks': True,
        # Browser-only interaction values differ from the frozen harness probes.
        'quotes': (('check', '2', False, 170), ('restore', '1', True, 305),
                   ('restore', '6', True, 1480))},
    'workshop-catalog-delivery.v1': {
        'name': 'workshop-catalog', 'report_schema': 'workshop-catalog-browser.v1',
        'api_path': '/api/sessions', 'brand_pattern': 'plan zajęć',
        'section_ids': ('catalog', 'schedule', 'faq', 'contact'),
        'field_ids': ('day', 'level'), 'action_id': 'apply-filters',
        'output_ids': ('sessions', 'filter-status'), 'live_ids': ('filter-status',),
        'faq_id': 'faq-filtering', 'file_mode': True, 'viewport_menu_checks': True,
        # Browser-only filters differ from the frozen harness probes.
        'filters': (
            ('tuesday', 'beginner', (WORKSHOP_SESSIONS[2],)),
            ('saturday', 'advanced', (WORKSHOP_SESSIONS[5],)),
            ('tuesday', 'intermediate', ()),
        ),
        'all_titles': ('Papierowy ogród','Historie z gliny','Błękitna cyjanotypia',
                       'Notes szyty ręcznie','Roślinny druk','Mały drzeworyt')},
}
SCENARIOS['workshop-catalog-ui-repair.v1'] = SCENARIOS['workshop-catalog-delivery.v1']
SCENARIOS['workshop-catalog-route-repair.v1'] = SCENARIOS['workshop-catalog-delivery.v1']
SCENARIOS['workshop-catalog-route-refinement.v1'] = SCENARIOS['workshop-catalog-delivery.v1']
# These reports preserve the same ROWEROWNIA UI/API contract at later workflow
# stages. Their provenance differs, while the browser expectations do not.
for _business_schema in ('business-website-resume.v1', 'business-website-revision.v1',
                         'business-website-edge-repair.v1'):
    SCENARIOS[_business_schema] = SCENARIOS['business-website-delivery.v1']
SCENARIOS['service-quote-transfer-revision.v1'] = SCENARIOS['service-quote-transfer-delivery.v1']
SCENARIOS['service-quote-transfer-ui-repair.v1'] = SCENARIOS['service-quote-transfer-delivery.v1']


def scenario_for(report):
    schema = report.get('schema') if isinstance(report, dict) else None
    try: return SCENARIOS[schema]
    except KeyError: raise ValueError('Unsupported website delivery report schema') from None


def checked_report(source):
    source = Path(source).absolute()
    if any(path.is_symlink() for path in (source, *source.parents)):
        raise ValueError('Browser evidence cannot use symlink paths')
    resolved = source.resolve(strict=True)
    workspace = WORKSPACE.resolve(strict=True)
    if (not resolved.is_relative_to(workspace) or not resolved.is_file()
            or resolved.stat().st_dev != workspace.stat().st_dev
            or resolved.stat().st_size > 8 * 1024 * 1024):
        raise ValueError('Browser report must be a bounded file in the Linux workspace')
    return resolved


def evidence_output(source, output_name):
    if not re.fullmatch(r'browser(?:-[a-z0-9]+)*', output_name):
        raise ValueError('Invalid browser evidence directory name')
    return source.parent / output_name


MENU_CLOSED = """(() => {
    const toggle = document.getElementById('menu-toggle');
    const links = [...document.querySelectorAll('#site-nav a')];
    if (toggle?.getAttribute('aria-expanded') !== 'false' || !links.length) return false;
    return links.every(link => {
        const r = link.getBoundingClientRect();
        const style = getComputedStyle(link);
        if (r.width > 0 && r.height > 0 && style.visibility !== 'hidden'
            && style.visibility !== 'collapse' && style.display !== 'none') return false;
        link.focus();
        return document.activeElement !== link;
    });
})()"""


def quote_interaction(scenario, choice, count, enabled):
    first_field, count_field, boolean_field = scenario['field_ids']
    return "{const flag=document.getElementById("+json.dumps(boolean_field)+");" \
        + "document.getElementById("+json.dumps(first_field)+").value="+json.dumps(choice)+";" \
        + "document.getElementById("+json.dumps(count_field)+").value="+json.dumps(count)+";" \
        + "if(flag.type==='checkbox'){flag.checked="+json.dumps(enabled)+";}else{" \
        + "flag.value="+json.dumps('1' if enabled else '0')+";}" \
        + "document.getElementById('calculate').click()}"


def filter_interaction(scenario, day, level):
    day_id,level_id=scenario['field_ids']
    return "document.getElementById("+json.dumps(day_id)+").value="+json.dumps(day)+";" \
        + "document.getElementById("+json.dumps(level_id)+").value="+json.dumps(level)+";" \
        + "document.getElementById("+json.dumps(scenario['action_id'])+").click()"


def filter_expectation(expected_sessions, all_titles):
    wanted=[row['title'] for row in expected_sessions]
    unwanted=[title for title in all_titles if title not in wanted]
    return """(() => {const list=document.getElementById('sessions');
        const status=document.getElementById('filter-status');const text=list?.innerText||'';
        const wanted=__WANTED__;const unwanted=__UNWANTED__;
        return !!list && !!status?.innerText.trim() && wanted.every(x=>text.includes(x))
            && unwanted.every(x=>!text.includes(x)) && (wanted.length>0 || text.trim().length>0);})()""" \
        .replace('__WANTED__',json.dumps(wanted,ensure_ascii=False)) \
        .replace('__UNWANTED__',json.dumps(unwanted,ensure_ascii=False))


def matching_filter_response(requests, start, scenario, day, level, expected_sessions):
    matches=[]
    expected_pairs=sorted((('day',day),('level',level)))
    for item in requests[start:]:
        parsed=urlsplit(item.get('path',''))
        pairs=parse_qsl(parsed.query,keep_blank_values=True)
        if parsed.path!=scenario['api_path'] or len(pairs)!=2 or sorted(pairs)!=expected_pairs:
            continue
        try:
            raw=json.loads(item['run']['log'])['response']
            body=json.loads(raw['body'])
        except (KeyError,TypeError,ValueError,json.JSONDecodeError):
            continue
        if raw.get('status')==200 and body=={'sessions':list(expected_sessions)}:
            matches.append(item)
    return len(matches)==1


def backend_response(files, path):
    check_idle()
    profile = preview_configuration()
    run = PreviewRunner(path).run(files, profile, 'aic-package-' + uuid4().hex)
    report = json.loads(run['log'])
    if (run.get('exit_code') != 0 or run.get('cli_exit_code') != 0
            or run.get('cleanup_confirmed') is not True or run.get('reason') is not None
            or run.get('profile') != profile or report.get('schema') != 'python-web-preview.v1'
            or not isinstance(report.get('response'), dict)
            or type(report['response'].get('status')) is not int
            or not isinstance(report['response'].get('body'), str)):
        raise ValueError('Isolated backend preview failed')
    return report['response'], run


class WebsiteBrowser(Browser):
    def __init__(self, ws, files, report, persist, scenario):
        super().__init__(ws)
        self.files, self.report, self.persist, self.scenario = files, report, persist, scenario
        self.file_allowlist = None

    async def call(self, method, params=None, session=None):
        self.serial += 1
        wanted = self.serial
        payload = {'id': wanted, 'method': method, 'params': params or {}}
        if session: payload['sessionId'] = session
        await self.ws.send(json.dumps(payload))
        while True:
            r = json.loads(await asyncio.wait_for(self.ws.recv(), 60))
            if r.get('method') == 'Fetch.requestPaused':
                p = r['params']; request = p['request']; url = urlsplit(request['url'])
                body = None; status = 200; kind = 'text/plain'
                request_url = request['url']
                if self.file_allowlist is not None:
                    allowed = request['method'] == 'GET' and request_url in self.file_allowlist
                    self.report['file_mode_requests'].append({'url': request_url[:300], 'allowed': allowed})
                    self.persist()
                    self.serial += 1
                    reply = {'id': self.serial, 'sessionId': r['sessionId'],
                             'method': 'Fetch.continueRequest' if allowed else 'Fetch.failRequest',
                             'params': {'requestId': p['requestId']}}
                    if not allowed: reply['params']['errorReason'] = 'BlockedByClient'
                    await self.ws.send(json.dumps(reply))
                    continue
                local = url.scheme == 'https' and url.netloc == 'business-website.test'
                if local and request['method'] == 'GET':
                    name = 'index.html' if url.path == '/' else url.path.lstrip('/')
                    if not url.query and name in ('index.html', 'style.css', 'app.js') and name in self.files:
                        body = self.files[name]
                        kind = {'index.html': 'text/html; charset=utf-8', 'style.css': 'text/css', 'app.js': 'text/javascript'}[name]
                    elif url.path == self.scenario['api_path']:
                        path = url.path + ('?' + url.query if url.query else '')
                        response, run = await asyncio.to_thread(backend_response, self.files, path)
                        self.report['requests'].append({'path': path, 'run': run})
                        self.persist()
                        body, status, kind = response['body'], response['status'], 'application/json'
                self.serial += 1
                reply = {'id': self.serial, 'sessionId': r['sessionId'],
                         'method': 'Fetch.fulfillRequest' if body is not None else 'Fetch.failRequest',
                         'params': {'requestId': p['requestId']}}
                if body is None:
                    reply['params']['errorReason'] = 'BlockedByClient'
                    if url.path != '/favicon.ico': self.report['blocked_requests'].append(request['url'][:180])
                else:
                    reply['params'].update(responseCode=status, body=base64.b64encode(body.encode()).decode(),
                        responseHeaders=[{'name': 'Content-Type', 'value': kind},
                            {'name': 'Content-Security-Policy', 'value': "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-src 'none'"}])
                await self.ws.send(json.dumps(reply))
            if r.get('method') == 'Runtime.executionContextCreated':
                self.contexts.append((r.get('sessionId'), r['params']['context']['id']))
            if r.get('method') == 'Runtime.exceptionThrown':
                self.errors.append(r['params']['exceptionDetails'].get('text', 'exception'))
            if r.get('id') == wanted:
                if 'error' in r: raise RuntimeError(str(r['error']))
                return r.get('result', {})


async def inspect(source, output_name='browser'):
    source = checked_report(source)
    raw = source.read_bytes(); original = json.loads(raw)
    scenario = scenario_for(original)
    files = original['final_sources']
    # Validate without importing or executing generated Python.
    from app.services.application_profile import parse_sources
    parse_sources(json.dumps({'files': files}))
    out = evidence_output(source, output_name)
    out.mkdir(mode=0o700)  # Never overwrite earlier evidence.
    report = {'schema': scenario['report_schema'], 'scenario': scenario['name'], 'status': 'running',
              'examiner_version': '2026-10-11.catalog.v4',
              'examiner_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_report_sha256': sha256(raw).hexdigest(),
              'source_sha256': {n: sha256(s.encode()).hexdigest() for n, s in files.items()},
              'checks': [], 'requests': [], 'blocked_requests': [], 'file_mode_requests': [],
              'accepted': False, 'visual_review': 'pending', 'deployed': False}
    def persist(): (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    persist()
    env = {k:v for k,v in os.environ.items() if k not in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS')}
    env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=/nonexistent'
    with tempfile.TemporaryDirectory(prefix='browser-', dir=out, ignore_cleanup_errors=True) as profile:
        chrome = subprocess.Popen(['/usr/bin/google-chrome','--headless','--ozone-platform=headless','--hide-scrollbars',
            '--disable-gpu','--disable-extensions','--disable-background-networking','--no-first-run',
            '--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            active = Path(profile)/'DevToolsActivePort'
            for _ in range(100):
                if active.exists(): break
                await asyncio.sleep(.1)
            port, path = active.read_text().splitlines()[:2]
            async with websockets.connect('ws://127.0.0.1:'+port+path, max_size=8*1024*1024) as ws:
                b = WebsiteBrowser(ws, files, report, persist, scenario)
                target = (await b.call('Target.createTarget', {'url':'about:blank'}))['targetId']
                session = (await b.call('Target.attachToTarget', {'targetId':target,'flatten':True}))['sessionId']
                await b.call('Runtime.enable', session=session)
                await b.call('Page.enable', session=session)
                await b.call('Fetch.enable', {'patterns':[{'urlPattern':'*'}]}, session)
                async def size(width):
                    await b.call('Emulation.setDeviceMetricsOverride', {'width':width,'height':1000,'deviceScaleFactor':1,'mobile':False}, session)
                await size(1440)
                await b.call('Page.navigate', {'url':ORIGIN+'/'}, session)
                ctx = None
                for _ in range(100):
                    await b.call('Runtime.evaluate', {'expression':'1'}, session)
                    for candidate in reversed(b.contexts):
                        try:
                            if await b.js('document.readyState==="complete" && !!document.querySelector("main")', candidate): ctx=candidate; break
                        except RuntimeError: pass
                    if ctx: break
                    await asyncio.sleep(.1)
                if ctx is None: raise ValueError('Document did not load')
                async def check(name, expression):
                    try:
                        actual = await b.js(expression, ctx)
                        report['checks'].append({'name':name,'passed':actual is True,'actual':actual})
                    except RuntimeError as exc:
                        report['checks'].append({'name':name,'passed':False,'error':str(exc)[:300]})
                    persist()
                async def shot(name, full_page=False):
                    await asyncio.sleep(.15)
                    params = {'format': 'png'}
                    if full_page:
                        layout = await b.call('Page.getLayoutMetrics', session=session)
                        content = layout['cssContentSize']
                        if not 0 < content['height'] <= 16000 or not 0 < content['width'] <= 2000:
                            raise ValueError('Full-page screenshot exceeds bounded dimensions')
                        params.update(captureBeyondViewport=True, clip={
                            'x': 0, 'y': 0, 'width': content['width'],
                            'height': content['height'], 'scale': 1})
                    snap = await b.call('Page.captureScreenshot', params, session)
                    (out/name).write_bytes(base64.b64decode(snap['data']))
                action_id=scenario.get('action_id','calculate')
                output_ids=scenario.get('output_ids',('result',))
                live_ids=scenario.get('live_ids',('result',))
                required = ('main', *scenario['section_ids'], 'site-nav', 'menu-toggle',
                            *scenario['field_ids'], action_id, *output_ids, scenario['faq_id'])
                await check('required-content', json.dumps(list(required))+".every(id=>document.getElementById(id)) && document.querySelectorAll('h1').length===1 && new RegExp("+json.dumps(scenario['brand_pattern'])+",'i').test(document.body.innerText)")
                await check('labelled-fields', json.dumps(list(scenario['field_ids']))+".every(id=>document.getElementById(id)?.labels?.length) && "+json.dumps(list(live_ids))+".every(id=>document.getElementById(id)?.getAttribute('aria-live')==='polite')")
                await check('desktop-no-overflow', 'document.documentElement.scrollWidth<=innerWidth')
                await check('navigation', json.dumps(list(scenario['section_ids']))+".every(id=>document.querySelector('#site-nav a[href=\"#'+id+'\"]')) && !!document.querySelector('a[href=\"#main\"]')")
                if 'filters' in scenario:
                    # Added after reviewing the initial empty catalogue. This is
                    # a separate UI acceptance check, not a changed API harness.
                    initial=await b.wait(filter_expectation(WORKSHOP_SESSIONS,scenario['all_titles']),ctx,12)
                    report['checks'].append({'name':'initial-catalog','passed':initial,
                        'scope':'All six sessions and a status must be visible before interaction.'})
                    persist()
                await shot('desktop.png')
                await shot('desktop-full.png', full_page=True)
                if 'quotes' in scenario:
                    for choice, count, enabled, total in scenario['quotes']:
                        before = len(report['requests'])
                        await b.js(quote_interaction(scenario, choice, count, enabled), ctx)
                        matched = await b.wait('document.getElementById("result").textContent.trim()==='+json.dumps(f"{scenario['result_prefix']}: {total} PLN"), ctx, 12)
                        report['checks'].append({'name':f'quote-{choice}-{count}-{enabled}','passed':matched and len(report['requests'])>before})
                        persist()
                else:
                    for day,level,expected_sessions in scenario['filters']:
                        before=len(report['requests']);await b.js(filter_interaction(scenario,day,level),ctx)
                        expression=filter_expectation(expected_sessions,scenario['all_titles'])
                        matched=await b.wait(expression,ctx,12)
                        response_ok=matching_filter_response(report['requests'],before,scenario,day,level,expected_sessions)
                        report['checks'].append({'name':f'filter-{day}-{level}','passed':matched and response_ok})
                        persist()
                await b.js("document.querySelector("+json.dumps('#'+scenario['faq_id']+' summary')+").click()", ctx)
                await check('faq-opens', "document.getElementById("+json.dumps(scenario['faq_id'])+").open")
                await size(390)
                await b.js('scrollTo(0,0)', ctx)
                await check('mobile-no-overflow', 'document.documentElement.scrollWidth<=innerWidth')
                report['closed_menu_geometry'] = await b.js("""(() => {
                    const box = e => { const r = e.getBoundingClientRect(); return {
                        width:r.width, height:r.height, top:r.top, left:r.left,
                        display:getComputedStyle(e).display, visibility:getComputedStyle(e).visibility}; };
                    return {nav:box(document.getElementById('site-nav')),
                        links:[...document.querySelectorAll('#site-nav a')].map(box)};
                })()""", ctx)
                await check('mobile-menu-closed', MENU_CLOSED)
                await shot('mobile.png')
                await shot('mobile-full.png', full_page=True)
                await b.js("document.getElementById('menu-toggle').click()", ctx)
                await check('mobile-menu-open', "document.getElementById('menu-toggle').getAttribute('aria-expanded')==='true' && document.getElementById('site-nav').getClientRects().length>0")
                if scenario.get('viewport_menu_checks'):
                    await check('mobile-menu-links-in-viewport', """(() => {
                        const links = [...document.querySelectorAll('#site-nav a')];
                        return links.length > 0 && links.every(link => {
                            const r = link.getBoundingClientRect();
                            const s = getComputedStyle(link);
                            if (r.width <= 0 || r.height <= 0 || s.visibility !== 'visible'
                                || r.top < 0 || r.left < 0 || r.bottom > innerHeight || r.right > innerWidth) return false;
                            const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
                            return hit === link || link.contains(hit);
                        });
                    })()""")
                await b.call('Input.dispatchKeyEvent', {'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27}, session)
                await check('mobile-escape', "document.getElementById('menu-toggle').getAttribute('aria-expanded')==='false' && document.activeElement.id==='menu-toggle'")
                if scenario.get('viewport_menu_checks'):
                    await check('mobile-escape-hides-links', """(() => {
                        const links = [...document.querySelectorAll('#site-nav a')];
                        return links.length > 0 && links.every(link => {
                            const r = link.getBoundingClientRect();
                            return r.width === 0 || r.height === 0 || getComputedStyle(link).visibility === 'hidden';
                        });
                    })()""")
                if scenario['file_mode']:
                    with tempfile.TemporaryDirectory(prefix='file-preview-', dir=out) as local:
                        local = Path(local)
                        selected = {name: files[name] for name in ('index.html','style.css','app.js')}
                        for name, content in selected.items(): (local/name).write_text(content, encoding='utf-8')
                        allowed = {(local/name).resolve().as_uri() for name in selected}
                        report['file_mode_source_sha256'] = {
                            name: sha256(content.encode()).hexdigest() for name, content in selected.items()}
                        b.file_allowlist = allowed; b.contexts.clear()
                        file_target = (await b.call('Target.createTarget', {'url':'about:blank'}))['targetId']
                        file_session = (await b.call('Target.attachToTarget', {'targetId':file_target,'flatten':True}))['sessionId']
                        await b.call('Runtime.enable', session=file_session); await b.call('Page.enable', session=file_session)
                        await b.call('Fetch.enable', {'patterns':[{'urlPattern':'*'}]}, file_session)
                        await b.call('Emulation.setDeviceMetricsOverride', {'width':390,'height':900,'deviceScaleFactor':1,'mobile':False}, file_session)
                        await b.call('Page.navigate', {'url':(local/'index.html').resolve().as_uri()}, file_session)
                        file_ctx = None
                        for _ in range(100):
                            await b.call('Runtime.evaluate', {'expression':'1'}, file_session)
                            for candidate in reversed(b.contexts):
                                try:
                                    if await b.js('document.readyState==="complete" && !!document.getElementById("runtime-note")', candidate): file_ctx=candidate;break
                                except RuntimeError: pass
                            if file_ctx: break
                            await asyncio.sleep(.1)
                        if file_ctx is None: raise ValueError('File-mode document did not load')
                        visible = await b.js(RUNTIME_NOTE_VISIBLE, file_ctx)
                        disabled = await b.js("document.getElementById("+json.dumps(action_id)+")?.disabled===true", file_ctx)
                        unauthorized = [item for item in report['file_mode_requests'] if not item['allowed']]
                        report['checks'].append({'name':'file-mode-safe','passed':visible is True and disabled is True and not unauthorized,
                            'runtime_note_visible':visible,'calculate_disabled':disabled,'unauthorized_requests':unauthorized})
                        snap = await b.call('Page.captureScreenshot', {'format':'png'}, file_session)
                        (out/'file-mode.png').write_bytes(base64.b64decode(snap['data']))
                        b.file_allowlist = None; persist()
                report['runtime_errors'] = b.errors
                report['status'] = 'passed' if all(c['passed'] for c in report['checks']) and not b.errors and not report['blocked_requests'] else 'failed'
        except asyncio.CancelledError:
            report.update(status='incomplete', error_type='TimeoutError',
                          error='Bounded browser deadline reached')
            raise
        except Exception as exc:
            report.update(status='incomplete', error_type=type(exc).__name__, error=str(exc)[:350])
        finally:
            try: os.killpg(chrome.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try: chrome.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(chrome.pid, signal.SIGKILL); chrome.wait(timeout=5)
            persist()
    print(json.dumps({'report':str(out/'report.json'),'status':report['status'],'checks':report['checks']},ensure_ascii=False))
    return int(report['status'] != 'passed')


async def bounded_inspect(source, output_name='browser'):
    try:
        return await asyncio.wait_for(inspect(source, output_name), timeout=BROWSER_DEADLINE_SECONDS)
    except TimeoutError:
        print(json.dumps({'report': str(evidence_output(source, output_name)/'report.json'),
                          'status': 'incomplete', 'error': 'bounded_browser_timeout'}))
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output-name', default='browser', help='new browser evidence folder; never overwrite')
    args = parser.parse_args()
    raise SystemExit(asyncio.run(bounded_inspect(args.report, args.output_name)))
