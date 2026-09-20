"""Opt-in real synthetic delivery audit; never changes the production database."""
import asyncio
import base64
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile

import pytest

from app.services.multifile_generation import parse_sources
from scripts import check_qwen_multifile as generator, upwork_web_case as case
from tests.browser_multifile_probe import check
from tests.conftest import OWNER_HEADERS
from tests.test_multifile_execution import package


def test_studio_dry_run_is_an_evaluation_not_training_or_execution(monkeypatch, capsys):
    monkeypatch.setattr(generator, 'check_idle', lambda: pytest.fail('No processes in dry-run'))
    assert generator.main(['--scenario', 'studio']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['scenario'] == 'studio' and not result['model_invoked']
    assert result['http_checks'] == 8
    assert result['independent_tests_sha256'] == sha256(case.ACCEPTANCE.encode()).hexdigest()
    assert 'class ClientAcceptance' not in result['brief']


def verified_files(report):
    if (report.get('schema') != 'qwen-multifile-pilot.v1' or report.get('scenario') != 'studio'
            or report.get('status') != 'passed' or report.get('brief') != case.BRIEF
            or report.get('independent_tests') != case.ACCEPTANCE):
        raise ValueError('This frozen studio brief needs passing backend evidence')
    files = parse_sources(report['generation']['content'])
    if {k:sha256(v.encode()).hexdigest() for k,v in files.items()} != report['source_checksums']:
        raise ValueError('Source checksum mismatch')
    return files


@pytest.mark.parametrize('changes', [{'scenario':'quote'}, {'status':'failed'}, {'brief':'changed'},
                                    {'independent_tests':'weakened'}])
def test_browser_gate_rejects_wrong_evidence(changes):
    report = {'schema':'qwen-multifile-pilot.v1', 'scenario':'studio', 'status':'passed',
              'brief':case.BRIEF, 'independent_tests':case.ACCEPTANCE}
    with pytest.raises(ValueError, match='frozen studio'):
        verified_files(report | changes)


@pytest.mark.skipif(not os.environ.get('AIC_STUDIO_WEB_REPORT'), reason='Explicit retained synthetic Qwen output only')
def test_retained_studio_website(client, task_repository):
    path = Path(os.environ['AIC_STUDIO_WEB_REPORT']).resolve()
    assert path.is_relative_to(Path('/home/marcin/ai-company-workspaces/qwen-training'))
    raw = path.read_bytes()
    report = json.loads(raw)
    files = verified_files(report)
    media_path = os.environ.get('AIC_STUDIO_MEDIA_REPORT')
    frame_transform = None
    if media_path:
        from scripts.studio_gallery import load_assets, enhance
        assets = load_assets(media_path)
        frame_transform = lambda html, source_files: enhance(html, source_files, assets)
    from scripts.compare_local_models import check_idle
    check_idle()
    out = Path(tempfile.mkdtemp(prefix='studio-browser-', dir=path.parent))
    observations = {'schema':'studio-browser-audit.v1', 'source_report_sha256':sha256(raw).hexdigest(),
                    'source_checksums':report['source_checksums'], 'checks':[], 'screenshots':[],
                    'accepted':False, 'deployed':False, 'visual_review':'pending', 'status':'incomplete'}
    if media_path:
        from scripts.studio_gallery import STATIC
        observations['media_report_sha256'] = sha256(Path(media_path).read_bytes()).hexdigest()
        observations['overlay_checksums'] = {name:sha256((STATIC/name).read_bytes()).hexdigest()
            for name in ('studio-gallery.css','studio-gallery.js','studio-scene.css','studio-scene.js','studio-tools.css','studio-tools.js','studio-tools.html','studio-navigation.js')}
    def save():
        (out/'report.json').write_text(json.dumps(observations, ensure_ascii=False, indent=2))
    save()
    body = package(client, task_repository, files)

    async def audit(evaluate, context, call, session):
        async def js(expression): return await evaluate(expression, context)
        async def require(name, expression):
            value = await js(expression)
            observations['checks'].append({'id':name, 'passed':value is True})
            if value is not True:
                observations['failed_layout'] = await js("({width:innerWidth,scrollY,scenePosition:document.querySelector('#visuals')?.dataset.scenePosition,scrollWidth:document.documentElement.scrollWidth,focus:document.activeElement.id,menuOpen:document.querySelector('#studio-menu')?.open,briefTop:document.querySelector('#brief-builder')?.getBoundingClientRect().top,overflow:[...document.querySelectorAll('body *')].filter(e=>e.checkVisibility()).map(e=>({tag:e.tagName,cls:e.className,left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right})).filter(r=>r.left<0||r.right>innerWidth+1).slice(0,20)})")
            save()
            assert value is True, name
        async def eventually(name, expression):
            for _ in range(25):
                if await js(expression): break
                await asyncio.sleep(.1)
            await require(name, expression)
        async def shot(name):
            result = await call('Page.captureScreenshot', {'format':'png'}, session)
            content = base64.b64decode(result['data'])
            (out/(name+'.png')).write_bytes(content)
            observations['screenshots'].append({'name':name+'.png', 'sha256':sha256(content).hexdigest()})
            save()
        async def viewport(width, height):
            await call('Emulation.setDeviceMetricsOverride', {'width':width, 'height':height,
                'deviceScaleFactor':1, 'mobile':False}, session)
            await asyncio.sleep(.15)

        await viewport(1440, 1000)
        await require('semantic-layout', "document.querySelectorAll('h1').length===1 && !!document.querySelector('main#main') && !!document.querySelector('footer')")
        await require('labelled-fields-and-live-result', "['service','pages','rush'].every(id=>document.getElementById(id)?.labels?.length>0) && document.querySelector('#result')?.getAttribute('aria-live')==='polite'")
        await require('skip-link', "!!document.querySelector('a[href=\"#main\"]') && document.querySelector('#main')?.getAttribute('tabindex')==='-1'")
        await require('desktop-no-overflow', "document.documentElement.scrollWidth<=innerWidth+1")
        await require('desktop-controls-not-clipped', "[...document.querySelectorAll('button,input,select,summary')].filter(e=>e.checkVisibility()).every(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.left>=-1&&r.right<=innerWidth+1})")
        await require('light-theme', "document.documentElement.dataset.theme==='light'")
        light = await js("getComputedStyle(document.body).backgroundColor+'|'+getComputedStyle(document.documentElement).backgroundColor")
        await shot('desktop-light')
        await js("document.querySelector('#theme-toggle').click()")
        await asyncio.sleep(.15)
        await require('dark-theme', "document.documentElement.dataset.theme==='dark'")
        dark = await js("getComputedStyle(document.body).backgroundColor+'|'+getComputedStyle(document.documentElement).backgroundColor")
        observations['checks'].append({'id':'theme-changes-background', 'passed':light!=dark})
        save()
        assert light != dark, 'Theme attributes alone do not change the rendered page'
        await shot('desktop-dark')
        await js("document.querySelector('#theme-toggle').click()")
        await require('theme-round-trip', "document.documentElement.dataset.theme==='light'")

        if media_path:
            await js("document.querySelector('.scene-journey').scrollIntoView({behavior:'instant'})")
            await eventually('spatial-scene-ready', "document.querySelector('#visuals').classList.contains('scene-ready') && Number(document.querySelector('#visuals').dataset.scenePosition)<.01")
            before = await js("document.querySelector('[data-art=\"1\"]').getBoundingClientRect().width")
            await shot('scene-start')
            await call('Input.dispatchMouseEvent', {'type':'mouseMoved','x':720,'y':450}, session)
            await call('Input.dispatchMouseEvent', {'type':'mouseWheel','x':720,'y':450,'deltaX':0,'deltaY':900}, session)
            await eventually('scene-wheel-moves-through-depth', "Number(document.querySelector('#visuals').dataset.scenePosition)>.3 && !document.querySelector('#art-viewer').open")
            await eventually('scene-spring-settles', "document.querySelector('#visuals').dataset.sceneMoving==='false'")
            after = await js("document.querySelector('[data-art=\"1\"]').getBoundingClientRect().width")
            observations['scene_wheel'] = {'before_width':before, 'after_width':after}
            assert after > before*1.1, 'Next image must visibly approach the viewer'
            await shot('scene-between-chapters')
            await call('Input.dispatchMouseEvent', {'type':'mouseWheel','x':720,'y':450,'deltaX':0,'deltaY':-900}, session)
            await eventually('scene-wheel-reverses', "Number(document.querySelector('#visuals').dataset.scenePosition)<.02")
            await js("document.querySelector('[data-scene-chapter=\"2\"]').click()")
            await eventually('scene-last-chapter', "Number(document.querySelector('#visuals').dataset.scenePosition)>1.98")
            await shot('scene-final-chapter')
            await js("document.querySelector('[data-scene-skip]').click()")
            await eventually('scene-skip-reaches-services', "Math.abs(document.querySelector('#services').getBoundingClientRect().top)<innerHeight/2")
            await js("document.querySelector('[data-scene-chapter=\"1\"]').click()")
            await eventually('scene-chapter-navigation', "Math.abs(Number(document.querySelector('#visuals').dataset.scenePosition)-1)<.02 && document.querySelector('[data-scene-chapter=\"1\"]').getAttribute('aria-current')==='true'")
            await js("document.querySelector('.visual-grid').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
            await eventually('scene-background-restores-previous-view', "Number(document.querySelector('#visuals').dataset.scenePosition)>1.98")
            await js("document.querySelector('[data-scene-chapter=\"1\"]').click()")
            await eventually('scene-return-to-second-study', "Math.abs(Number(document.querySelector('#visuals').dataset.scenePosition)-1)<.02")
            await require('scene-no-horizontal-overflow', "document.documentElement.scrollWidth<=innerWidth+1")
            await require('gallery-images-loaded', "[...document.querySelectorAll('[data-art] img')].length===3 && [...document.querySelectorAll('[data-art] img')].every(i=>i.complete&&i.naturalWidth===768)")
            await shot('gallery-desktop')
            await js("document.querySelector('[data-open-art=\"1\"]').click()")
            await require('gallery-dialog-opens', "document.querySelector('#art-viewer').open && document.querySelector('#art-counter').textContent==='2 / 3'")
            await require('gallery-flies-from-card', "document.querySelector('#art-viewer').dataset.phase==='opening' && document.querySelector('.art-flight')?.getAnimations().some(a=>a.playState==='running')")
            await asyncio.sleep(.12)
            await shot('gallery-opening-motion')
            await eventually('gallery-open-motion-cleans-up', "document.querySelector('#art-viewer').dataset.phase==='open' && !document.querySelector('.art-flight')")
            await js("document.querySelector('[data-zoom-in]').click()")
            await require('gallery-zoom-buttons', "document.querySelector('#zoom-level').textContent==='120%'")
            await require('gallery-allows-native-pinch', "getComputedStyle(document.querySelector('.art-stage')).touchAction.includes('pinch-zoom')")
            point = await js("(()=>{const r=document.querySelector('.art-stage').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()")
            await call('Input.dispatchMouseEvent', {'type':'mouseMoved', **point}, session)
            await asyncio.sleep(.15)
            await call('Input.dispatchMouseEvent', {'type':'mouseWheel', **point, 'deltaX':0,'deltaY':-100}, session)
            for _ in range(10):
                if await js("document.querySelector('#zoom-level').textContent==='130%'"): break
                await asyncio.sleep(.1)
            observations['wheel_observation'] = {'point':point,'zoom':await js("document.querySelector('#zoom-level').textContent")}
            await shot('gallery-wheel')
            await require('gallery-wheel-zoom', "document.querySelector('#zoom-level').textContent==='130%'")
            await js("document.querySelector('[data-next]').click()")
            await require('gallery-switch-animated', "document.querySelector('#art-viewer').dataset.phase==='switching' && document.querySelector('.art-stage img').getAnimations().some(a=>a.playState==='running')")
            await eventually('gallery-switch-complete', "document.querySelector('#art-viewer').dataset.phase==='open'")
            await require('gallery-next-resets-zoom', "document.querySelector('#art-counter').textContent==='3 / 3' && document.querySelector('#zoom-level').textContent==='100%'")
            await shot('gallery-viewer')
            await js("window.galleryCloseTrace=[];document.querySelector('#art-viewer').addEventListener('cancel',()=>window.galleryCloseTrace.push('cancel'));document.querySelector('#art-viewer').addEventListener('close',()=>window.galleryCloseTrace.push('close'))")
            observations['return_target'] = await js("document.querySelector('[data-art=\"2\"] .visual-image').getBoundingClientRect().toJSON()")
            await call('Input.dispatchKeyEvent', {'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27}, session)
            await call('Input.dispatchKeyEvent', {'type':'keyUp','key':'Escape','code':'Escape','windowsVirtualKeyCode':27}, session)
            # Native Escape/cancel is dispatched asynchronously by Chromium.
            for _ in range(10):
                value = await js("({phase:document.querySelector('#art-viewer').dataset.phase,flight:!!document.querySelector('.art-flight'),trace:window.galleryCloseTrace,animations:document.querySelector('.art-stage img').getAnimations().map(a=>a.playState)})")
                observations.setdefault('return_motion', []).append(value)
                save()
                if value['flight']: break
                await asyncio.sleep(.05)
            await require('gallery-return-animated', "document.querySelector('#art-viewer').dataset.phase==='closing' && !!document.querySelector('.art-flight')")
            for _ in range(10):
                if await js("!document.querySelector('#art-viewer').open && document.activeElement.dataset.openArt==='1'"): break
                await asyncio.sleep(.1)
            observations['close_observation'] = await js("({open:document.querySelector('#art-viewer').open,focus:document.activeElement.outerHTML.slice(0,250)})")
            await require('gallery-escape-restores-focus', "!document.querySelector('#art-viewer').open && document.activeElement.dataset.openArt==='1'")
            await eventually('gallery-close-event-complete', "document.querySelector('#art-viewer').dataset.phase==='closed'")
            await js("document.querySelector('[data-open-art=\"1\"]').click()")
            await eventually('gallery-ready-for-background-close', "document.querySelector('#art-viewer').dataset.phase==='open'")
            await call('Input.dispatchMouseEvent', {'type':'mousePressed','x':4,'y':4,'button':'left','clickCount':1}, session)
            await call('Input.dispatchMouseEvent', {'type':'mouseReleased','x':4,'y':4,'button':'left','clickCount':1}, session)
            await eventually('gallery-background-closes', "document.querySelector('#art-viewer').dataset.phase==='closed' && !document.querySelector('#art-viewer').open")

            # One continuous user journey, not isolated feature demonstrations.
            await js("document.querySelector('[data-scene-chapter=\"1\"]').click()")
            await eventually('combined-start-in-scene', "Math.abs(Number(document.querySelector('#visuals').dataset.scenePosition)-1)<.02")
            await js("document.querySelector('.scene-hud a[href=\"#studio\"]').click()")
            await eventually('combined-opens-tools', "Math.abs(document.querySelector('#studio').getBoundingClientRect().top)<innerHeight/2")
            await js("(()=>{const r=document.createRange();r.selectNodeContents(document.querySelector('#studio h2'));getSelection().removeAllRanges();getSelection().addRange(r);document.body.dispatchEvent(new MouseEvent('click',{bubbles:true}));})()")
            await require('selection-does-not-trigger-back', "document.activeElement.id==='studio'")
            await js("getSelection().removeAllRanges();document.body.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,clientX:2,clientY:400}));document.body.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:2,clientY:450}))")
            await require('drag-does-not-trigger-back', "document.activeElement.id==='studio'")
            await js("document.querySelector('#view-return button').click()")
            await eventually('combined-tools-back-restores-scene', "Math.abs(Number(document.querySelector('#visuals').dataset.scenePosition)-1)<.03")
            observations['combined_before_wheel']=await js("({scrollY,position:document.querySelector('#visuals').dataset.scenePosition,target:document.elementFromPoint(720,450).outerHTML.slice(0,150),overflow:getComputedStyle(document.body).overflow})")
            save()
            await call('Input.dispatchMouseEvent', {'type':'mouseMoved','x':720,'y':450}, session)
            await call('Input.dispatchMouseEvent', {'type':'mouseWheel','x':720,'y':450,'deltaX':0,'deltaY':200}, session)
            await eventually('combined-wheel-still-moves-scene', "Number(document.querySelector('#visuals').dataset.scenePosition)>1.05")
            await js("window.combinedScroll=scrollY;document.querySelector('[data-open-art=\"1\"]').click();document.querySelector('#art-viewer').dispatchEvent(new WheelEvent('wheel',{deltaY:-100,bubbles:true,cancelable:true}))")
            await eventually('combined-opening-keeps-wheel-input', "document.querySelector('#art-viewer').dataset.phase==='open' && document.querySelector('#zoom-level').textContent==='110%'")
            await js("document.querySelector('[data-next]').click();document.querySelector('#art-viewer').dispatchEvent(new WheelEvent('wheel',{deltaY:-100,bubbles:true,cancelable:true}))")
            await eventually('combined-switch-keeps-wheel-input', "document.querySelector('#art-viewer').dataset.phase==='open' && document.querySelector('#zoom-level').textContent==='110%' && document.querySelector('#art-counter').textContent==='3 / 3'")
            await js("document.querySelector('[data-close]').click()")
            await eventually('combined-modal-back-preserves-scene', "document.querySelector('#art-viewer').dataset.phase==='closed' && Math.abs(scrollY-window.combinedScroll)<3")
            await call('Input.dispatchMouseEvent', {'type':'mouseWheel','x':720,'y':450,'deltaX':0,'deltaY':-200}, session)
            await eventually('combined-wheel-works-after-modal', "scrollY<window.combinedScroll-100")

            await js("document.querySelector('#studio').scrollIntoView({behavior:'instant'});document.querySelectorAll('.studio-tree details').forEach(e=>e.open=true)")
            await require('functional-tree-expands', "document.querySelectorAll('.studio-tree details[open]').length===3 && [...document.querySelectorAll('.studio-tree a')].every(a=>!!document.querySelector(a.hash))")
            await js("document.querySelector('#brief-type').value='platform';document.querySelector('#brief-goal').value='Portal dla twórców';document.querySelector('.studio-modules input[value=accounts]').click();document.querySelector('.studio-modules input[value=search]').click();document.querySelector('#brief-build').click()")
            await require('brief-composer-real-output', "document.querySelector('#brief-output').value.includes('Portal dla twórców') && document.querySelector('#brief-output').value.includes('Testy odmowy dostępu') && document.querySelector('#brief-output').value.includes('Nie uruchomiono AI') && document.querySelector('#brief-count').textContent.includes('3 / 8')")
            await js("document.querySelector('#brief-select').click()")
            await require('brief-select-for-manual-copy', "document.querySelector('#brief-output').selectionEnd===document.querySelector('#brief-output').value.length && document.querySelector('#brief-output').selectionStart===0")
            for mode in ('orbit','wave','flow','helix'):
                await js(f"document.querySelector('#motion-path').value='{mode}';document.querySelector('#motion-path').dispatchEvent(new Event('input'));document.querySelector('.scene-journey').scrollIntoView({{behavior:'instant'}})")
                await eventually('motion-path-'+mode, f"document.querySelector('#visuals').dataset.sceneMode==='{mode}' && document.querySelector('#visuals').dataset.sceneMoving==='false'")
            await js("document.querySelector('#motion-elasticity').value='80';document.querySelector('#motion-elasticity').dispatchEvent(new Event('input'));document.querySelector('#motion-depth').value='120';document.querySelector('#motion-depth').dispatchEvent(new Event('input'));document.querySelector('#motion-pause').click()")
            frozen = await js("document.querySelector('[data-art=\"1\"]').style.transform+'|'+document.querySelector('[data-art=\"1\"]').style.getPropertyValue('--scene-x')")
            await js("window.scrollBy({top:500,behavior:'instant'})")
            await asyncio.sleep(.15)
            assert frozen == await js("document.querySelector('[data-art=\"1\"]').style.transform+'|'+document.querySelector('[data-art=\"1\"]').style.getPropertyValue('--scene-x')"), 'Paused scene changed'
            await require('motion-controls-pause-and-ranges', "document.querySelector('#motion-pause').getAttribute('aria-pressed')==='true' && document.querySelector('#elasticity-value').textContent==='80%' && document.querySelector('#depth-value').textContent==='120%'")
            await js("document.querySelector('[data-scene-chapter=\"2\"]').click()")
            await require('explicit-navigation-works-while-motion-paused', "Number(document.querySelector('#visuals').dataset.scenePosition)>1.98 && document.querySelector('#motion-pause').getAttribute('aria-pressed')==='true'")
            await js("document.querySelector('#motion-reset').click()")
            await eventually('motion-resumes-and-settles', "document.querySelector('#visuals').dataset.sceneMoving==='false' && document.querySelector('#motion-pause').getAttribute('aria-pressed')==='false'")
            await shot('spring-helix-scene')
            for width,height in ((320,568),(390,844),(768,1024),(1024,768),(1440,900),(2560,1440)):
                await viewport(width,height)
                await js("document.querySelector('#studio').scrollIntoView({behavior:'instant'})")
                await require(f'responsive-tools-{width}', "document.documentElement.scrollWidth<=innerWidth+1 && [...document.querySelectorAll('#studio button,#studio input,#studio select,#studio textarea,.studio-tree summary')].filter(e=>e.checkVisibility()).every(e=>{const r=e.getBoundingClientRect();return r.left>=-1&&r.right<=innerWidth+1&&r.width>0})")
                if width in (320,768): await shot(f'studio-tools-{width}')
                await js("document.querySelector('#studio-menu-toggle').click();document.querySelectorAll('.studio-menu-tree details').forEach(e=>e.open=true)")
                await require(f'responsive-open-menu-{width}', "document.querySelector('#studio-menu').open && (()=>{const r=document.querySelector('#studio-menu').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.top>=0&&r.bottom<=innerHeight+1})() && document.querySelector('#studio-menu').scrollWidth<=document.querySelector('#studio-menu').clientWidth+1")
                if width==320:
                    await asyncio.sleep(.35)
                    await shot('studio-open-menu-320')
                await js("document.querySelector('#studio-menu-close').click()")
                await eventually('studio-menu-closed-'+str(width), "!document.querySelector('#studio-menu').open && document.querySelector('#studio-menu-toggle').getAttribute('aria-expanded')==='false'")
            await viewport(1280,800)
            await js("document.documentElement.style.fontSize='200%'")
            await require('tools-text-scaling-200-percent', "document.documentElement.scrollWidth<=innerWidth+1 && document.querySelector('#brief-build').checkVisibility() && document.querySelector('#motion-path').checkVisibility()")
            await shot('studio-tools-large-text')
            await js("document.documentElement.style.fontSize=''")

        await viewport(390, 844)
        if media_path:
            await require('scene-mobile-editorial-fallback', "!document.querySelector('#visuals').classList.contains('scene-ready') && getComputedStyle(document.querySelector('.scene-stage')).position!=='sticky'")
            await js("scrollTo({top:0,behavior:'instant'})")
            await call('Emulation.setTouchEmulationEnabled', {'enabled':True,'maxTouchPoints':1}, session)
            point=await js("(()=>{const r=document.querySelector('#studio-menu-toggle').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()")
            await call('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[point]}, session)
            await call('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]}, session)
            await eventually('studio-menu-touch-opens', "document.querySelector('#studio-menu').open")
            await call('Input.dispatchKeyEvent', {'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27}, session)
            await call('Input.dispatchKeyEvent', {'type':'keyUp','key':'Escape','code':'Escape','windowsVirtualKeyCode':27}, session)
            await eventually('studio-menu-escape-restores-focus', "document.querySelector('#studio-menu').dataset.phase==='closed' && !document.querySelector('#studio-menu').open && document.activeElement.id==='studio-menu-toggle'")
            await js("document.querySelector('#studio-menu-toggle').click()")
            await call('Input.dispatchMouseEvent', {'type':'mousePressed','x':2,'y':2,'button':'left','clickCount':1}, session)
            await call('Input.dispatchMouseEvent', {'type':'mouseReleased','x':2,'y':2,'button':'left','clickCount':1}, session)
            await eventually('studio-menu-background-closes', "document.querySelector('#studio-menu').dataset.phase==='closed' && !document.querySelector('#studio-menu').open")
            await js("document.querySelector('#studio-menu-toggle').click();document.querySelector('[data-studio-jump=brief-builder]').click()")
            await eventually('studio-menu-opens-working-tool', "!document.querySelector('#studio-menu').open && document.activeElement.id==='brief-builder' && Math.abs(document.querySelector('#brief-builder').getBoundingClientRect().top)<innerHeight/2")
            await call('Emulation.setTouchEmulationEnabled', {'enabled':False}, session)
            await eventually('navigation-return-strip-visible', "document.querySelector('#view-return').checkVisibility() && document.querySelector('#brief-builder').getBoundingClientRect().top>=0")
            await js("document.querySelector('#brief-goal').click();document.querySelector('#brief-goal').value='Zachowaj ten projekt'")
            await require('input-does-not-navigate-back', "window.StudioNavigation.canBack && document.querySelector('#view-return').checkVisibility()")
            await shot('mobile-contextual-return')
            await require('real-click-target-is-empty-background', "['BODY','MAIN','SECTION','DIV','ARTICLE'].includes(document.elementFromPoint(2,500).tagName)")
            await call('Input.dispatchMouseEvent', {'type':'mousePressed','x':2,'y':500,'button':'left','clickCount':1}, session)
            await call('Input.dispatchMouseEvent', {'type':'mouseReleased','x':2,'y':500,'button':'left','clickCount':1}, session)
            await eventually('empty-background-restores-previous-screen', "scrollY<5 && document.activeElement.id==='studio-menu-toggle'")
            await require('back-preserves-brief', "document.querySelector('#brief-goal').value==='Zachowaj ten projekt'")
            await js("document.querySelector('#studio-menu-toggle').click();document.querySelector('[data-studio-jump=brief-builder]').click()")
            await eventually('return-button-ready', "document.querySelector('#studio-menu').dataset.phase==='closed' && document.querySelector('#view-return').checkVisibility() && scrollY>100")
            await js("document.querySelector('#view-return button').click()")
            await eventually('explicit-return-restores-previous-screen', "scrollY<5 && document.activeElement.id==='studio-menu-toggle'")
        await require('mobile-no-overflow', "document.documentElement.scrollWidth<=innerWidth+1")
        await require('mobile-controls-not-clipped', "[...document.querySelectorAll('button,input,select,summary')].filter(e=>e.checkVisibility()).every(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.left>=-1&&r.right<=innerWidth+1})")
        await require('mobile-menu-initially-closed', "document.querySelector('#menu-toggle')?.getAttribute('aria-expanded')==='false' && !document.querySelector('#site-nav')?.checkVisibility()")
        await js("document.querySelector('#menu-toggle').focus();document.querySelector('#menu-toggle').click()")
        await require('mobile-menu-opens', "document.querySelector('#menu-toggle').getAttribute('aria-expanded')==='true' && document.querySelector('#site-nav').checkVisibility()")
        await shot('mobile-menu')
        await call('Input.dispatchKeyEvent', {'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27}, session)
        await call('Input.dispatchKeyEvent', {'type':'keyUp','key':'Escape','code':'Escape','windowsVirtualKeyCode':27}, session)
        await require('escape-closes-and-restores-focus', "document.querySelector('#menu-toggle').getAttribute('aria-expanded')==='false' && !document.querySelector('#site-nav').checkVisibility() && document.activeElement.id==='menu-toggle'")
        await js("document.querySelector('#menu-toggle').click();document.querySelector('#site-nav a[href=\"#quote\"]').click()")
        for _ in range(20):
            if await js("Math.abs(document.querySelector('#quote').getBoundingClientRect().top)<innerHeight"): break
            await asyncio.sleep(.1)
        await require('quote-anchor-target', "Math.abs(document.querySelector('#quote').getBoundingClientRect().top)<innerHeight")
        await shot('mobile-quote')
        await js("document.querySelector('#faq-delivery summary').scrollIntoView();document.querySelector('#faq-delivery summary').click()")
        await require('faq-opens', "document.querySelector('#faq-delivery').open===true && document.querySelector('#faq-delivery').textContent.trim().length>60")
        await js("document.querySelector('#faq-delivery summary').click()")
        await require('faq-closes', "document.querySelector('#faq-delivery').open===false")
        await call('Emulation.setEmulatedMedia', {'features':[{'name':'prefers-reduced-motion','value':'reduce'}]}, session)
        if context[0] != session:
            await call('Emulation.setEmulatedMedia', {'features':[{'name':'prefers-reduced-motion','value':'reduce'}]}, context[0])
        await require('reduced-motion', "matchMedia('(prefers-reduced-motion: reduce)').matches && [...document.querySelectorAll('*')].every(e=>getComputedStyle(e).animationDuration.split(',').every(d=>parseFloat(d)<=0.01))")
        if media_path:
            await viewport(1440,1000)
            await require('scene-desktop-reduced-motion-fallback', "!document.querySelector('#visuals').classList.contains('scene-ready')")
            await viewport(390,844)
            await js("document.querySelector('[data-open-art=\"0\"]').click()")
            await eventually('gallery-reduced-motion-no-flight', "document.querySelector('#art-viewer').dataset.phase==='open' && !document.querySelector('.art-flight') && document.querySelector('#art-viewer').getAnimations({subtree:true}).every(a=>a.playState!=='running')")
            await require('gallery-mobile-controls-visible', "[...document.querySelectorAll('#art-viewer button')].every(b=>{const r=b.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.top>=0&&r.bottom<=innerHeight+1})")
            await shot('gallery-mobile-reduced-motion')
            await js("document.querySelector('[data-close]').click()")
            await eventually('gallery-reduced-motion-close', "!document.querySelector('#art-viewer').open && !document.body.classList.contains('art-open')")
            for target in {session,context[0]}:
                await call('Emulation.setEmulatedMedia', {'features':[{'name':'prefers-reduced-motion','value':'no-preference'}]}, target)
            await js("document.querySelector('[data-open-art=\"1\"]').click();document.querySelector('#art-viewer').dispatchEvent(new WheelEvent('wheel',{deltaY:-100,bubbles:true,cancelable:true}));document.querySelector('[data-close]').click();document.querySelector('[data-close]').click()")
            await eventually('gallery-close-during-animation', "!document.querySelector('#art-viewer').open && !document.querySelector('.art-flight') && !document.body.classList.contains('art-open')")
            await eventually('gallery-fast-close-fully-complete', "document.querySelector('#art-viewer').dataset.phase==='closed'")
            await js("document.querySelector('[data-open-art=\"1\"]').click()")
            await viewport(480,800)
            await eventually('gallery-resize-during-flight-recovers', "document.querySelector('#art-viewer').dataset.phase==='open' && !document.querySelector('.art-flight') && document.querySelector('#zoom-level').textContent==='100%'")
            await js("document.querySelector('[data-close]').click()")
            await eventually('gallery-resized-close-cleans-state', "document.querySelector('#art-viewer').dataset.phase==='closed' && !document.body.classList.contains('art-open')")
            await js("window.savedAnimation=Element.prototype.animate;Element.prototype.animate=undefined;document.querySelector('[data-open-art=\"1\"]').click()")
            await eventually('gallery-missing-animation-api-still-opens', "document.querySelector('#art-viewer').dataset.phase==='open' && !document.querySelector('.art-flight')")
            await js("document.querySelector('[data-close]').click()")
            await eventually('gallery-missing-animation-api-still-closes', "document.querySelector('#art-viewer').dataset.phase==='closed' && !document.body.classList.contains('art-open')")
            await js("Element.prototype.animate=window.savedAnimation;delete window.savedAnimation")

        # This extra requirement belongs to the CSS design brief, not the older
        # functional baseline. Screenshots above survive a rejected design.
        if report.get('stage_kind') == 'css-design':
            await viewport(1440, 1000)
            await require('design-desktop-menu-hidden', "!document.querySelector('#menu-toggle').checkVisibility() && document.querySelector('#site-nav').checkVisibility()")

    try:
        asyncio.run(check(client, body, OWNER_HEADERS, cases=case.BROWSER_CASES, expected_color=None, audit=audit, frame_transform=frame_transform))
        observations['checks'].append({'id':'four-quote-interactions', 'passed':True})
        run_response = client.post('/api/package-runs', headers=OWNER_HEADERS, json=body)
        assert run_response.status_code == 200, run_response.text
        run = run_response.json()
        assert run['state'] == 'passed'
        candidate = client.get(f"/api/package-runs/{run['id']}/candidate.zip", headers=OWNER_HEADERS)
        assert candidate.status_code == 200
        with ZipFile(io.BytesIO(candidate.content)) as archive:
            for name, content in files.items():
                assert archive.read('sources/'+name).decode() == content
            assert json.loads(archive.read('delivery.json'))['accepted'] is False
        (out/'studio-candidate.zip').write_bytes(candidate.content)
        observations['candidate'] = {'name':'studio-candidate.zip', 'sha256':sha256(candidate.content).hexdigest(),
                                     'package_checksum':body['package_checksum'], 'owner_accepted':False}
        if media_path:
            observations['media_report_sha256'] = sha256(Path(media_path).read_bytes()).hexdigest()
            observations['candidate']['includes_media_overlay'] = False
            observations['preview_overlay'] = 'Trusted gallery plus separate ComfyUI manifest; ZIP contains base app only'
        readiness = client.get(f"/api/package-runs/{run['id']}/delivery-readiness", headers=OWNER_HEADERS).json()
        assert readiness['ready'] is False
        observations['checks'].append({'id':'candidate-sources-match-and-release-remains-gated', 'passed':True})
        observations['status'] = 'passed'
        assert task_repository.get_required(body['task_id']).progress == 0
    except Exception as exc:
        observations.update(status='failed', error_type=type(exc).__name__)
        raise
    finally:
        save()
        print('Studio browser report:', out/'report.json')
