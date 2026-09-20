"""Assemble three private browser trials. Media copied read-only; output stays Linux."""
import argparse
from hashlib import sha256
import html
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image

TEMPLATES=Path(__file__).parent/'templates'

def stamp(p,index):
    palettes=[('#3a6658','#bac8aa'),('#8b423b','#ecc7ab'),('#354f6e','#b4c3c8'),('#875d36','#dcc694'),('#6a5278','#c5bacb'),('#536537','#c8d2a8')]
    ink,bg=palettes[index//3%6];perfs=''.join(f'<circle cx="{x}" cy="{y}" r="5"/>' for x,y in [(x,y) for x in range(12,240,13) for y in [10,290]]+[(x,y) for y in range(10,291,13) for x in [10,230]])
    motifs=[
      '<path d="M37 191V124h21V85h16v39h17v-22h26v22h12V74h17v50h25v-19h14v19h18v67Z" fill="INK"/><path d="M65 86l1-30 6 14zM136 74l-1-33 9 20z" fill="INK"/>',
      '<path d="M26 186L114 74 149 122 176 103 215 186Z" fill="INK"/><path d="M86 112l28-38 28 37-17-6-12 10-11-11z" fill="#eee6ce"/><path d="M25 198q34-13 70 0t71 0t57 0M25 212q34-13 70 0t71 0t57 0" fill="none" stroke="INK" stroke-width="3"/>',
      '<path d="M113 194q-14-60 12-100" fill="none" stroke="INK" stroke-width="4"/><path d="M117 157q-45 4-53-30 40-6 53 30M120 174q46 4 55-25-41-8-55 25" fill="INK"/><g fill="INK"><ellipse cx="126" cy="101" rx="17" ry="32"/><ellipse cx="126" cy="101" rx="17" ry="32" transform="rotate(60 126 101)"/><ellipse cx="126" cy="101" rx="17" ry="32" transform="rotate(120 126 101)"/></g><circle cx="126" cy="101" r="12" fill="#ede4cc"/>'
    ]
    art=motifs[index%3].replace('INK',ink);lines=''.join(f'<path d="M27 {y}h185" stroke="{ink}" opacity=".07"/>' for y in range(63,224,4))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="240" height="300" viewBox="0 0 240 300"><defs><mask id="perf"><rect width="240" height="300" fill="white"/><g fill="black">{perfs}</g></mask><filter id="texture"><feTurbulence type="fractalNoise" baseFrequency=".65" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope=".11"/></feComponentTransfer><feBlend in="SourceGraphic" mode="multiply"/></filter></defs><g mask="url(#perf)"><rect x="10" y="10" width="220" height="280" fill="#f5eddb"/><rect x="24" y="24" width="192" height="252" fill="{bg}" stroke="{ink}" stroke-width="1.5"/><rect x="30" y="59" width="180" height="167" fill="#f0e8d155"/>{lines}<g filter="url(#texture)">{art}</g><text x="120" y="45" fill="{ink}" font-family="Georgia,serif" font-size="15" letter-spacing="2" text-anchor="middle">{html.escape(p['country'].upper())}</text><path d="M34 233h172" stroke="{ink}"/><text x="37" y="258" fill="{ink}" font-family="Georgia,serif" font-size="25">{index%5+1},00</text><text x="203" y="253" fill="{ink}" font-family="Georgia,serif" font-size="15" text-anchor="end">{p['year']}</text><text x="120" y="271" fill="{ink}" font-family="Arial" font-size="6" letter-spacing="2" text-anchor="middle">ATLAS · ILUSTRACJA STUDYJNA</text></g></svg>'''

def film(folder):
    """Original procedural moving light sculpture, rendered to seekable H.264."""
    w,h,fps,frames=1280,720,24,240
    output=folder/'horizon.mp4'
    if output.exists():return
    command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-n','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','24','-g','1','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    yy,xx=np.mgrid[-1:1:complex(h),-w/h:w/h:complex(w)].astype(np.float32)
    rng=np.random.default_rng(1809);stars=[(int(rng.integers(w)),int(rng.integers(h)),float(rng.uniform(.2,.7))) for _ in range(130)]
    try:
        for frame in range(frames):
            t=frame/(frames-1);cx=.3+.18*math.sin(t*math.pi*1.2);cy=-.17+.07*math.sin(t*5)
            x=xx-cx;y=yy-cy;radius=np.sqrt(x*x+(y*1.2)**2);angle=np.arctan2(y,x)
            mist=np.exp(-radius**2/.95)*(.035+.025*np.sin(angle*3+t*6)**2)
            horizon=np.exp(-((yy-.35-.035*np.sin(xx*2+t*4))/.08)**2)*.07
            light=np.zeros_like(xx);core=np.zeros_like(xx)
            for i in range(5):
                r=.24+i*.19+t*.42;warp=.06*np.sin(angle*3+t*3+i*.7)+.035*np.cos(angle*7-t*4)
                d=np.abs(radius-r-warp)
                facing=.25+.75*(.5+.5*np.sin(angle+t*2+i))
                light+=np.exp(-d*26)*facing*.18
                core+=np.exp(-d*180)*facing*.7
            ribbon=np.exp(-np.abs(yy-.30-.07*np.sin(xx*3+t*8))*100)*np.exp(-(xx*.65)**2)*.20
            reflection=np.exp(-np.abs(yy-.57-.06*np.sin(xx*4-t*7))*27)*.045
            shade=np.maximum(0,1-(xx*.20)**2-(yy*.34)**2)
            rgb=np.empty((h,w,3),dtype=np.float32)
            rgb[:,:,0]=.025+mist*.8+light*.57+core*.82+horizon*.52+ribbon*.85+reflection
            rgb[:,:,1]=.018+mist*.45+light*.35+core*.60+horizon*.35+ribbon*.53+reflection*.5
            rgb[:,:,2]=.05+mist*2+light*1.4+core*.94+horizon*1.5+ribbon+reflection*2
            rgb*=shade[:,:,None]
            for sx,sy,intensity in stars:
                tx=(sx+int(t*35))%w;rgb[sy,tx,:]+=intensity*(.6+.4*math.sin(t*5+sx))
            raw=np.uint8(np.clip(rgb,0,1)*255)
            if frame==0:Image.fromarray(raw).save(folder/'poster.jpg',quality=92)
            process.stdin.write(raw.tobytes())
        process.stdin.close()
        if process.wait(timeout=30):raise ValueError('Movie encoding failed')
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=10)

def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--track',action='append',type=Path,default=[]);p.add_argument('--logo',type=Path);p.add_argument('--cover',type=Path);p.add_argument('--render-film',action='store_true');a=p.parse_args();root=a.output.resolve()
    if not root.is_relative_to('/home/marcin/ai-company-workspaces') or not root.is_dir():raise ValueError('Private Linux directory required')
    for site in ('stamps','music','casino'):
        for source in (TEMPLATES/site).iterdir():shutil.copyfile(source,root/site/source.name)
    s=json.loads((root/'stamps/proposal.json').read_text());products=s['products']
    if len(products)!=18 or {p['id'] for p in products}!={f's{i:02}' for i in range(1,19)}:raise ValueError('Expected 18 unique stamp IDs')
    if len(s['categories'])!=4 or any(p['category'] not in s['categories'] or type(p['price']) is not int or not 15<=p['price']<=400 or type(p['year']) is not int for p in products):raise ValueError('Invalid catalog')
    countries={'Polska','Japonia','Francja','Norwegia','Wielka Brytania','Włochy'}
    if {p['country'] for p in products}!=countries or any(sum(p['country']==c for p in products)!=3 for c in countries):raise ValueError('Invalid country grouping')
    # The original model proposal remains in evidence; use standard philately wording.
    for p in products:
        if p['condition']=='Świeży':p['condition']='Czysty — przykład'
    art=root/'stamps/art';art.mkdir(exist_ok=True)
    for i,p in enumerate(products):(art/(p['id']+'.svg')).write_text(stamp(p,i))
    (root/'stamps/data.js').write_text('window.TrialData='+json.dumps({'products':products,'categories':s['categories']},ensure_ascii=True)+';')
    assets=root/'music/assets';assets.mkdir(exist_ok=True);tracks=[];provenance=[]
    for i,track in enumerate(a.track):
        if track.suffix.lower()!='.mp3' or track.stat().st_size>30_000_000:raise ValueError('Bounded MP3 required')
        target=assets/f'track-{i+1:02}.mp3';shutil.copyfile(track,target)
        duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(target)],text=True,timeout=10).strip())
        title=track.stem.removeprefix('Million Horizons - ')
        tracks.append({'title':title,'src':'assets/'+target.name,'duration':duration})
        provenance.append({'kind':'audio','source':str(track),'sha256':sha256(target.read_bytes()).hexdigest()})
    if not tracks:raise ValueError('Choose actual audio or prepare a labelled demo recording')
    if a.logo:
        with Image.open(a.logo) as logo:
            if logo.width>6000 or logo.height>6000:raise ValueError('Logo too large')
            logo.verify()
        # Copy exact supplied raster; HTML can display its actual format regardless of suffix.
        name='logo'+a.logo.suffix.lower()
        if a.logo.suffix.lower() not in ('.png','.jpg'):raise ValueError('PNG/JPEG logo required')
        shutil.copyfile(a.logo,assets/name)
        page=root/'music/index.html';page.write_text(page.read_text().replace('assets/logo.png','assets/'+name))
        provenance.append({'kind':'logo','source':str(a.logo),'sha256':sha256(a.logo.read_bytes()).hexdigest()})
    if a.cover:
        shutil.copyfile(a.cover,assets/'cover.png')
        page=root/'music/index.html';page.write_text(page.read_text().replace('<div class="record-art">','<div class="record-art"><img class="cover-art" src="assets/cover.png" alt="Okładka This Is My Horizon — Million Horizons">'))
        css=root/'music/style.css';css.write_text(css.read_text()+'\n.cover-art{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:2}.record-art:has(.cover-art) .record-tag{display:none}\n')
    events=[{'id':'e1','title':'Beyond the Horizon','city':'Gdańsk','venue':'Scena klubowa — demo','day':'18','month':'PAŹ','monthNumber':'10','year':'2026','type':'CLUB NIGHT'}, {'id':'e2','title':'Infinite Frequencies','city':'Warszawa','venue':'Przestrzeń koncertowa — demo','day':'07','month':'LIS','monthNumber':'11','year':'2026','type':'LIVE SESSION'}, {'id':'e3','title':'A State of Connection','city':'Oslo','venue':'Scena elektroniczna — demo','day':'21','month':'LIS','monthNumber':'11','year':'2026','type':'TRANCE NIGHT'}]
    (root/'music/data.js').write_text('window.TrialData='+json.dumps({'tracks':tracks,'events':events},ensure_ascii=True)+';')
    if a.render_film:
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]));from scripts.compare_local_models import check_idle
        check_idle();film(assets)
    page=root/'music/index.html';page.write_text(page.read_text().replace('<sup>®</sup>',''))
    (root/'evidence/media-provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
    for site in ('stamps','music','casino'):
        folder=root/site;files={str(f.relative_to(folder)):sha256(f.read_bytes()).hexdigest() for f in folder.rglob('*') if f.is_file() and f.name not in ('proposal.json','manifest.json','README.md')}
        (folder/'manifest.json').write_text(json.dumps({'site':site,'files':files,'accepted':False,'deployed':False},indent=2))
        (folder/'README.md').write_text('Local website trial. Serve index.html through HTTP. No external dependencies.\nReview required. No actual order, concert booking, cash gambling or external publication.\nModel logic plus supervised UI integration; see separate evidence.\n')
    print(json.dumps({'output':str(root),'sites':3,'audio_tracks':len(tracks),'logo_included':a.logo is not None,'movie':(assets/'horizon.mp4').exists()}))

if __name__=='__main__':main()
