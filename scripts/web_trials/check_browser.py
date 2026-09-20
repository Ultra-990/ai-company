"""Independent checks in an owned headless Chrome; no desktop session access."""
import argparse
import asyncio
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.request import urlopen
import websockets

class Browser:
    def __init__(self,ws):self.ws=ws;self.serial=0;self.contexts=[];self.errors=[]
    async def call(self,method,params=None,session=None):
        self.serial+=1;payload={'id':self.serial,'method':method,'params':params or {}}
        if session:payload['sessionId']=session
        await self.ws.send(json.dumps(payload))
        while True:
            r=json.loads(await asyncio.wait_for(self.ws.recv(),25))
            if r.get('method')=='Runtime.executionContextCreated':self.contexts.append((r.get('sessionId'),r['params']['context']['id']))
            if r.get('method')=='Runtime.exceptionThrown':self.errors.append(r['params']['exceptionDetails'].get('text','exception'))
            if r.get('id')==self.serial:
                if 'error' in r:raise RuntimeError(str(r['error']))
                return r.get('result',{})
    async def js(self,expr,context):
        r=await self.call('Runtime.evaluate',{'expression':expr,'contextId':context[1],'returnByValue':True,'userGesture':True,'awaitPromise':True},context[0])
        if 'exceptionDetails' in r:raise RuntimeError(r['exceptionDetails'].get('exception',{}).get('description',str(r['exceptionDetails'])))
        return r.get('result',{}).get('value')
    async def wait(self,expr,context,seconds=8):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if await self.js(expr,context):return True
            await asyncio.sleep(.1)
        return False
    async def open(self,url,site):
        target=(await self.call('Target.createTarget',{'url':'about:blank'}))['targetId'];session=(await self.call('Target.attachToTarget',{'targetId':target,'flatten':True}))['sessionId'];self.contexts=[]
        await self.call('Runtime.enable',session=session)
        await self.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False},session)
        await self.call('Page.navigate',{'url':url+'/'+site},session)
        attached={target};context=None
        for _ in range(100):
            await asyncio.sleep(.1);await self.call('Runtime.evaluate',{'expression':'1'},session)
            for info in (await self.call('Target.getTargets'))['targetInfos']:
                if info['type']=='iframe' and info['targetId'] not in attached and info.get('url')==url+'/'+site+'/index.html':
                    child=(await self.call('Target.attachToTarget',{'targetId':info['targetId'],'flatten':True}))['sessionId'];attached.add(info['targetId']);await self.call('Runtime.enable',session=child)
            for candidate in list(self.contexts):
                try:
                    if await self.js('!!window.TrialLogic && !!document.querySelector("h1")',candidate):context=candidate;break
                except RuntimeError:pass
            if context:break
        if not context:raise RuntimeError('Frame did not load '+site)
        await self.call('Page.bringToFront',session=session)
        return target,session,context

