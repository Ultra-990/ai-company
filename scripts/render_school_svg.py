"""Mechanical rendering of validated static SVG in an owned sandboxed Chrome.

No generated Python/JS is executed. No browser profile, desktop or network page
of the owner is used. CDP evaluates only the fixed measurement code below.
"""
import asyncio
import base64
from collections import Counter
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

import websockets

from scripts.vector_school_contract import WIDTH, HEIGHT, PROFILES, validate_svg


def chrome_args(profile):
    return ['/usr/bin/google-chrome', '--headless', '--disable-gpu', '--mute-audio',
            '--disable-extensions', '--disable-background-networking', '--disable-sync',
            '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0',
            '--host-resolver-rules=MAP * ~NOTFOUND', f'--user-data-dir={profile}', 'about:blank']


def chrome_env():
    return {key: value for key, value in os.environ.items()
            if key not in {'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'}}


@contextmanager
def owned_profile(output):
    profile = tempfile.mkdtemp(prefix='chrome-', dir=output)
    try:
        yield profile
    finally:
        # Chrome descendants can finish a profile write just after their parent
        # exits. Retry only removal of this invocation's own temporary directory.
        for attempt in range(20):
            try:
                shutil.rmtree(profile)
                break
            except FileNotFoundError:
                break
            except OSError as exc:
                if exc.errno != errno.ENOTEMPTY or attempt == 19: raise
                time.sleep(.1)


def stop_owned_chrome(process):
    # Popen creates a new session below: this group contains only this browser.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try: os.killpg(process.pid, sig)
        except ProcessLookupError: pass
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if sig == signal.SIGKILL: raise


def document(source, *, profile='leaflet'):
    validate_svg(source, profile=profile)
    # Fixed export wrapper scales units only for the physical A5 PDF; it does
    # not change the local model's SVG source or layout.
    wrapper = '''<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; object-src 'none'; base-uri 'none'; form-action 'none'">
<style>html,body{margin:0;padding:0;width:592px;height:840px;overflow:hidden}
svg{display:block} @page{size:148mm 210mm;margin:0}
@media print{html,body{width:148mm;height:210mm}svg{width:148mm;height:210mm}}</style>
</head><body>'''
    if profile != 'leaflet':
        spec = PROFILES[profile]
        wrapper = (wrapper.replace('592px', str(spec['width'])+'px').replace('840px', str(spec['height'])+'px')
                   .replace('148mm', str(spec['size_mm'][0])+'mm').replace('210mm', str(spec['size_mm'][1])+'mm')
                   .replace('svg{', 'body>svg{'))
    return wrapper + source + '</body></html>'


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


# The original center-only contrast sample misses bars crossing the top or
# bottom of a label. Keep this additional measurement separate so historical
# render reports and other profiles retain their original contract.
SOURCE_LABEL_MEASURE = r'''(()=>{
const rgb=value=>{const m=value.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);return m?m.slice(1).map(Number):null;};
return [...document.querySelectorAll('svg>text')].map(el=>{
const foreground=rgb(getComputedStyle(el).fill),bad=new Set();
for(let i=0;i<el.getNumberOfChars();i++){
if(!el.textContent[i].trim())continue;
const c=el.getExtentOfChar(i);
for(const fx of [.2,.5,.8])for(const fy of [.15,.5,.85]){
const stack=document.elementsFromPoint(c.x+c.width*fx,c.y+c.height*fy);
const under=stack.find(n=>n!==el&&['rect','circle','ellipse','line','path','text'].includes(n.localName));
const paint=under?getComputedStyle(under):null;
const background=paint?rgb(paint.fill==='none'?paint.stroke:paint.fill):[255,255,255];
if(foreground&&background&&Math.max(...foreground.map((v,j)=>Math.abs(v-background[j])))<24)bad.add(i);
}
}
return {text:el.textContent,character_indices:[...bad]};
});})()'''

