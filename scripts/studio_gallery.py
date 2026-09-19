"""Verified local PNG manifest -> trusted gallery markup, not executable model code."""
import base64
import io
from hashlib import sha256
from html import escape
import json
import re
from pathlib import Path
import struct

from scripts.build_studio_media import ROOT, IDS
from scripts.prepare_training_data import unique_object

STATIC=Path(__file__).resolve().parents[1]/'app/static/organization-os'


def load_assets(path):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT) or path.stat().st_size>1_000_000:raise ValueError('Local bounded media report required')
    report=json.loads(path.read_bytes(),object_pairs_hook=unique_object)
    if report.get('schema')!='studio-media.v1' or report.get('status')!='rendered' or report.get('own_service_stopped') is not True:
        raise ValueError('Completed generation required')
    entries=report.get('assets')
    if not isinstance(entries,list) or len(entries)!=3:raise ValueError('Three assets required')
    assets=[]
    for entry,identifier in zip(entries,IDS):
        if entry.get('id')!=identifier or entry.get('status')!='rendered':raise ValueError('Invalid image identity')
        image=(path.parent/entry['file']).resolve()
        if not image.is_relative_to(path.parent) or not image.is_file() or not 0<image.stat().st_size<=4_000_000:
            raise ValueError('Image escapes report or is too large')
        raw=image.read_bytes()
        if sha256(raw).hexdigest()!=entry['sha256'] or raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR' or struct.unpack('>II',raw[16:24])!=(768,512):
            raise ValueError('PNG checksum/dimensions mismatch')
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
        for key,limit in [('title',60),('alt',180)]:
            if not isinstance(entry[key],str) or not 0<len(entry[key])<=limit:raise ValueError('Invalid caption')
        assets.append({k:entry[k] for k in ('id','alt','title')} | {'src':'data:image/png;base64,'+base64.b64encode(raw).decode()})
    return assets


def enhance(html,files,assets):
    def image(asset):return f'<img src="{asset["src"]}" alt="{escape(asset["alt"],quote=True)}" width="768" height="512" decoding="async">'
    cards=''.join(f'<article class="visual-card" data-art="{i}"><button type="button" data-open-art="{i}" aria-haspopup="dialog"><div class="visual-image">{image(a)}</div><h3>{escape(a["title"])}</h3><p>0{i+1} / OTWÓRZ STUDIUM ↗</p></button></article>' for i,a in enumerate(assets))
    chapters=''.join(f'<button type="button" data-scene-chapter="{i}" aria-label="Przejdź do studium: {escape(a["title"],quote=True)}"><span>0{i+1}</span> {escape(a["title"])}</button>' for i,a in enumerate(assets))
    gallery=('<section id="visuals" aria-labelledby="visuals-title"><p class="visual-kicker">QWEN × COMFYUI / STUDIA WIZUALNE</p>'
        '<div class="visual-intro"><h2 id="visuals-title">Nie oglądaj.<br>Wejdź w obraz.</h2><p>Przewijaj, aby przejść przez formę, przestrzeń i materiał. Obrazy zbliżają się i ustępują miejsca kolejnym. Własne eksperymenty AI — nie realizacje klientów.</p></div>'
        '<div class="scene-journey"><div class="scene-stage"><div class="scene-hud"><span>FORMA / VISUAL LAB</span><span data-scene-counter>01 — 03</span><a href="#services">Pomiń scenę ↗</a></div>'
        '<div class="scene-word" aria-hidden="true">FORMA</div><div class="visual-grid">'+cards+'</div>'
        '<div class="scene-footer"><p>PRZEWIJAJ, BY ZMIENIĆ PERSPEKTYWĘ ↓</p><nav aria-label="Studia wizualne">'+chapters+'</nav><div class="scene-track" aria-hidden="true"><i></i></div></div>'
        '</div></div></section>')
    dialog='''<dialog id="art-viewer" aria-labelledby="art-title" aria-describedby="art-help"><div class="art-toolbar"><h2 id="art-title">Studium</h2><span id="art-counter" aria-live="polite"></span><button type="button" data-close aria-label="Zamknij galerię">Zamknij ×</button></div><div class="art-stage"><img alt=""></div><div class="art-controls"><button type="button" data-prev aria-label="Poprzedni obraz">←</button><button type="button" data-zoom-out aria-label="Oddal">−</button><output id="zoom-level" aria-live="polite">100%</output><button type="button" data-zoom-in aria-label="Przybliż">+</button><button type="button" data-reset>Reset</button><button type="button" data-next aria-label="Następny obraz">→</button></div><p class="art-instructions" id="art-help">Kółko nad obrazem: przybliż / oddal · strzałki: zmień obraz · Esc: zamknij. Na telefonie użyj przycisków.</p></dialog>'''
    old='<div class="art" aria-hidden="true"><i></i><i></i><i></i></div>'
    if old not in html or '<section id="services">' not in html:raise ValueError('Studio HTML contract changed')
    html=html.replace(old,'<a class="hero-visual" href="#visuals">'+image(assets[0])+'<span>WEJDŹ W SCENĘ ↓</span></a>',1)
    html=re.sub(r'<p class="filewarn" role="note">.*?</p>', '<p class="filewarn" role="note">Podgląd demonstracyjny · Kalkulator działa w izolacji · Grafiki wygenerowano lokalnie w ComfyUI.</p>',html,count=1,flags=re.DOTALL)
    html=html.replace('<section id="services">',gallery+'<section id="services">',1)
    html=html.replace('<a href="#services">Usługi</a>','<a href="#visuals">Galeria</a><a href="#services">Usługi</a>',1)
    html=html.replace('</head>','<link rel="stylesheet" href="studio-gallery.css"><link rel="stylesheet" href="studio-scene.css"></head>',1)
    html=html.replace('</body>',dialog+'<script src="studio-gallery.js"></script><script src="studio-scene.js"></script></body>',1)
    return html, files | {name:(STATIC/name).read_text() for name in ('studio-gallery.css','studio-gallery.js','studio-scene.css','studio-scene.js')}
