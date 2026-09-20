"""Trusted FORMA candidate entrypoint; copied into the standalone bundle."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from modules.logic import estimate

ROOT = Path(__file__).parent
# Replaced with a literal allowlist by the assembler, never derived from requests.
PUBLIC = {}


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def reply(self, status, data):
        self.send(status, json.dumps(data).encode(), 'application/json; charset=utf-8')

    def do_GET(self):
        url = urlsplit(self.path)
        if url.scheme or url.netloc or url.fragment:
            return self.reply(400, {'error': 'Invalid path'})
        if url.path == '/health' and not url.query:
            return self.reply(200, {'status': 'ok'})
        if url.path == '/api/estimate':
            try:
                if len(self.path) > 180:
                    raise ValueError()
                query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
                if set(query) != {'service', 'pages', 'rush'} or any(len(v) != 1 for v in query.values()):
                    raise ValueError()
                service, pages, rush = (query[k][0] for k in ('service', 'pages', 'rush'))
                if rush not in ('0', '1') or not pages.isascii() or not pages.isdigit():
                    raise ValueError()
                total = estimate(service, pages, rush == '1')
                return self.reply(200, {'total': total})
            except ValueError:
                return self.reply(400, {'error': 'Podaj usługę, liczbę stron 1–20 i tryb ekspres 0/1.'})
        if url.path in PUBLIC and not url.query:
            name, content_type = PUBLIC[url.path]
            return self.send(200, (ROOT / name).read_bytes(), content_type)
        self.reply(404, {'error': 'Not found'})

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer((os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '8080'))), Handler).serve_forever()