# Source objects are flat, bounded SVG shapes. A small interior grid detects
# parts that exist in JSON but are entirely painted over by later shapes.
SOURCE_PART_MEASURE = r'''(()=>{
const shapes=[...document.querySelectorAll('svg>rect,svg>circle,svg>ellipse,svg>line,svg>path')];
const members=new Set(shapes);
return shapes.map((el,index)=>{
const b=el.getBoundingClientRect();let visible=0;
for(const fx of [.1,.3,.5,.7,.9])for(const fy of [.1,.3,.5,.7,.9]){
const front=document.elementsFromPoint(b.x+b.width*fx,b.y+b.height*fy).find(n=>members.has(n));
if(front===el)visible++;
}
return {index,fill:getComputedStyle(el).fill,visible_samples:visible,tested_samples:25};
});})()'''

PANEL_LINE_MEASURE = r'''(()=>{
const productPaint=point=>{
const shape=document.elementsFromPoint(...point).find(n=>n.parentElement?.localName==='g'&&['rect','circle','ellipse','line','path'].includes(n.localName));
return shape?getComputedStyle(shape).fill:null;
};
const contactPaint=point=>[...new Set(Array.from({length:8},(_,i)=>{
const angle=i*Math.PI/4;
return productPaint([point[0]+Math.cos(angle),point[1]+Math.sin(angle)]);
}).filter(color=>color&&color!=='none'))];
const routePaint=(start,end)=>{
const steps=Math.min(2048,Math.max(2,Math.ceil(Math.hypot(end[0]-start[0],end[1]-start[1])/2)));
return [...new Set(Array.from({length:steps+1},(_,i)=>{
const t=i/steps;return productPaint([start[0]*(1-t)+end[0]*t,start[1]*(1-t)+end[1]*t]);
}).filter(color=>color&&color!=='none'))];
};
const visibleSamples=(n,start,end,foreground)=>{
const rgb=value=>(value.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/)||[]).slice(1).map(Number);
const ink=rgb(foreground);let count=0;
for(const t of [.1,.2,.3,.4,.5,.6,.7,.8,.9]){
const x=start[0]*(1-t)+end[0]*t,y=start[1]*(1-t)+end[1]*t;
const stack=document.elementsFromPoint(x,y);if(stack[0]!==n)continue;
const under=stack.find(el=>el!==n&&['rect','circle','ellipse','line','path','text'].includes(el.localName));
const background=under?rgb(getComputedStyle(under).fill):[255,255,255];
if(ink.length===3&&background.length===3&&Math.max(...ink.map((v,i)=>Math.abs(v-background[i])))>=24)count++;
}return count;
};
return [...document.querySelectorAll('svg>line,svg>rect')].flatMap((n,index)=>{
const paint=getComputedStyle(n);
if(n.localName==='line')return paint.stroke==='none'||parseFloat(paint.strokeWidth)<=0?[]:
[{index,kind:'line',start:[n.x1.baseVal.value,n.y1.baseVal.value],end:[n.x2.baseVal.value,n.y2.baseVal.value],stroke_width:parseFloat(paint.strokeWidth),
product_endpoint_fills:[[n.x1.baseVal.value,n.y1.baseVal.value],[n.x2.baseVal.value,n.y2.baseVal.value]].map(productPaint),
product_endpoint_contact_fills:[[n.x1.baseVal.value,n.y1.baseVal.value],[n.x2.baseVal.value,n.y2.baseVal.value]].map(contactPaint),endpoint_contact_radius:1,
route_product_fills:routePaint([n.x1.baseVal.value,n.y1.baseVal.value],[n.x2.baseVal.value,n.y2.baseVal.value]),
visible_samples:visibleSamples(n,[n.x1.baseVal.value,n.y1.baseVal.value],[n.x2.baseVal.value,n.y2.baseVal.value],paint.stroke)}];
const x=n.x.baseVal.value,y=n.y.baseVal.value,w=n.width.baseVal.value,h=n.height.baseVal.value;
if(paint.fill==='none'||Math.min(w,h)<=0||Math.min(w,h)>16||Math.max(w,h)<3*Math.min(w,h))return [];
const start=w>=h?[x,y+h/2]:[x+w/2,y],end=w>=h?[x+w,y+h/2]:[x+w/2,y+h];
return [{index,kind:'rectangle_bar',start,end,stroke_width:Math.min(w,h),product_endpoint_fills:[start,end].map(productPaint),
product_endpoint_contact_fills:[start,end].map(contactPaint),endpoint_contact_radius:1,
route_product_fills:routePaint(start,end),
visible_samples:visibleSamples(n,start,end,paint.fill)}];
});})()'''


