"""Mechanical rendering of validated static SVG in an owned sandboxed Chrome.

No generated Python/JS is executed. No browser profile, desktop or network page
of the owner is used. CDP evaluates only the fixed measurement code below.
"""
import asyncio
import base64
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import websockets

from scripts.vector_school_contract import WIDTH, HEIGHT, validate_svg


def chrome_args(profile):
    return ['/usr/bin/google-chrome', '--headless', '--disable-gpu', '--mute-audio',
            '--disable-extensions', '--disable-background-networking', '--disable-sync',
            '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0',
            '--host-resolver-rules=MAP * ~NOTFOUND', f'--user-data-dir={profile}', 'about:blank']


def chrome_env():
    return {key: value for key, value in os.environ.items()
            if key not in {'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'}}


def document(source):
    validate_svg(source)
    # Fixed export wrapper scales units only for the physical A5 PDF; it does
    # not change the local model's SVG source or layout.
    return '''<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; object-src 'none'; base-uri 'none'; form-action 'none'">
<style>html,body{margin:0;padding:0;width:592px;height:840px;overflow:hidden}
svg{display:block} @page{size:148mm 210mm;margin:0}
@media print{html,body{width:148mm;height:210mm}svg{width:148mm;height:210mm}}</style>
</head><body>''' + source + '</body></html>'


MEASURE = r'''(async()=>{await document.fonts.ready;
return [...document.querySelectorAll('svg>text')].map(el=>{
const b=el.getBBox(),occluded=[],lowContrast=[];
const rgb=value=>{const m=value.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);return m?m.slice(1).map(Number):null;};
const foreground=rgb(getComputedStyle(el).fill);
for(let i=0;i<el.getNumberOfChars();i++){
if(!el.textContent[i].trim())continue;
const c=el.getExtentOfChar(i);
const stack=document.elementsFromPoint(c.x+c.width/2,c.y+c.height/2);
if(stack[0]!==el)occluded.push(i);
const under=stack.find(n=>n!==el&&['rect','circle','ellipse','line','path','text'].includes(n.localName));
const paint=under?getComputedStyle(under):null;
const background=paint?rgb(paint.fill==='none'?paint.stroke:paint.fill):[255,255,255];
if(foreground&&background&&Math.max(...foreground.map((v,j)=>Math.abs(v-background[j])))<24)lowContrast.push(i);
}
return {text:el.textContent,bbox:[b.x,b.y,b.width,b.height],occluded_character_centers:occluded,low_contrast_character_centers:lowContrast,
font_family:getComputedStyle(el).fontFamily,font_size:getComputedStyle(el).fontSize};});})()'''


def pdf_checks(path, texts):
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
    info = subprocess.check_output(['/usr/bin/pdfinfo', str(path)], env=env, text=True, timeout=10)
    extracted = subprocess.check_output(['/usr/bin/pdftotext', '-layout', str(path), '-'],
                                        env=env, text=True, timeout=10)
    fonts = subprocess.check_output(['/usr/bin/pdffonts', str(path)], env=env, text=True, timeout=10)
    images = subprocess.check_output(['/usr/bin/pdfimages', '-list', str(path)], env=env, text=True, timeout=10)
    font_rows = [line.split() for line in fonts.splitlines()[2:] if line.strip()]
    embedded = bool(font_rows and all(len(row) >= 8 and row[-5] == 'yes' for row in font_rows))
    image_count = len([line for line in images.splitlines()[2:] if line.strip()])
    pages = re.search(r'^Pages:\s+(\d+)$', info, re.M)
    size = re.search(r'^Page size:\s+([\d.]+) x ([\d.]+) pts', info, re.M)
    a5 = bool(size and abs(float(size[1])-148/25.4*72) < .5 and abs(float(size[2])-210/25.4*72) < .5)
    same_words = Counter(extracted.split()) == Counter(' '.join(texts).split())
    result = {'pages': int(pages[1]) if pages else None, 'a5_size': a5,
              'text_word_multiset_preserved': same_words, 'text_extraction': extracted,
              'embedded_fonts': embedded, 'actual_font_names': [row[0] for row in font_rows],
              'raster_image_count': image_count,
              'press_preflight_performed': False}
    if result['pages'] != 1 or not a5 or not same_words or not embedded or image_count:
        raise ValueError('PDF page/text export check failed')
    return result


