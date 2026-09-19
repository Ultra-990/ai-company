"""Temporary, loopback-only preview of the synthetic FORMA pilot. No live DB.

Generated Python runs only through the existing restricted container runner.
Generated JS stays in the platform's opaque sandbox frame. Not a deployment.
"""
import argparse
import json
from pathlib import Path
import secrets
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.design_upwork_web_pilot import read_report
from scripts.check_qwen_multifile import checked_report
from scripts.compare_local_models import check_idle
from scripts import upwork_web_case as case
from app.services.multifile_generation import parse_sources
from app.services.multifile_preview import MultifilePreviewRunner, certified_configuration
from hashlib import sha256


def sources(report):
    if (report.get('schema') != 'qwen-multifile-pilot.v1'
            or report.get('scenario') != 'studio' or report.get('status') != 'passed'
            or report.get('brief') != case.BRIEF or report.get('independent_tests') != case.ACCEPTANCE
            or report.get('accepted') is not False or report.get('deployed') is not False):
        raise ValueError('Only the unpublished, backend-tested synthetic studio pilot')
    files = parse_sources(report['generation']['content'])
    if {k: sha256(v.encode()).hexdigest() for k, v in files.items()} != report['source_checksums']:
        raise ValueError('Sources changed')
    return files


def estimate_path(path):
    if not isinstance(path, str) or len(path) > 180:
        raise ValueError('Bounded estimate path required')
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc or parsed.fragment or parsed.path != '/api/estimate':
        raise ValueError('Only local estimate API')
    query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    if set(query) != {'service', 'pages', 'rush'} or any(len(v) != 1 for v in query.values()):
        raise ValueError('Unexpected or repeated parameters')
    if query['service'][0] not in ('landing', 'site') or query['rush'][0] not in ('0', '1'):
        raise ValueError('Unknown service or rush mode')
    if not query['pages'][0].isascii() or not query['pages'][0].isdigit() or not 1 <= int(query['pages'][0]) <= 20:
        raise ValueError('Pages must be 1–20')
    return path


def run_request(files, path):
    check_idle()  # No inference; refuse new workload if other containers appear.
    run = MultifilePreviewRunner(path).run(
        files, certified_configuration() | {'request_path': path}, 'aic-package-' + uuid4().hex)
    result = checked_report(run, 'python-web-multifile-preview.v1')
    return {'response': result['response']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--media-report', type=Path, help='Optional verified local ComfyUI assets')
    parser.add_argument('--minutes', type=int, default=120, choices=range(1, 121))
    args = parser.parse_args(argv)
    report, digest = read_report(args.report)
    files = sources(report)
    # Reuse the platform frame and its existing CSP; no app startup/lifespan.
    from app.main import application_frame
    frame = application_frame()
    opening = run_request(files, '/')
    token = secrets.token_urlsafe(32)  # Preview-only CSRF, never an owner credential.
    html = opening['response']['body']
    frame_files = {k: v for k, v in files.items() if k.endswith(('.css', '.js'))}
    if args.media_report:
        from scripts.studio_gallery import load_assets, enhance
        html, frame_files = enhance(html, frame_files, load_assets(args.media_report))
    init = json.dumps({'kind': 'application-init', 'html': html, 'files': frame_files}).replace('<', '\\u003c')
    parent = ('''<!doctype html><html lang="pl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>FORMA — podgląd Qwen</title>
<style>html,body{margin:0;height:100%;font:14px system-ui;background:#171717;color:#fff}
body{display:flex;flex-direction:column}aside{padding:10px 16px}iframe{border:0;width:100%;flex:1;min-height:0}</style>
<aside>FORMA · rzeczywisty prototyp Qwen · kalkulator działa w izolacji · nie jest to zatwierdzone wydanie</aside>
<iframe title="Strona FORMA" src="/frame" sandbox="allow-scripts allow-forms"></iframe>
<script>const frame=document.querySelector('iframe');
window.addEventListener('message',async e=>{
 if(e.source!==frame.contentWindow||e.origin!=='null')return;
 if(e.data?.kind==='application-ready'){frame.contentWindow.postMessage(INIT,'*');return;}
 if(e.data?.kind!=='application-request')return;
 let reply;try{const r=await fetch('/probe',{method:'POST',headers:{'Content-Type':'application/json','X-Preview-CSRF':TOKEN},body:JSON.stringify({path:e.data.path})});reply=await r.json();}
 catch{reply={error:'Podgląd zakończył się lub jest niedostępny.'};}
 frame.contentWindow.postMessage({kind:'application-reply',id:e.data.id,...reply},'*');
});</script></html>''').replace('TOKEN', json.dumps(token)).replace('INIT', init).encode()

    class Handler(BaseHTTPRequestHandler):
        def send(self, content, status=200, headers=None):
            self.send_response(status)
            for key, value in (headers or {}).items():
                if key.lower() != 'content-length': self.send_header(key, value)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if self.headers.get('Host') != authority:
                self.send(b'', 403); return
            if self.path == '/':
                self.send(parent, headers={'Content-Type': 'text/html; charset=utf-8',
                    'Content-Security-Policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
                    'Referrer-Policy': 'no-referrer'})
            elif self.path == '/frame': self.send(frame.body, headers=dict(frame.headers))
            else: self.send(b'', 404)

        def do_POST(self):
            if (self.path != '/probe' or self.headers.get('Host') != authority
                    or self.headers.get('Origin') != base
                    or self.headers.get('X-Preview-CSRF') != token):
                self.send(b'{"error":"Forbidden"}', 403); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 512: raise ValueError('Request size')
                path = estimate_path(json.loads(self.rfile.read(length))['path'])
                if self.server.requests_left <= 0:
                    self.send(b'{"error":"Limit 60 obliczen podgladu."}', 429); return
                self.server.requests_left -= 1
                reply = run_request(files, path)
                self.send(json.dumps(reply).encode(), headers={'Content-Type': 'application/json'})
            except Exception:
                self.send(b'{"error":"Nie wykonano obliczenia: parametry, zasoby lub izolacja."}', 409,
                          {'Content-Type': 'application/json'})

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args): pass

    with HTTPServer(('127.0.0.1', 0), Handler) as server:
        server.timeout = 1
        server.requests_left = 60
        authority = f'127.0.0.1:{server.server_port}'
        base = 'http://' + authority
        print(json.dumps({'url': base, 'minutes': args.minutes, 'source_sha256': digest,
                          'production_data_changed': False}), flush=True)
        deadline = time.monotonic() + args.minutes * 60
        try:
            while time.monotonic() < deadline: server.handle_request()
        except KeyboardInterrupt: pass
    return 0


if __name__ == '__main__': raise SystemExit(main())
