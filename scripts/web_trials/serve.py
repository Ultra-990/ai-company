"""Read-only isolated browser preview of exact local trial files, with media ranges."""
import argparse
from hashlib import sha256
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import ipaddress
import json
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit
from zipfile import ZipFile, ZipInfo, ZIP_STORED

SITES={'stamps':'Atlas · znaczki','music':'Million Horizons','casino':'Nocturne · gry'}
TYPES={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.mp3':'audio/mpeg','.mp4':'video/mp4'}

def read_files(root):
    files={};archives={};checksums={};total=0
    for site in SITES:
        folder=root/site;manifest=json.loads((folder/'manifest.json').read_text())
        if len(manifest['files'])>80:raise ValueError('Too many files')
        contents={}
        for name,digest in manifest['files'].items():
            if not re.fullmatch(r'[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*\.[a-z0-9]+',name):raise ValueError('Invalid path')
            path=folder/name
            if path.suffix not in TYPES or any(x.is_symlink() for x in [path,*path.parents]):raise ValueError('Unsupported file')
            if path.stat().st_size>40_000_000:raise ValueError('File too large')
            raw=path.read_bytes();total+=len(raw)
            if total>100_000_000 or sha256(raw).hexdigest()!=digest:raise ValueError('Changed or oversized package')
            files[f'/{site}/{name}']=(raw,TYPES[path.suffix]);contents[name]=raw
        out=io.BytesIO()
        with ZipFile(out,'w',ZIP_STORED) as z:
            def write(name,raw):
                info=ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16
                z.writestr(info,raw)
            for name,raw in sorted(contents.items()):write(name,raw)
            write('manifest.json',json.dumps(manifest,sort_keys=True,indent=2))
            write('README.md',(folder/'README.md').read_bytes())
        archives[f'/downloads/{site}.zip']=(out.getvalue(),'application/zip')
        checksums[site]=sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    return files|archives,checksums

def range_bytes(value,size):
    if not value:return None
    m=re.fullmatch(r'bytes=(\d*)-(\d*)',value)
    if not m or not any(m.groups()):raise ValueError('Invalid range')
    left,right=m.groups()
    if not left:
        length=int(right)
        if length<=0:raise ValueError('Invalid suffix')
        return max(0,size-length),size-1
    start=int(left);end=min(size-1,int(right)) if right else size-1
    if start>=size or end<start:raise ValueError('Unsatisfied range')
    return start,end

def handler(files,host):
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):pass
        def reply(self,raw,status=200,kind='text/html; charset=utf-8',extra=None):
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)))
            self.send_header('Connection','close');self.close_connection=True
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',('sandbox allow-scripts allow-forms allow-downloads; ' if self.path.endswith('/index.html') else '')+"default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; frame-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
            for k,v in (extra or {}).items():self.send_header(k,v)
            self.end_headers()
            if self.command!='HEAD':
                try:self.wfile.write(raw)
                except (BrokenPipeError,ConnectionResetError):pass
        def do_HEAD(self):self.do_GET()
        def do_GET(self):
            if self.headers.get('Host')!=host:return self.reply(b'Invalid host',421,'text/plain')
            parsed=urlsplit(self.path)
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:return self.reply(b'Not found',404,'text/plain')
            path=parsed.path
            if path in ['/','/stamps','/music','/casino']:
                selected=path[1:] or 'stamps'
                nav=''.join(f'<a href="/{key}" aria-current="{str(key==selected).lower()}">{html.escape(label)}</a>' for key,label in SITES.items())
                page=f'''<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{SITES[selected]} · podgląd</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#090b10;color:#ccc;font:12px Arial}}nav{{height:43px;display:flex;align-items:center;padding:0 20px;gap:22px;border-bottom:1px solid #333}}a{{color:#aaa;text-decoration:none;padding:10px 0}}a[aria-current=true]{{color:white}}.zip{{margin-left:auto;color:#bcb0de}}iframe{{display:block;border:0;width:100%;height:calc(100svh - 43px)}}@media(max-width:550px){{nav{{font-size:10px;padding:0 10px;gap:14px}}.zip{{font-size:9px}}}}</style><nav aria-label="Projekty testowe">{nav}<a class="zip" href="/downloads/{selected}.zip">Pobierz ZIP ↓</a></nav><iframe title="{SITES[selected]}" src="/{selected}/index.html" sandbox="allow-scripts allow-forms allow-downloads"></iframe></html>'''
                return self.reply(page.encode())
            item=files.get(path)
            if item is None:return self.reply(b'Not found',404,'text/plain')
            raw,kind=item;extra={}
            if path.startswith('/downloads/'):extra['Content-Disposition']='attachment; filename="'+path.rsplit('/',1)[-1]+'"'
            if kind.startswith(('video/','audio/')):
                extra['Accept-Ranges']='bytes'
                try:r=range_bytes(self.headers.get('Range'),len(raw))
                except ValueError:return self.reply(b'',416,kind,{'Content-Range':f'bytes */{len(raw)}'})
                if r:
                    start,end=r;extra['Content-Range']=f'bytes {start}-{end}/{len(raw)}'
                    return self.reply(raw[start:end+1],206,kind,extra)
            return self.reply(raw,200,kind,extra)
        def do_POST(self):self.reply(b'Preview is read-only',405,'text/plain')
    return Handler

def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--bind',default='127.0.0.1');p.add_argument('--port',type=int,default=0);p.add_argument('--minutes',type=int,default=120);a=p.parse_args()
    ip=ipaddress.ip_address(a.bind)
    allowed=ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))
    if not allowed or a.bind=='0.0.0.0' or not 1<=a.minutes<=240:raise ValueError('Loopback/RFC1918 and bounded lifetime required')
    root=a.output.resolve()
    if not root.is_relative_to('/home/marcin/ai-company-workspaces'):raise ValueError('Private Linux workspace required')
    files,checksums=read_files(root)
    server=ThreadingHTTPServer((a.bind,a.port),BaseHTTPRequestHandler)
    server.RequestHandlerClass=handler(files,f'{a.bind}:{server.server_port}')
    timer=threading.Timer(a.minutes*60,server.shutdown);timer.daemon=True;timer.start()
    print(json.dumps({'url':f'http://{a.bind}:{server.server_port}','checksums':checksums,'minutes':a.minutes}),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:timer.cancel();server.server_close()

if __name__=='__main__':main()