def pdf_checks(path, texts, *, size_mm=(148, 210)):
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
    correct_size = bool(size and abs(float(size[1])-size_mm[0]/25.4*72) < .5 and abs(float(size[2])-size_mm[1]/25.4*72) < .5)
    actual_words = Counter(extracted.split()); expected_words = Counter(' '.join(texts).split())
    same_words = actual_words == expected_words
    result = {'pages': int(pages[1]) if pages else None, 'a5_size': correct_size and size_mm == (148, 210),
              'text_word_multiset_preserved': same_words, 'text_extraction': extracted,
              'embedded_fonts': embedded, 'actual_font_names': [row[0] for row in font_rows],
              'raster_image_count': image_count,
              'press_preflight_performed': False}
    if size_mm != (148, 210): result.update(expected_size_mm=list(size_mm), page_size_matches=correct_size)
    if not same_words:
        mismatch = {'missing': [w[:40] for w in list((expected_words-actual_words).elements())[:3]],
                    'unexpected': [w[:40] for w in list((actual_words-expected_words).elements())[:3]]}
        raise ValueError('PDF text clipped or changed: '+json.dumps(mismatch)+
                         '; fit each complete text line inside page margins before export.')
    if result['pages'] != 1 or not correct_size or not same_words or not embedded or image_count:
        raise ValueError('PDF page/text export check failed')
    return result


def export_assessment(path, texts, purpose, *, size_mm=(148, 210)):
    if purpose not in {'deliverable', 'controlled_fault_input'}:
        raise ValueError('Explicit render purpose required')
    try:
        return pdf_checks(path, texts, size_mm=size_mm) if size_mm != (148, 210) else pdf_checks(path, texts)
    except ValueError as exc:
        if purpose != 'controlled_fault_input': raise
        # A deliberately displaced line can fail text extraction. This is an
        # input to a repair exercise, never acceptance of a learner output.
        return {'accepted_as_deliverable': False, 'error': str(exc),
                'purpose': 'controlled_fault_input'}