async def render(source, output):
    validated = validate_svg(source)
    wrapper = document(source)
    with tempfile.TemporaryDirectory(prefix='chrome-', dir=output) as profile:
        process = subprocess.Popen(chrome_args(profile), env=chrome_env(),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            async with asyncio.timeout(50):
                active = Path(profile)/'DevToolsActivePort'
                for _ in range(100):
                    if active.exists(): break
                    if process.poll() is not None: raise RuntimeError('Owned Chrome exited')
                    await asyncio.sleep(.1)
                port, path = active.read_text().splitlines()[:2]
                async with websockets.connect(f'ws://127.0.0.1:{port}{path}', max_size=8*1024*1024) as ws:
                    serial = 0
                    async def call(method, params=None, session=None):
                        nonlocal serial
                        serial += 1
                        payload = {'id': serial, 'method': method, 'params': params or {}}
                        if session: payload['sessionId'] = session
                        await ws.send(json.dumps(payload))
                        while True:
                            reply = json.loads(await asyncio.wait_for(ws.recv(), 10))
                            if reply.get('id') == serial:
                                if 'error' in reply: raise RuntimeError('CDP operation failed: '+method)
                                return reply.get('result', {})
                    version = await call('Browser.getVersion')
                    await call('Browser.setDownloadBehavior', {'behavior': 'deny'})
                    target = await call('Target.createTarget', {'url': 'about:blank'})
                    session = (await call('Target.attachToTarget', {'targetId': target['targetId'], 'flatten': True}))['sessionId']
                    await call('Page.enable', session=session)
                    await call('Network.enable', session=session)
                    await call('Network.setBlockedURLs', {'urls': ['*']}, session)
                    await call('Emulation.setDeviceMetricsOverride',
                               {'width': WIDTH, 'height': HEIGHT, 'deviceScaleFactor': 1, 'mobile': False}, session)
                    tree = await call('Page.getFrameTree', session=session)
                    await call('Page.setDocumentContent', {'frameId': tree['frameTree']['frame']['id'], 'html': wrapper}, session)
                    measured = await call('Runtime.evaluate', {'expression': MEASURE, 'returnByValue': True, 'awaitPromise': True}, session)
                    if 'exceptionDetails' in measured: raise RuntimeError('Text measurement failed')
                    layout = measured['result']['value']
                    if [item['text'] for item in layout] != validated['texts']:
                        raise ValueError('Rendered text differs from parsed source')
                    screenshot = await call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False}, session)
                    png = base64.b64decode(screenshot['data'], validate=True)
                    if len(png) > 4*1024*1024: raise ValueError('PNG output limit')
                    (output/'preview.png').write_bytes(png)
                    exported = await call('Page.printToPDF', {'printBackground': True, 'displayHeaderFooter': False,
                        'paperWidth': 148/25.4, 'paperHeight': 210/25.4, 'marginTop': 0, 'marginBottom': 0,
                        'marginLeft': 0, 'marginRight': 0, 'preferCSSPageSize': True, 'scale': 1}, session)
                    pdf = base64.b64decode(exported['data'], validate=True)
                    if not pdf.startswith(b'%PDF-') or len(pdf) > 4*1024*1024: raise ValueError('PDF output limit')
                    (output/'preview.pdf').write_bytes(pdf)
                    result = {'layout': layout, 'browser_version': version, 'static_svg': validated,
                              'pdf': pdf_checks(output/'preview.pdf', validated['texts']),
                              'desktop_used': False, 'sandbox_disabled': False, 'external_page_loaded': False}
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        result['own_browser_stopped'] = process.poll() is not None
        return result