async def run(args,out,report):
    env={k:v for k,v in os.environ.items() if k not in {'DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS'}};env['DBUS_SESSION_BUS_ADDRESS']='unix:path=/nonexistent'
    with tempfile.TemporaryDirectory(prefix='chrome-',dir=out) as profile:
        process=subprocess.Popen(['/usr/bin/google-chrome','--headless','--ozone-platform=headless','--disable-gpu','--mute-audio','--disable-extensions','--disable-background-networking','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            active=Path(profile)/'DevToolsActivePort'
            for _ in range(100):
                if active.exists():break
                await asyncio.sleep(.1)
            port,path=active.read_text().splitlines()[:2]
            async with websockets.connect('ws://127.0.0.1:'+port+path,max_size=8*1024*1024) as ws:
                b=Browser(ws)
                async def record(site,name,expr,ctx):
                    actual=await b.js(expr,ctx);report['checks'].append({'site':site,'name':name,'passed':actual is True,'actual':actual});save()
                def save():(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
                for site in ['stamps','music','casino']:
                    target=None
                    try:
                        target,session,ctx=await b.open(args.url,site)
                        await record(site,'opaque-origin',"(()=>{try{return parent.document===document}catch{return true}})()",ctx)
                        await record(site,'no-horizontal-overflow-desktop','document.documentElement.scrollWidth<=innerWidth+1',ctx)
                        await b.js('window.probeFocusCalls=0;window.nativeProbeFocus=HTMLElement.prototype.focus;HTMLElement.prototype.focus=function(...a){window.probeFocusCalls++;return window.nativeProbeFocus.apply(this,a)}',ctx)
                        if site=='stamps':
                            await record(site,'model-catalog-sort-filter-total',"(()=>{const L=TrialLogic,D=TrialData.products,original=JSON.stringify(D);return D.length===18&&L.filterProducts(D,{country:'Polska'}).length===3&&L.filterProducts(D,{query:'  JAPONIA  '}).length===3&&L.filterProducts(D,{query:'nonexistent-xyz'}).length===0&&L.filterProducts(D,{sort:'price-asc'}).every((x,i,a)=>!i||a[i-1].price<=x.price)&&L.filterProducts(D,{sort:'oldest'}).every((x,i,a)=>!i||a[i-1].year<=x.year)&&L.cartTotal(D,[D[0].id,D[0].id,D[1].id,'missing'])===D[0].price+D[1].price&&JSON.stringify(D)===original})()",ctx)
                            await b.js("document.querySelector('[data-country=Japonia]').click()",ctx);await asyncio.sleep(.5)
                            await record(site,'country-opens-gallery',"document.querySelectorAll('.product').length===3 && document.querySelector('#country').value==='Japonia'",ctx)
                            await b.js("document.querySelector('[data-open]').click();window.firstTitle=document.querySelector('#detail-title').textContent",ctx)
                            await b.wait("document.querySelector('#detail-image').naturalWidth>0",ctx)
                            await record(site,'gallery-image-loaded',"document.querySelector('#product-dialog').open && document.querySelector('#detail-image').naturalWidth>0",ctx)
                            await b.js("document.querySelector('#next').click()",ctx)
                            await record(site,'gallery-next',"document.querySelector('#detail-title').textContent!==window.firstTitle",ctx)
                            await b.js("document.querySelector('#detail-add').click();document.querySelector('#detail-add').click()",ctx)
                            await record(site,'single-stock-cart',"document.querySelector('#cart-count').textContent==='1' && document.querySelector('#detail-add').disabled",ctx)
                            await b.js("document.querySelector('[data-close=product-dialog]').click();document.querySelector('#cart-open').click();document.querySelector('#checkout').click()",ctx)
                            await record(site,'test-checkout',"!document.querySelector('#receipt').hidden && document.querySelector('#receipt-content').textContent.includes('Płatność: nie pobrano')",ctx)
                            await b.js("document.querySelector('[data-remove]').click()",ctx)
                            await record(site,'cart-remove-recalculates',"document.querySelector('#cart-count').textContent==='0'&&document.querySelector('#checkout').disabled&&document.querySelector('#receipt').hidden",ctx)
                            await b.js("document.querySelector('[data-close=cart-dialog]').click();document.querySelector('#clear').click();document.querySelector('#search').value='missing-xyz';document.querySelector('#search').dispatchEvent(new Event('input'))",ctx)
                            await record(site,'empty-search-state',"!document.querySelector('#empty').hidden&&document.querySelectorAll('.product').length===0",ctx)
                            await b.js("document.querySelector('#clear').click();scrollTo({top:0,behavior:'instant'})",ctx)
                        elif site=='music':
                            await record(site,'model-time-and-events',"(()=>{const L=TrialLogic;return L.scrollTime(50,0,100,10)===5&&L.scrollTime(-1,0,100,10)===0&&L.scrollTime(200,0,100,10)===10&&L.scrollTime(1,1,1,10)===0&&L.scrollTime(NaN,0,10,3)===0&&L.formatTime(125.9)==='2:05'&&L.formatTime(-1)==='0:00'&&L.filterEvents(TrialData.events,'Oslo').length===1})()",ctx)
                            ready=await b.wait("document.querySelector('#horizon-film').readyState>=2 && document.querySelector('#audio').readyState>=1",ctx,15)
                            report['checks'].append({'site':site,'name':'media-metadata','passed':ready})
                            await record(site,'three-tracks-no-autoplay',"document.querySelectorAll('.track').length===3&&document.querySelector('#audio').paused&&document.querySelector('#horizon-film').duration>9",ctx)
                            await record(site,'owner-logo-loaded',"!document.querySelector('#brand-logo').hidden && document.querySelector('#brand-logo').naturalWidth>0",ctx)
                            await b.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':1100,'y':500},session)
                            await b.call('Input.dispatchMouseEvent',{'type':'mouseWheel','x':1100,'y':500,'deltaX':0,'deltaY':650},session);await asyncio.sleep(.8)
                            await record(site,'native-wheel-seeks-video-forward',"scrollY>400&&document.querySelector('#horizon-film').currentTime>1",ctx)
                            await b.js("window.filmForward=document.querySelector('#horizon-film').currentTime",ctx)
                            await b.call('Input.dispatchMouseEvent',{'type':'mouseWheel','x':1100,'y':500,'deltaX':0,'deltaY':-350},session);await asyncio.sleep(.7)
                            await record(site,'native-wheel-seeks-video-back',"document.querySelector('#horizon-film').currentTime<window.filmForward",ctx)
                            await b.js("document.querySelector('a[href=\"#sound\"]:not(.skip)').click()",ctx);await asyncio.sleep(.7)
                            await b.js("document.querySelector('#play').click()",ctx);await b.wait("document.querySelector('#audio').currentTime>.1",ctx,10)
                            await record(site,'audio-real-playback',"!document.querySelector('#audio').paused&&document.querySelector('#audio').currentTime>0",ctx)
                            await b.js("document.querySelector('#play').click();document.querySelector('#seek').value=500;document.querySelector('#seek').dispatchEvent(new Event('input'))",ctx);await asyncio.sleep(.3)
                            await record(site,'audio-pause-and-seek',"document.querySelector('#audio').paused&&Math.abs(document.querySelector('#audio').currentTime/document.querySelector('#audio').duration-.5)<.02",ctx)
                            await b.js("document.querySelector('#next-track').click()",ctx);await b.wait("document.querySelector('#audio').readyState>=1",ctx)
                            await record(site,'next-track-does-not-autoplay',"document.querySelector('#audio').currentSrc.endsWith('track-02.mp3')&&document.querySelector('#audio').paused",ctx)
                            await b.js("document.querySelector('#play').click()",ctx);await b.wait("!document.querySelector('#audio').paused",ctx)
                            await b.js("Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'))",ctx)
                            await record(site,'hidden-page-pauses-audio',"document.querySelector('#audio').paused",ctx)
                            await b.js("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));document.querySelector('#city').value='Oslo';document.querySelector('#city').dispatchEvent(new Event('change'));document.querySelector('[data-event]').click()",ctx)
                            await record(site,'filtered-event-dialog',"document.querySelectorAll('.event').length===1&&document.querySelector('#event-dialog').open&&document.querySelector('#event-detail').textContent.includes('Oslo')",ctx)
                            await b.js("document.querySelector('[data-close=event-dialog]').click();scrollTo({top:0,behavior:'instant'})",ctx)
                        else:
                            expr="""(()=>{const L=TrialLogic,R=new Set([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]);for(let n=0;n<37;n++)for(const choice of ['red','black','even','odd']){const win=n!==0&&(choice==='red'?R.has(n):choice==='black'?!R.has(n):choice==='even'?n%2===0:n%2===1);if(L.roulettePayout(10,choice,n)!==(win?20:0))return false}for(const a of ['star','diamond','seven','cherry'])for(const b of ['star','diamond','seven','cherry'])for(const c of ['star','diamond','seven','cherry']){const distinct=new Set([a,b,c]).size,want=distinct===1?(a==='seven'?200:100):distinct===2?20:0;if(L.slotPayout(10,[a,b,c])!==want)return false}for(const [cards,total,soft,bust] of [[[],0,false,false],[['A','A','9'],21,true,false],[['A','A','9','K'],21,false,false],[['A','6'],17,true,false],[['10','8','6'],24,false,true],[['A','K'],21,true,false]]){const r=L.blackjackValue(cards);if(r.total!==total||r.soft!==soft||r.bust!==bust)return false}for(const f of [()=>L.blackjackValue(['X']),()=>L.roulettePayout(-1,'red',1),()=>L.roulettePayout(10,'red',37),()=>L.roulettePayout(10,'invalid',1),()=>L.slotPayout(10,['seven']),()=>L.slotPayout(NaN,['seven','seven','seven'])]){let failed=false;try{f()}catch{failed=true}if(!failed)return false}return true})()"""
                            await record(site,'independent-224-game-cases',expr,ctx)
                            await b.js("document.querySelector('#play').click();document.querySelector('#play').click();document.querySelector('#tab-slots').click()",ctx)
                            await record(site,'single-stake-no-concurrent-games',"document.body.dataset.balance==='950'&&document.body.dataset.busy==='true'&&document.querySelector('#slots').hidden",ctx)
                            await b.wait("document.body.dataset.busy==='false'",ctx)
                            await record(site,'roulette-settles-once',"document.querySelectorAll('.history-row').length===1&&Number(document.querySelector('#roulette-number').textContent)>=0",ctx)
                            await b.js("window.oldBalance=document.body.dataset.balance;document.querySelector('#stake').value=-10;document.querySelector('#play').click()",ctx)
                            await record(site,'invalid-stake-does-not-charge',"document.body.dataset.balance===window.oldBalance&&document.querySelector('#status').textContent.includes('10–500')",ctx)
                            await b.js("document.querySelector('#stake').value=50;document.querySelector('#tab-slots').click();document.querySelector('#play').click()",ctx);await b.wait("document.body.dataset.busy==='false'",ctx)
                            await record(site,'slots-real-round',"document.querySelectorAll('.history-row').length===2&&[...document.querySelectorAll('.reel')].every(x=>!x.classList.contains('spinning'))",ctx)
                            await b.js("document.querySelector('#tab-blackjack').click();document.querySelector('#play').click();if(document.body.dataset.busy==='true')document.querySelector('#stand').click()",ctx)
                            await record(site,'blackjack-completes-hand',"document.body.dataset.busy==='false'&&document.querySelectorAll('.history-row').length===3&&document.querySelectorAll('#dealer-cards .back').length===0&&Number(document.body.dataset.balance)>=0",ctx)
                            await b.js("document.querySelector('#reset').click();document.querySelector('#tab-roulette').click()",ctx)
                            await record(site,'reset-wallet',"document.body.dataset.balance==='1000'&&document.querySelectorAll('.history-row').length===0",ctx)
                        await record(site,'no-programmatic-focus-during-delayed-work','window.probeFocusCalls===0',ctx)
                        await b.js("scrollTo({top:0,behavior:'instant'})",ctx);await asyncio.sleep(.35)
                        shot=await b.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False},session);(out/f'{site}-desktop.png').write_bytes(base64.b64decode(shot['data']))
                        for width,height in [(390,844),(768,1024),(320,740)]:
                            await b.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':height,'deviceScaleFactor':1,'mobile':False},session);await asyncio.sleep(.2)
                            await record(site,f'no-horizontal-overflow-{width}','document.documentElement.scrollWidth<=innerWidth+1',ctx)
                            if width==390:
                                shot=await b.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False},session);(out/f'{site}-mobile.png').write_bytes(base64.b64decode(shot['data']))
                        await b.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]},session)
                        if ctx[0]!=session:await b.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]},ctx[0])
                        await b.wait("matchMedia('(prefers-reduced-motion:reduce)').matches",ctx)
                        await record(site,'reduced-motion-respected',"getComputedStyle(document.documentElement).scrollBehavior==='auto'",ctx)
                        if site=='music':
                            await b.js("window.stillFrame=document.querySelector('#horizon-film').currentTime;scrollBy(0,300)",ctx);await asyncio.sleep(.3)
                            await record(site,'reduced-motion-video-stays-still',"Math.abs(document.querySelector('#horizon-film').currentTime-window.stillFrame)<.1",ctx)
                    except Exception as exc:
                        report['checks'].append({'site':site,'name':'execution','passed':False,'error':str(exc)[:600]});save()
                    finally:
                        if target:await b.call('Target.closeTarget',{'targetId':target})
                report['browser_exceptions']=b.errors;save()
                await ws.send(json.dumps({'id':b.serial+1,'method':'Browser.close'}));await asyncio.to_thread(process.wait,timeout=5)
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)

def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--url',default='http://127.0.0.1:33117');a=p.parse_args()
    if not a.url.startswith('http://127.0.0.1:'):raise ValueError('Own loopback preview required')
    root=a.output.resolve();out=Path(tempfile.mkdtemp(prefix='browser-',dir=root/'evidence'))
    report={'schema':'three-web-trials-browser.v1','checks':[],'accepted':False,'deployed':False,'manifests':{s:sha256((root/s/'manifest.json').read_bytes()).hexdigest() for s in ('stamps','music','casino')}}
    started=time.monotonic()
    try:asyncio.run(run(a,out,report))
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3);report['passed']=bool(report['checks']) and all(c['passed'] for c in report['checks']) and not report.get('browser_exceptions')
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps({'report':str(out/'report.json'),'passed':report['passed'],'checks':len(report['checks']),'failed':[c['name'] for c in report['checks'] if not c['passed']]}),flush=True)
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