async def render(source, output, *, purpose='deliverable', profile='leaflet', png_scale=1):
    if purpose not in {'deliverable', 'controlled_fault_input'}:
        raise ValueError('Explicit render purpose required')
    if png_scale not in (1, .4): raise ValueError('Fixed preview scales required')
    validated = validate_svg(source, profile=profile); spec = PROFILES[profile]
    wrapper = document(source, profile=profile)
    measurement = MEASURE
    if profile != 'leaflet':
        measurement = (MEASURE.replace("'svg>text'", "'svg text'").replace('el.getBBox()', 'el.getBoundingClientRect()')
            .replace('const stack=document.elementsFromPoint(c.x+c.width/2,c.y+c.height/2);',
                     'const pt=new DOMPoint(c.x+c.width/2,c.y+c.height/2).matrixTransform(el.getScreenCTM()); const stack=document.elementsFromPoint(pt.x,pt.y);'))
    with owned_profile(output) as chrome_profile:
        process = subprocess.Popen(chrome_args(chrome_profile), env=chrome_env(),
                                   start_new_session=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            async with asyncio.timeout(50):
                active = Path(chrome_profile)/'DevToolsActivePort'
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
                               {'width': spec['width'], 'height': spec['height'], 'deviceScaleFactor': png_scale, 'mobile': False}, session)
                    tree = await call('Page.getFrameTree', session=session)
                    await call('Page.setDocumentContent', {'frameId': tree['frameTree']['frame']['id'], 'html': wrapper}, session)
                    measured = await call('Runtime.evaluate', {'expression': measurement, 'returnByValue': True, 'awaitPromise': True}, session)
                    if 'exceptionDetails' in measured: raise RuntimeError('Text measurement failed')
                    layout = measured['result']['value']
                    label_background_samples = None
                    if profile in ('product_source', 'product_infographic', 'product_infographic_v2'):
                        samples = await call('Runtime.evaluate', {'expression': SOURCE_LABEL_MEASURE, 'returnByValue': True}, session)
                        if 'exceptionDetails' in samples: raise RuntimeError('Label contrast measurement failed')
                        label_background_samples = samples['result']['value']
                    panel_lines = None
                    if profile in ('product_infographic', 'product_infographic_v2'):
                        lines = await call('Runtime.evaluate', {'expression': PANEL_LINE_MEASURE, 'returnByValue': True}, session)
                        if 'exceptionDetails' in lines: raise RuntimeError('Panel line measurement failed')
                        panel_lines = lines['result']['value']
                    if profile == 'product_source':
                        parts = await call('Runtime.evaluate', {'expression': SOURCE_PART_MEASURE, 'returnByValue': True}, session)
                        if 'exceptionDetails' in parts: raise RuntimeError('Product part visibility measurement failed')
                        source_shape_visibility = parts['result']['value']
                    shape_layout = None
                    group_layout = None
                    if profile != 'leaflet':
                        shapes = await call('Runtime.evaluate', {'expression': "[...document.querySelectorAll('svg rect,svg circle,svg ellipse,svg line,svg path')].map(el=>{const b=el.getBoundingClientRect();return {tag:el.localName,bbox:[b.x,b.y,b.width,b.height]};})", 'returnByValue': True}, session)
                        if 'exceptionDetails' in shapes: raise RuntimeError('Shape measurement failed')
                        shape_layout = shapes['result']['value']
                        groups = await call('Runtime.evaluate', {'expression': "[...document.querySelectorAll('svg>g')].map(el=>{const b=el.getBoundingClientRect();return {bbox:[b.x,b.y,b.width,b.height],child_count:el.children.length};})", 'returnByValue': True}, session)
                        if 'exceptionDetails' in groups: raise RuntimeError('Group measurement failed')
                        group_layout = groups['result']['value']
                    if [item['text'] for item in layout] != validated['texts']:
                        raise ValueError('Rendered text differs from parsed source')
                    screenshot = await call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False}, session)
                    png = base64.b64decode(screenshot['data'], validate=True)
                    if len(png) > 4*1024*1024: raise ValueError('PNG output limit')
                    (output/'preview.png').write_bytes(png)
                    exported = await call('Page.printToPDF', {'printBackground': True, 'displayHeaderFooter': False,
                        'paperWidth': spec['size_mm'][0]/25.4, 'paperHeight': spec['size_mm'][1]/25.4, 'marginTop': 0, 'marginBottom': 0,
                        'marginLeft': 0, 'marginRight': 0, 'preferCSSPageSize': True, 'scale': 1}, session)
                    pdf = base64.b64decode(exported['data'], validate=True)
                    if not pdf.startswith(b'%PDF-') or len(pdf) > 4*1024*1024: raise ValueError('PDF output limit')
                    (output/'preview.pdf').write_bytes(pdf)
                    result = {'layout': layout, 'browser_version': version, 'static_svg': validated,
                              'pdf': export_assessment(output/'preview.pdf', validated['texts'], purpose, size_mm=spec['size_mm']),
                              'render_purpose': purpose,
                              'desktop_used': False, 'sandbox_disabled': False, 'external_page_loaded': False}
                    if shape_layout is not None: result['shape_layout'] = shape_layout
                    if label_background_samples is not None: result['label_background_samples'] = label_background_samples
                    if profile == 'product_source': result['source_shape_visibility'] = source_shape_visibility
                    if panel_lines is not None: result['panel_line_segments'] = panel_lines
                    if group_layout is not None: result['group_layout'] = group_layout
        finally:
            stop_owned_chrome(process)
        result['own_browser_stopped'] = process.poll() is not None
        return result
