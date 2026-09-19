"""Sequential private Chrome, GPU disabled, all API calls mocked. No real tokens/writes."""
import argparse
import asyncio
import base64
import json
from pathlib import Path
import subprocess
import tempfile

import websockets


async def check(output):
    with tempfile.TemporaryDirectory(prefix='ai-client-check-', ignore_cleanup_errors=True) as profile:
        process=subprocess.Popen(['/usr/bin/google-chrome','--headless','--disable-gpu','--disable-extensions','--disable-background-networking','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',f'--user-data-dir={profile}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            path=Path(profile)/'DevToolsActivePort'
            for _ in range(70):
                if path.exists(): break
                await asyncio.sleep(.1)
            port,ws_path=path.read_text().splitlines()[:2]
            async with websockets.connect(f'ws://127.0.0.1:{port}{ws_path}',max_size=8*1024*1024) as ws:
                serial=0
                async def call(method,params=None,session=None):
                    nonlocal serial
                    serial+=1;msg={'id':serial,'method':method,'params':params or {}}
                    if session: msg['sessionId']=session
                    await ws.send(json.dumps(msg))
                    while True:
                        r=json.loads(await asyncio.wait_for(ws.recv(),15))
                        if r.get('id')==serial:
                            if 'error' in r: raise RuntimeError(r['error'])
                            return r.get('result',{})
                target=await call('Target.createTarget',{'url':'about:blank'})
                session=(await call('Target.attachToTarget',{'targetId':target['targetId'],'flatten':True}))['sessionId']
                async def js(source):
                    r=await call('Runtime.evaluate',{'expression':source,'returnByValue':True,'awaitPromise':True},session)
                    if 'exceptionDetails' in r: raise RuntimeError(r['exceptionDetails'])
                    return r['result'].get('value')
                async def wait(source):
                    for _ in range(80):
                        if await js(source):return
                        await asyncio.sleep(.1)
                    raise AssertionError(source)
                async def screenshot(name):
                    data=await call('Page.captureScreenshot',{'format':'png'},session)
                    (output/name).write_bytes(base64.b64decode(data['data']))
                await call('Page.enable',session=session)
                await call('Page.addScriptToEvaluateOnNewDocument',{'source':r'''
window.clientFixture={project:{title:'Studio Forma — strona internetowa',summary:'Projekt demonstracyjny do testu interfejsu, nie rzeczywiste zlecenie. Strona pracowni, portfolio i kontakt.',progress:42,status:'in_progress',next_step:'Uzgodnienie widoku portfolio i wersji mobilnej.',milestones:[
{key:'brief',title:'Ustalenia i zakres',status:'completed',description:'Cel strony, odbiorcy i zakres pierwszego wydania.',deliverable:'Specyfikacja v1: strona główna, portfolio, informacje o pracowni, kontakt.',acceptance_criteria:['Potwierdzony zakres i wyłączenia'],review_note:'Zakres sprawdzony — dane demonstracyjne.'},
{key:'design',title:'Projekt interfejsu',status:'review',description:'Układ treści, typografia i widok mobilny.',deliverable:'Makieta v2: wprowadzenie, siatka projektów, opis pracowni.',acceptance_criteria:['Czytelna nawigacja','Układ mobilny'],review_note:'Do uzgodnienia układ portfolio.'},
{key:'build',title:'Budowa strony',status:'in_progress',description:'Powstają komponenty i widoki dla uzgodnionego zakresu.',deliverable:'Opis wersji roboczej: sekcja wprowadzająca i lista projektów.',acceptance_criteria:['Zgodność z zatwierdzoną makietą']},
{key:'qa',title:'Kontrola jakości',status:'planned',description:'Testy klawiatury, formularza i wersji mobilnej.'},
{key:'delivery',title:'Przekazanie projektu',status:'planned',description:'Instrukcje i uzgodniona wersja do przekazania.'}]},updated_at:'2026-09-12T12:00:00Z',expires_at:'2026-10-01T12:00:00Z',source:'owner_published_snapshot'};
clientFixture.publication_checksum='d'.repeat(64);clientFixture.client_decisions=[];
window.feedbackFixture={id:1,publication_checksum:clientFixture.publication_checksum,stage_index:1,stage_title:'Projekt interfejsu',decision:'changes_requested',comment:'Proszę powiększyć nagłówek.',created_at:clientFixture.updated_at,owner_reply:null,acknowledged_at:null,stage_snapshot:clientFixture.project.milestones[1]};
window.calls=[];window.failRead=false;window.expired=false;window.delayRead=false;
window.fetch=async(path,opts={})=>{
 if(path==='/api/owner-session'){window.sessionProbes=(window.sessionProbes||0)+1;return Response.json({}, {status:401});}
 calls.push({path,method:opts.method||'GET',body:opts.body});
 if(path==='/api/client/overview'){
  if(expired)return Response.json({},{status:401});if(failRead)return Response.json({},{status:503});
  if(delayRead)return new Promise(resolve=>window.finishRead=()=>resolve(Response.json(clientFixture)));
  return Response.json(clientFixture);
 }
 if(path==='/api/client/activity')return Response.json({recorded:true});
 if(path==='/api/client/feedback'&&opts.method==='POST'){window.sentDecision=JSON.parse(opts.body);clientFixture.client_decisions=[feedbackFixture];return Response.json(feedbackFixture);}
 if(path==='/api/client/feedback'||path==='/api/client-shares/8/feedback')return Response.json({feedback:[feedbackFixture],next_cursor:null});
 if(path==='/api/client-feedback/1/acknowledge'){feedbackFixture.owner_reply=JSON.parse(opts.body).reply;feedbackFixture.acknowledged_at=clientFixture.updated_at;return Response.json(feedbackFixture);}
 if(path==='/api/client-history')return Response.json({shares:[{id:8,project_id:5,title:clientFixture.project.title,progress:42,last_activity_at:'2026-09-12T13:00:00Z'}],next_cursor:null});
 if(path==='/api/client-shares/8/history')return Response.json({share:{id:8,project_id:5,updated_at:clientFixture.updated_at},project:clientFixture.project,revisions:[{id:2,kind:'updated',at:clientFixture.updated_at,project:clientFixture.project}],activities:[{id:2,kind:'view_stage',stage_title:'Budowa strony <img src=x onerror=alert(1)>',at:'2026-09-12T13:00:00Z'}],next_revision:null,next_activity:null});
 if(path==='/api/client-shares/8'&&(!opts.method||opts.method==='GET'))return Response.json({share:{id:8,project_id:5,updated_at:clientFixture.updated_at,expires_at:clientFixture.expires_at},project:clientFixture.project});
 if(path==='/api/client-shares'&&opts.method==='POST'){window.createdPublication=JSON.parse(opts.body);return Response.json({id:9,token:'mock-publishing-code',expires_at:'2026-10-01T12:00:00Z'},{status:201});}
 if(String(path).startsWith('/api/organization-os/'))return Response.json({},{status:503});
 throw Error('API not mocked: '+path);
};
'''},session)
                await call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False},session)
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/client'},session)
                await wait("document.readyState==='complete'&&!!document.querySelector('#client-login')")
                assert await js("document.querySelector('#client-project').hidden")
                await js("document.querySelector('#client-token').value='mock-only';document.querySelector('#client-login').requestSubmit()")
                await wait("!document.querySelector('#client-project').hidden")
                assert await js("document.querySelectorAll('#client-milestones button').length===5 && document.querySelectorAll('#client-stage-menu button').length===5")
                assert await js("document.querySelector('.client-sidebar').getBoundingClientRect().right<document.querySelector('.client-content').getBoundingClientRect().left")
                await js("document.querySelector('[data-palette-select]').value='blue';document.querySelector('[data-palette-select]').dispatchEvent(new Event('change'));if(document.documentElement.dataset.theme!=='light')document.querySelector('[data-theme-toggle]').click()")
                await screenshot('client-workflow-light.png')
                await js("document.querySelectorAll('#client-stage-menu button')[2].click()")
                assert await js("document.querySelector('#client-stage-title').textContent==='Budowa strony'&&document.querySelector('#client-stage-deliverable').textContent.includes('Opis wersji roboczej')")
                await js("document.querySelector('[data-client-view=materials]').click();clientFixture.project.progress=43;document.querySelector('#client-refresh').click()")
                await wait("document.querySelector('#client-progress-number').textContent==='43%'")
                assert await js("!document.querySelector('#client-view-materials').hidden&&document.querySelectorAll('#client-materials article').length===3")
                await js("document.querySelector('[data-client-view=reviews]').click()")
                assert await js("document.querySelectorAll('#client-reviews article').length===1")
                await js("document.querySelector('#client-reviews button').click()")
                assert await js("document.querySelector('#client-stage-title').textContent==='Projekt interfejsu'")
                await js("document.querySelector('#client-feedback-open').click()")
                assert await js("document.querySelector('#client-feedback-dialog').open")
                await screenshot('client-decision.png')
                await js("document.querySelector('#client-feedback-choice').value='changes_requested';document.querySelector('#client-feedback-comment').value='Proszę powiększyć nagłówek.';document.querySelector('#client-feedback-confirm').checked=true;document.querySelector('#client-feedback-form').requestSubmit()")
                await wait("document.querySelector('#client-stage-decision').textContent.includes('Proszę powiększyć')")
                assert await js("sentDecision.publication_checksum===clientFixture.publication_checksum&&sentDecision.stage_index===1&&document.querySelector('#client-feedback-open').hidden")
                # Updates retain selection by stable key, including a reorder.
                await js("clientFixture.project.milestones.reverse();document.querySelector('#client-refresh').click()")
                await wait("document.querySelector('#client-stage-position').textContent==='ETAP 4 / 5'")
                await js("clientFixture.project.milestones.reverse();document.querySelector('#client-refresh').click()")
                await wait("document.querySelector('#client-stage-position').textContent==='ETAP 2 / 5'")
                await js("if(document.documentElement.dataset.theme!=='dark')document.querySelector('[data-theme-toggle]').click();window.scrollTo(0,0)")
                await screenshot('client-workflow-dark.png')
                for width in (390,768):
                    await call('Emulation.setDeviceMetricsOverride',{'width':width,'height':900,'deviceScaleFactor':1,'mobile':width==390},session)
                    assert await js("document.documentElement.scrollWidth<=innerWidth"),width
                    assert await js("[...document.querySelectorAll('#client-milestones button')].every(b=>b.scrollHeight<=b.clientHeight+2)"),'nested scrolling'
                    if width==390:await screenshot('client-workflow-phone.png')
                await js("window.failRead=true;document.querySelector('#client-refresh').click()")
                await wait("document.querySelector('#client-message').classList.contains('is-error')")
                assert await js("!document.querySelector('#client-project').hidden")
                await js("window.failRead=false;clientFixture.project.milestones=[{title:'<img src=x onerror=alert(1)>',status:'completed',deliverable:'<script>bad()</script>'}];document.querySelector('#client-refresh').click()")
                await wait("document.querySelectorAll('#client-milestones button').length===1")
                assert await js("!document.querySelector('#client-project img')&&!document.querySelector('#client-project script')&&document.querySelector('#client-stage-deliverable').textContent.includes('<script>')")
                await js("clientFixture.project.milestones=[];document.querySelector('#client-refresh').click()")
                await wait("document.querySelector('#client-stage-detail').hidden")
                assert await js("document.querySelector('#client-milestones').textContent.includes('nie został')")
                await js("window.delayRead=true;document.querySelector('#client-refresh').click()")
                await wait("typeof finishRead==='function'")
                await js("document.querySelector('#client-logout').click();finishRead()")
                await asyncio.sleep(.1)
                assert await js("document.querySelector('#client-project').hidden&&document.querySelector('#client-title').textContent===''&&document.querySelector('#client-stage-deliverable').textContent===''")
                assert await js("calls.filter(c=>c.method==='POST').every(c=>['/api/client/activity','/api/client/feedback'].includes(c.path))")
                await call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False},session)
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/os/clients'},session)
                await wait("document.readyState==='complete'&&!!document.querySelector('#history-access')")
                await js("document.querySelector('#history-token').value='mock-owner';document.querySelector('#history-access').requestSubmit()")
                await wait("!document.querySelector('#history-workspace').hidden&&!document.querySelector('#history-refresh').disabled")
                await js("document.querySelector('[data-share-id]').click()")
                await wait("!document.querySelector('#history-detail').hidden&&!document.querySelector('#history-refresh').disabled")
                assert await js("document.querySelector('#history-events').textContent.includes('<img')&&!document.querySelector('#history-events img')")
                assert await js("document.querySelector('#history-preview').getAttribute('href')==='/os/client-preview?share=8'")
                await js("document.querySelector('#history-feedback textarea').value='Uwzględnimy zmianę w kolejnej publikacji.';document.querySelector('#history-feedback form').requestSubmit()")
                await wait("document.querySelector('#history-feedback').textContent.includes('Odpowiedź wykonawcy')")
                await screenshot('owner-client-history.png')
                await js("document.querySelector('#history-logout').click()")
                assert await js("document.querySelector('#history-events').textContent===''&&document.querySelector('#history-projects').textContent===''")
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/os/client-preview'},session)
                await wait("document.readyState==='complete'&&!!document.querySelector('#client-preview-example')")
                await js("document.querySelector('#client-preview-example').click()")
                assert await js("document.querySelector('#client-title').textContent.includes('PRZYKŁAD')&&document.querySelectorAll('#client-milestones button').length===4&&calls.length===0")
                await screenshot('owner-client-preview-demo.png')
                await js("document.querySelector('#client-logout').click();document.querySelector('#client-token').value='mock-owner';document.querySelector('#client-login').requestSubmit()")
                await wait("!document.querySelector('#client-project').hidden&&document.querySelector('#client-title').textContent.includes('Studio Forma')")
                assert await js("document.querySelector('#client-feedback-open').hidden&&document.querySelector('#client-feedback-load').hidden&&calls.every(c=>c.method==='GET')&&document.querySelector('#client-preview-select').value==='8'")
                await js("document.querySelector('#client-logout').click()")
                assert await js("document.querySelector('#client-preview-select').children.length===0")
                await call('Page.navigate',{'url':'http://127.0.0.1:8000/os/publishing'},session)
                await wait("document.readyState==='complete'&&!!document.querySelector('#publishing-load')")
                await js("document.querySelector('#owner-menu').showModal();document.querySelector('#open-client-publishing').click();document.querySelector('#publishing-token').value='mock-owner';document.querySelector('#publishing-share-id').value='8';document.querySelector('#publishing-load').click()")
                await wait("document.querySelectorAll('#publishing-milestones fieldset').length===5&&!document.querySelector('#publishing-add-stage').disabled")
                assert await js("document.querySelector('#publishing-milestones [data-field=deliverable]').value.includes('Specyfikacja v1')")
                await js("document.querySelector('#publishing-add-stage').click();const s=document.querySelector('#publishing-milestones fieldset:last-child');s.querySelector('[data-field=title]').value='Wsparcie';s.querySelector('[data-field=description]').value='Instrukcja';s.querySelector('[data-field=deliverable]').value='Opublikowany materiał';document.querySelector('#publishing-confirm').checked=true;document.querySelector('#publishing-form').requestSubmit()")
                await wait("!document.querySelector('#publishing-result').hidden")
                assert await js("createdPublication.milestones.length===6&&createdPublication.milestones[5].deliverable==='Opublikowany materiał'&&createdPublication.milestones[0].key==='brief'")
                await js("document.querySelector('#publishing-close').click()")
                await wait("document.querySelector('#publishing-milestones').children.length===0&&document.querySelector('#publishing-client-code').value===''")
                print(json.dumps({'workflow':True,'left_menu':True,'materials':True,'review_view':True,'selection_and_tab_preserved':True,'mobile':True,'text_safety':True,'stale_response_after_logout':True,'owner_history':True,'workflow_publisher':True,'gpu':False,'real_api_writes':False,'screenshots':str(output)}))
        finally:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    asyncio.run(check(args.output))
