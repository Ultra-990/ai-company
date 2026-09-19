"""Short CPU-only browser test. ALL API calls mocked, no real owner token/writes."""
import asyncio
import json
from pathlib import Path
import subprocess
import tempfile
import sys

import websockets

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.package_previews import preview_sources
from app.services.workspace_packages import validate_files


async def check():
    preview = dict(task_id=2, package_id=55, source_checksum='a'*64, **preview_sources({'files':validate_files({
        'index.html':'<link rel="stylesheet" href="styles.css"><main><h1>Podgląd testowy</h1><a href="https://preview-test.invalid/navigation">Link bez nawigacji</a></main>',
        'styles.css':'@import url("https://preview-test.invalid/import.css"); h1 { color:rgb(17,34,51) } body { background-image:url("https://preview-test.invalid/image") }',
    })}))
    # Defense-in-depth test: even bypassing the server filter must not run JS.
    preview['document'] = preview['document'].replace('</body>', '<script>document.documentElement.setAttribute("data-script-ran","yes")</script></body>')
    with tempfile.TemporaryDirectory(prefix='ai-work-check-', ignore_cleanup_errors=True) as profile:
        process = subprocess.Popen([
            '/usr/bin/google-chrome', '--headless', '--disable-gpu', '--disable-extensions',
            '--disable-background-networking', '--no-first-run', '--no-default-browser-check',
            '--remote-debugging-port=0', f'--user-data-dir={profile}', 'about:blank',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            port_file = Path(profile) / 'DevToolsActivePort'
            for _ in range(70):
                if port_file.exists(): break
                await asyncio.sleep(.1)
            port, path = port_file.read_text().splitlines()[:2]
            async with websockets.connect(f'ws://127.0.0.1:{port}{path}', max_size=2*1024*1024) as ws:
                serial = 0
                events = []
                async def call(method, params=None, session=None):
                    nonlocal serial
                    serial += 1
                    msg = dict(id=serial, method=method, params=params or {})
                    if session: msg['sessionId'] = session
                    await ws.send(json.dumps(msg))
                    while True:
                        r = json.loads(await asyncio.wait_for(ws.recv(), 15))
                        if 'method' in r:
                            events.append(r)
                        if r.get('method') == 'Fetch.requestPaused':
                            await ws.send(json.dumps(dict(id=1000000+len(events), method='Fetch.failRequest',
                                                          params=dict(requestId=r['params']['requestId'],errorReason='BlockedByClient'),
                                                          sessionId=r['sessionId'])))
                        if r.get('id') == serial:
                            if 'error' in r: raise RuntimeError(r['error'])
                            return r.get('result', {})
                target = await call('Target.createTarget', {'url':'about:blank'})
                session = (await call('Target.attachToTarget', {'targetId':target['targetId'], 'flatten':True}))['sessionId']
                await call('Page.enable', session=session)
                await call('Network.enable', session=session)
                # A second guard for the test itself: no external test URLs leave Chrome.
                await call('Network.setBlockedURLs', {'urls':['*preview-test.invalid*']}, session)
                async def js(source):
                    r=await call('Runtime.evaluate', {'expression':source,'returnByValue':True,'awaitPromise':True},session)
                    if 'exceptionDetails' in r: raise RuntimeError(r['exceptionDetails'])
                    return r['result'].get('value')
                async def wait(source):
                    for _ in range(80):
                        if await js(source): return
                        await asyncio.sleep(.1)
                    raise AssertionError(source + ': ' + str(await js("document.querySelector('#message')?.textContent")))
                # Entry must remain visible without menu scripts or a running scene.
                await call('Emulation.setScriptExecutionDisabled', {'value':True}, session)
                for entry in ('/os', '/os/spatial'):
                    await call('Page.navigate', {'url':'http://127.0.0.1:8000'+entry}, session)
                    await wait("document.readyState==='complete' && !!document.querySelector('#workbench-shortcut')")
                    for width in (1440, 390):
                        await call('Emulation.setDeviceMetricsOverride', {'width':width,'height':900,'deviceScaleFactor':1,'mobile':width==390},session)
                        assert await js("(()=>{const a=document.querySelector('#workbench-shortcut'),r=a.getBoundingClientRect();return a.pathname==='/os/work'&&r.width>100&&r.height>=44&&r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<innerHeight&&getComputedStyle(a).visibility==='visible'})()"), (entry,width)
                    await js("document.querySelector('#workbench-shortcut').click()")
                    await wait("location.pathname==='/os/work' && document.readyState==='complete' && !!document.querySelector('#access')")
                await call('Emulation.clearDeviceMetricsOverride', session=session)
                await call('Emulation.setScriptExecutionDisabled', {'value':False}, session)
                await call('Page.addScriptToEvaluateOnNewDocument', {'source':'window.previewFixture='+json.dumps(preview)+';'+r'''
window.calls=[];window.failOnce=true;window.order=null;
window.report={report_id:56,package_id:55,source_checksum:'a'.repeat(64),outcome:'issues_found',counts:{passed:1,failed:1,warning:0},not_checked:['Nie uruchomiono kodu.'],checks:[{status:'failed',path:'index.html',line:8,message:'Brak alt <img src=x onerror=alert(1)>'}]};
window.fetch=async(path,options={})=>{
  if(path==='/api/owner-session'){
    const signedIn=document.cookie.includes('mock-owner-session=on');
    if(options.method==='POST'){
      if(options.headers?.Authorization!=='Bearer ui-test-only')return Response.json({}, {status:401});
      document.cookie='mock-owner-session=on;path=/';
    }else if(options.method==='DELETE'){
      document.cookie='mock-owner-session=;path=/;max-age=0';return Response.json({authenticated:false});
    }else if(!signedIn)return Response.json({}, {status:401});
    return Response.json({authenticated:true,csrf:'browser-csrf-only',expires_at:Date.now()/1000+3600});
  }
  if(options.headers instanceof Headers){const h=options.headers;options.headers=Object.fromEntries(h);options.headers.Authorization=h.get('Authorization');}
  calls.push({path,options});
  if(!String(path).startsWith('/api/'))throw new Error('Unexpected request');
  if(options.headers?.Authorization!=='Bearer ui-test-only'&&!(document.cookie.includes('mock-owner-session=on')&&options.headers?.['x-owner-csrf']==='browser-csrf-only'&&options.credentials==='same-origin'))return Response.json({}, {status:401});
  if(path==='/api/upwork-orders'&&options.method==='POST'){
    const b=JSON.parse(options.body);window.upworkRequests=window.upworkRequests||[];upworkRequests.push(b);
    if(upworkRequests.length===1)return Response.json({detail:'Niepewny zapis'},{status:503});
    window.upworkOrder={project_id:200,plan_id:201,brief:{title:b.title,upwork_intake:b},tasks:[11,12,13,14].map((id,i)=>({id,title:['Zakres','Budowa','Testy','Przekazanie'][i],status:'pending',delegation:null})),analysis:null};
    return Response.json(upworkOrder,{status:201});
  }
  if(path==='/api/upwork-orders')return Response.json({orders:window.upworkOrder?[{project_id:200,title:upworkOrder.brief.title}]:[],profile:'Python stdlib, HTTP GET',next_cursor:null});
  if(path==='/api/upwork-orders/200')return Response.json(upworkOrder);
  if(path==='/api/upwork-orders/200/analysis'){
    upworkOrder.analysis={id:201,state:'queued',result_content:null};return Response.json(upworkOrder.analysis);
  }
  if(path==='/api/local-inference/201/run'){
    upworkOrder.analysis={id:201,state:'awaiting_review',result_content:JSON.stringify({fit:'CLARIFY',reason:'<img src=x onerror=alert(1)> doprecyzuj zakres',questions:['Jaka waluta?'],scope:[],acceptance_cases:[],exclusions:['Hosting']})};
    return Response.json(upworkOrder.analysis);
  }
  if(path==='/api/work-orders/200')return Response.json({project_id:200,plan_id:201,brief:{title:'Zlecenie Upwork',goal:'Zakres do realizacji',acceptance_criteria:['Test'],constraints:'Bez publikacji'},tasks:[],artifacts:[]});
  if(path==='/api/work-orders/options')return Response.json({units:[{id:8,key:'digital-experience.websites',name:'Strony internetowe'}]});
  if(path==='/api/client-history')return Response.json({shares:[],next_cursor:null});
  if(path==='/api/work-orders'&&options.method==='POST'){
    const b=JSON.parse(options.body);
    if(failOnce){failOnce=false;return Response.json({}, {status:503});}
    order={project_id:100,plan_id:101,brief:b,tasks:[1,2,3,4].map((id,i)=>({id,title:['Specyfikacja','Implementacja','Testy','Odbiór'][i],status:'pending',approval_status:'pending',progress:0,assigned_role:'test-role',queued:false,completion_criterion:'Potwierdzone dowodem'})),artifacts:[]};
    return Response.json(order,{status:201});
  }
  if(path==='/api/work-orders')return Response.json({orders:order?[{project_id:100,title:order.brief.title}]:[],next_cursor:null});
  if(path==='/api/work-orders/100')return Response.json(order);
  if(path==='/api/tasks/2/workspace-packages/55')return Response.json({artifact_id:55,task_id:2,checksum:'a'.repeat(64),files:[{path:'app.py',size_bytes:42}]});
  if(path==='/api/package-runs'&&options.method==='POST'){
    const b=JSON.parse(options.body);window.runnerRequests=window.runnerRequests||[];runnerRequests.push(b);
    if(runnerRequests.length===1)return Response.json({}, {status:503});
    if(b.task_id!==2||b.package_id!==55||b.package_checksum!=='a'.repeat(64)||!b.confirm_execution)throw Error('Wrong runner binding');
    window.testRun={id:1,task_id:2,package_id:55,package_checksum:'a'.repeat(64),state:'passed',result:{log:'<img src=x onerror=alert(1)>'}};
    return Response.json(testRun);
  }
  if(path==='/api/package-runs')return Response.json({enabled:true,runs:window.testRun?[testRun]:[]});
  if(path==='/api/application-quality'&&options.method==='POST'){
    window.qualityRequests=window.qualityRequests||[];const data=JSON.parse(options.body);qualityRequests.push(data);
    if(qualityRequests.length===1)return Response.json({}, {status:503});
    if(data.max_repairs!==2||!data.confirm_automatic_repairs||data.package_id!==55)throw Error('Bad cycle binding');
    window.qualityCycle={...data,id:88,state:'pending',message:'Cykl zapisany',steps:[]};return Response.json(qualityCycle);
  }
  if(path==='/api/application-quality/88/run'){
    window.qualityRuns=(window.qualityRuns||0)+1;
    qualityCycle={...qualityCycle,state:'passed',final_package_id:57,message:'Poprawiono <img src=x onerror=alert(1)>',steps:[{kind:'test',id:1,state:'failed',package_id:55},{kind:'repair',id:2,state:'awaiting_review',package_id:57},{kind:'test',id:3,state:'passed',package_id:57}]};
    return Response.json(qualityCycle);
  }
  if(path==='/api/application-quality')return Response.json({cycles:window.qualityCycle?[qualityCycle]:[]});
  if(path==='/api/package-runs/1/delivery-readiness'){
    if(window.readinessUnavailable)return Response.json({}, {status:503});
    return Response.json({run_id:1,task_id:2,package_id:55,ready:!!window.ownerAccepted,
      checks:[{passed:true,message:'Testy tej wersji zaliczone'},
              {passed:!!window.ownerAccepted,message:window.ownerAccepted?'Odbiór potwierdzony':'Najpierw odbierz zadanie <img src=x onerror=alert(1)>'}],
      note:'Nie wysłano klientowi.'});
  }
  if(path==='/api/application-revisions'&&options.method==='POST'){
    const b=JSON.parse(options.body);window.revisionRequests=window.revisionRequests||[];revisionRequests.push(b);
    if(revisionRequests.length===1)return Response.json({}, {status:503});
    if(b.task_id!==2||b.package_id!==55||!b.auto_test||!b.confirm_revision)throw Error('Wrong revision binding');
    window.revision={...b,id:77,state:'queued',new_package_id:null,test_state:null};return Response.json(revision);
  }
  if(path==='/api/application-revisions/77/run'){
    window.revisionRuns=(window.revisionRuns||0)+1;
    revision={...revision,state:'awaiting_review',new_package_id:56,test_state:'passed'};return Response.json(revision);
  }
  if(path==='/api/application-revisions')return Response.json({revisions:window.revision?[revision]:[]});
  if(path==='/api/local-inference'&&options.method==='POST'){
    window.inferenceInput=JSON.parse(options.body);
    window.inference={id:1,task_id:1,state:'queued',model:'qwen-test',model_digest:'d'.repeat(64),metrics:{},result_content:null};
    return Response.json(inference);
  }
  if(path==='/api/local-inference')return Response.json({enabled:true,model:'qwen-test',timeout_seconds:180,runs:window.inference?[inference]:[]});
  if(path==='/api/local-inference/1/run'){
    inference.state='awaiting_review';inference.result_content='Kontrolowana atrapa <img src=x onerror=alert(1)>';inference.metrics.elapsed_seconds=.1;
    return Response.json(inference);
  }
  if(path==='/api/local-inference/1/retry'){
    if(!JSON.parse(options.body).confirm)throw Error('Missing confirmation');
    inference.state='queued';inference.metrics.retry_history=[{state:'failed'}];return Response.json(inference);
  }
  if(path==='/api/agent-teams/initialize'||path==='/api/agent-teams')return Response.json({created:6,note:'Dane z rejestru wykonań, nie monitor procesów',teams:[{department_id:300,department:'Testowy dział',active:true,charter:{mission:'Test specjalizacji',target_key:'digital-experience.websites'},agents:[{id:20,role_title:'Kierownik',supervisor_id:2,active:true,assigned_tasks:4,runtime_status:'not_started'},{id:21,role_title:'Wykonawca',supervisor_id:20,active:true,assigned_tasks:1,runtime_status:'awaiting_review',latest_run_states:{awaiting_review:1},specialization:{specialization:'Strony i interakcje',instruction:'Nie uznawaj opisu za dowód <img src=x onerror=alert(1)>',runtime_mode:'local_qwen_on_demand'}}]}]});
  if(path==='/api/agent-teams/300/work')return Response.json({tasks:[{task_id:1,project_id:100,title:'Analiza <img src=x onerror=alert(1)>',status:'in_progress',worker:{name:'Wykonawca'},reviewer:{name:'Kontroler'},run:{id:1,state:'awaiting_review'},planning_blockers:[]}],next_cursor:1});
  if(path==='/api/agent-teams/300/work?before=1')return Response.json({tasks:[],next_cursor:null});
  if(path==='/api/work-orders/100/delegate'){
    order.tasks.forEach((t,i)=>t.delegation={manager:{id:20,name:'Kierownik'},worker:{id:21,name:'Wykonawca'},reviewer:{id:22,name:'Kontroler'},predecessor_id:i?i:null,planning_blockers:i?['Najpierw odbierz wcześniejszy etap.']:[],planning_ready:!i,execution_enabled:false,execution_hold:'Wymagane uzgodnienie zasobów',execution_brief:'Instrukcja <script> nie jest kodem'});
    return Response.json(order);
  }
  if(path==='/api/tasks/1/agent-packet')return Response.json({packet_id:60,task_id:1,checksum:'b'.repeat(64),model_invoked:false,packet:{task_context:{title:'Specyfikacja <script> nie uruchamiaj'},policy:{model_invoked:false}}});
  if(path==='/api/tasks/1/agent-packets/60/prompt')return Response.json({text:'INSTRUKCJA SYSTEMOWA\nTestowy prompt Qwen <script> bez narzędzi.',model_invoked:false});
  if(path==='/api/local-model-queue'&&options.method==='POST'){
    window.queueInput=JSON.parse(options.body);
    window.queueJob={id:1,task_id:1,packet_id:60,state:'queued',attempts:0};return Response.json(queueJob);
  }
  if(path==='/api/local-model-queue')return Response.json({mode:'simulation',live_enabled:false,concurrency:1,reason:'Model wyłączony.',jobs:window.queueJob?[queueJob]:[],next_cursor:null});
  if(path==='/api/local-model-queue/simulate-next'){queueJob.state='simulation_complete';queueJob.attempts=1;queueJob.result_content='SYMULACJA <img src=x onerror=alert(1)>';return Response.json({job:queueJob,model_invoked:false});}
  if(path==='/api/tasks/1/agent-results'){
    const b=JSON.parse(options.body);window.imported=b;
    if(b.packet_id!==60||b.packet_checksum!=='b'.repeat(64))throw Error('Wrong packet version');
    order.tasks[0].status='in_progress';order.tasks[0].attempt_status='awaiting_review';
    return Response.json({attempt_id:70,task_id:1,status:'awaiting_review',model_invoked:false});
  }
  if(path==='/api/tasks/1/review'){
    if(options.method==='POST'){
      const b=JSON.parse(options.body);window.reviewDecision=b;
      if(b.attempt_id!==70||b.result_checksum!=='c'.repeat(64)||!b.accepted)throw Error('Wrong review version');
      order.tasks[0].status='completed';order.tasks[0].attempt_status='completed';order.tasks[0].progress=100;
      order.tasks[1].delegation.planning_ready=true;order.tasks[1].delegation.planning_blockers=[];
      return Response.json(order.tasks[0]);
    }
    return Response.json({id:70,task_id:1,worker_id:'owner-import',result_content:imported.result_content,result_checksum:'c'.repeat(64)});
  }
  if(path==='/api/work-orders/100/website-starter'&&options.method==='POST'){
    order.artifacts=[{id:55,task_id:2,type:'source_code',name:'organization-os.workspace.v1',description:'Szkielet do odbioru'}];
    return Response.json({artifact_id:55},{status:201});
  }
  if(path==='/api/tasks/2/workspace-packages/55/static-check'&&options.method==='POST'){
    order.artifacts.unshift({id:56,task_id:2,type:'test_result',name:'organization-os.static-check.v1',description:'Raport kontroli'});
    return Response.json(report,{status:201});
  }
  if(path==='/api/tasks/2/static-checks/56')return Response.json(report);
  if(path==='/api/tasks/2/workspace-packages/55/disk-export')return Response.json({directory:'/home/marcin/ai-company-workspaces/packages/test-only',file_count:4,verified:true,code_executed:false});
  if(path==='/api/tasks/2/workspace-packages/55/preview')return Response.json(previewFixture);
  throw new Error('Unmocked API call: '+path);
};
'''}, session)
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/os/work'}, session)
                await wait("document.readyState==='complete' && !!document.querySelector('#access')")
                await js("document.querySelector('#token').value='ui-test-only';document.querySelector('#access').requestSubmit()")
                await wait("!document.querySelector('#workspace').hidden && !document.querySelector('#intake button').disabled")
                await js(r"""(()=>{const f=document.querySelector('#intake');
f.elements.title.value='Test <img src=x onerror=alert(1)>';
f.elements.goal.value='Zbudować stronę testową bez sieci.';
f.elements.audience.value='Odbiorcy';f.elements.constraints.value='Bez publikacji';
f.elements.criteria.value='Czytelność\nKlawiatura';f.requestSubmit();})()""")
                await wait("document.querySelector('#message').textContent.includes('Usługa niedostępna') && !document.querySelector('#intake button').disabled")
                await js("document.querySelector('#intake').requestSubmit()")
                await wait("!document.querySelector('#detail').hidden && document.querySelectorAll('.task').length===4")
                assert await js("(()=>{const p=calls.filter(c=>c.path==='/api/work-orders'&&c.options.method==='POST').map(c=>JSON.parse(c.options.body));return p.length===2&&p[0].request_id===p[1].request_id&&p[1].goal==='Zbudować stronę testową bez sieci.'&&p[1].organization_unit_id===8})()"), 'form or idempotency regression'
                assert await js("!document.querySelector('#project-title img') && document.querySelector('#project-title').textContent.includes('<img')"), 'HTML injection'
                await wait("!document.querySelector('#initialize-teams').disabled")
                await js("document.querySelector('#initialize-teams').click()")
                await wait("document.querySelector('#teams').textContent.includes('Testowy dział') && !document.querySelector('#delegate').disabled")
                await js("document.querySelector('#teams details').open=true;document.querySelector('#teams button').click()")
                await wait("document.querySelector('#teams').textContent.includes('Analiza <img') && !document.querySelector('#delegate').disabled")
                assert await js("document.querySelector('#teams').textContent.includes('Wynik oczekuje na odbiór') && !document.querySelector('#teams img') && document.querySelector('#teams a[href=\"/os/work?project=100\"]') && calls.filter(c=>c.path.includes('/local-inference')&&c.options.method==='POST').length===0")
                await js("document.querySelector('#teams [data-more-work]').click()")
                await wait("!document.querySelector('#teams [data-more-work]') && !document.querySelector('#delegate').disabled")
                await js("document.querySelector('#delegate').click()")
                await wait("document.querySelector('#tasks').textContent.includes('Kontroler: Kontroler') && !document.querySelector('#delegate').disabled")
                assert await js("document.querySelector('#tasks').textContent.includes('Najpierw odbierz') && !document.querySelector('#tasks script')"), 'delegation or text safety regression'
                await js("document.querySelector('[data-agent-packet=\"1\"]').click()")
                await wait("document.querySelector('#agent-session').open && !document.querySelector('#agent-source').disabled")
                assert await js("document.querySelector('#agent-instructions').value.includes('<script>') && !document.querySelector('#agent-session script')"), 'packet injection'
                await js("document.querySelector('#agent-prompt').click()")
                await wait("document.querySelector('#agent-instructions').value.includes('Testowy prompt Qwen')&&!document.querySelector('#agent-prompt').disabled")
                assert await js("document.querySelector('#agent-message').textContent.includes('Nie wysłano')&&!document.querySelector('#agent-session script')")
                await js("document.querySelector('#agent-infer').click()")
                await wait("!document.querySelector('#agent-session').open && document.querySelector('#inference-runs').textContent.includes('Wynik przekazany') && !document.querySelector('#inference-refresh').disabled")
                assert await js("inferenceInput.packet_id===60&&inferenceInput.packet_checksum==='b'.repeat(64)&&!document.querySelector('#inference-runs img')&&document.querySelector('#inference-runs').textContent.includes('<img')")
                await js("inference.state='failed';document.querySelector('#inference-refresh').click()")
                await wait("document.querySelector('#inference-runs button')?.textContent.includes('ponowienie') && !document.querySelector('#inference-refresh').disabled")
                await js("document.querySelector('#inference-runs button').click()")
                await wait("document.querySelector('#inference-runs').textContent.includes('Zachowane nieudane próby: 1') && !document.querySelector('#inference-refresh').disabled")
                assert await js("calls.filter(c=>c.path==='/api/local-inference/1/run').length===1 && inference.state==='queued'"), 'retry must not start inference'
                await js("document.querySelector('[data-agent-packet=\"1\"]').click()")
                await wait("document.querySelector('#agent-session').open&&!document.querySelector('#agent-source').disabled")
                await call('Emulation.setDeviceMetricsOverride', {'width':390,'height':900,'deviceScaleFactor':1,'mobile':True},session)
                assert await js("(()=>{const r=document.querySelector('#agent-session').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.height<=innerHeight})()"), 'handoff mobile bounds'
                await call('Emulation.clearDeviceMetricsOverride',session=session)
                await js("document.querySelector('#agent-queue').click()")
                await wait("document.querySelector('#local-queue-jobs').textContent.includes('Oczekuje')&&!document.querySelector('#agent-close').disabled")
                assert await js("queueInput.packet_id===60&&queueInput.packet_checksum==='b'.repeat(64)&&order.tasks[0].status==='pending'")
                await js("document.querySelector('#agent-close').click();document.querySelector('#local-queue-next').click()")
                await wait("document.querySelector('#local-queue-jobs').textContent.includes('Symulacja zakończona')&&!document.querySelector('#local-queue-next').disabled")
                assert await js("order.tasks[0].status==='pending'&&!document.querySelector('#local-queue-jobs img')&&document.querySelector('#local-queue-jobs').textContent.includes('<img')")
                await js("document.querySelector('[data-agent-packet=\"1\"]').click()")
                await wait("document.querySelector('#agent-session').open&&!document.querySelector('#agent-source').disabled")
                await js("document.querySelector('#agent-source').value='Właściciel — test UI';document.querySelector('#agent-result').value='Specyfikacja <img src=x onerror=alert(1)>';document.querySelector('#agent-result-form').requestSubmit()")
                await wait("!document.querySelector('#agent-session').open && !!document.querySelector('[data-agent-review=\"1\"]') && !document.querySelector('#starter').disabled")
                await js("document.querySelector('[data-agent-review=\"1\"]').click()")
                await wait("document.querySelector('#agent-session').open && !document.querySelector('#agent-review-reason').disabled")
                assert await js("document.querySelector('#agent-review-content').value.includes('<img') && !document.querySelector('#agent-session img')"), 'result injection'
                await js("document.querySelector('#agent-review-reason').value='Sprawdzono kryteria';document.querySelector('#agent-review-evidence').value='Ręczny raport';document.querySelector('#agent-review-form').requestSubmit(document.querySelector('[value=accept]'))")
                await wait("!document.querySelector('#agent-session').open && !!document.querySelector('[data-agent-packet=\"2\"]') && !document.querySelector('#starter').disabled")
                assert await js("reviewDecision.result_checksum==='c'.repeat(64)&&document.querySelector('#agent-result').value===''&&document.querySelector('#agent-review-content').value===''")
                await wait("!document.querySelector('#starter').disabled")
                await js("document.querySelector('#starter').click()")
                await wait("document.querySelector('#artifacts button')?.textContent==='Pobierz ZIP'")
                await wait("!document.querySelector('[data-check-package]').disabled")
                await js("document.querySelector('[data-check-package]').click()")
                await wait("!document.querySelector('#check-report').hidden && !!document.querySelector('[data-check-report]')")
                assert await js("document.querySelector('#check-summary').textContent.includes('Wykryto problemy') && !document.querySelector('#check-findings img')")
                await wait("!document.querySelector('[data-check-report]').disabled")
                await js("document.querySelector('[data-check-report]').click()")
                await wait("document.querySelector('#message').textContent.includes('Odczytano raport')")
                await wait("!document.querySelector('[data-disk-export]').disabled")
                await js("document.querySelector('[data-disk-export]').click()")
                await wait("document.querySelector('#message').textContent.includes('Zapis na dysku Linux: /home/marcin/')")
                await wait("!document.querySelector('[data-disk-verify]').disabled")
                await js("document.querySelector('[data-disk-verify]').click()")
                await wait("document.querySelector('#message').textContent.includes('Weryfikacja zapisu:')")
                await wait("!document.querySelector('[data-preview-package]').disabled")
                await js("document.querySelector('[data-preview-package]').click()")
                await wait("document.querySelector('#preview').open && !document.querySelector('#preview-phone').disabled")
                await asyncio.sleep(.3)
                assert await js("document.querySelector('#preview-frame').getAttribute('sandbox')==='' && document.querySelector('#preview-frame').contentDocument===null && !document.querySelector('#preview-frame').srcdoc.includes('ui-test-only')"), 'sandbox/token isolation'
                tree = await call('Page.getFrameTree', session=session)
                frames = tree['frameTree'].get('childFrames', [])
                if frames:
                    preview_session = session
                    frame = frames[0]['frame']['id']
                else:
                    # Chromium may place the opaque sandbox in a separate process.
                    targets = (await call('Target.getTargets'))['targetInfos']
                    target = next(t for t in targets if t['type']=='iframe')
                    preview_session = (await call('Target.attachToTarget', {'targetId':target['targetId'],'flatten':True}))['sessionId']
                    frame = (await call('Page.getFrameTree', session=preview_session))['frameTree']['frame']['id']
                await call('Runtime.enable', session=preview_session)
                context = next(e['params']['context']['id'] for e in reversed(events)
                               if e.get('method')=='Runtime.executionContextCreated'
                               and e['params']['context'].get('auxData', {}).get('frameId')==frame
                               and e['params']['context']['auxData'].get('isDefault'))
                inspection = await call('Runtime.evaluate', {'contextId':context,'expression':"JSON.stringify({color:getComputedStyle(document.querySelector('h1')).color,scriptRan:document.documentElement.hasAttribute('data-script-ran'),parentBlocked:(()=>{try{return !parent.document}catch(e){return e.name==='SecurityError'}})()})",'returnByValue':True}, preview_session)
                state = json.loads(inspection['result']['value'])
                assert state == dict(color='rgb(17, 34, 51)', scriptRan=False, parentBlocked=True), state
                # Retry a CSS fetch from the child while listening to its CDP session.
                await call('Network.enable', session=preview_session)
                await call('Network.setBlockedURLs', {'urls':[]}, preview_session)
                await call('Fetch.enable', {'patterns':[{'urlPattern':'*preview-test.invalid*'}]}, preview_session)
                await call('Runtime.evaluate', {'contextId':context,'expression':"(()=>{const link=document.createElement('link');link.rel='stylesheet';link.href='https://preview-test.invalid/blocked.css';document.head.append(link)})()"},preview_session)
                await js("document.querySelector('#preview-phone').click()")
                assert await js("document.querySelector('#preview-frame').getBoundingClientRect().width===390 && document.querySelector('#preview-phone').getAttribute('aria-pressed')==='true'")
                await call('Input.dispatchKeyEvent', {'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27},session)
                await call('Input.dispatchKeyEvent', {'type':'keyUp','key':'Escape','code':'Escape','windowsVirtualKeyCode':27},session)
                await wait("!document.querySelector('#preview').open && !document.querySelector('#preview-frame').hasAttribute('srcdoc')")
                await js("document.querySelector('[data-preview-package]').click()")
                await wait("document.querySelector('#preview').open && !document.querySelector('#preview-phone').disabled")
                assert await js("calls.every(c=>!c.path.includes('execute') && c.options.redirect==='error' && c.options.credentials==='omit')")
                await call('Emulation.setDeviceMetricsOverride', {'width':390,'height':844,'deviceScaleFactor':1,'mobile':True},session)
                assert await js("document.documentElement.scrollWidth<=innerWidth"), 'mobile overflow'
                assert await js("document.querySelector('#preview').scrollWidth<=document.querySelector('#preview').clientWidth"), 'preview mobile overflow'
                await js("document.querySelector('#theme').click();document.querySelector('#logout').click()")
                assert await js("document.querySelector('#token').value===''&&document.querySelector('#workspace').hidden&&document.querySelector('#project-goal').textContent===''&&document.querySelector('#check-report').hidden&&document.querySelector('#check-findings').textContent===''&&Object.keys(localStorage).every(k=>['organization-theme','organization-palette'].includes(k))&&sessionStorage.length===0")
                assert await js("!document.querySelector('#preview').open && !document.querySelector('#preview-frame').hasAttribute('srcdoc') && document.querySelector('#preview-binding').textContent===''")
                failures = [e['params'].get('blockedReason') for e in events if e.get('method')=='Network.loadingFailed']
                assert 'csp' in failures and not any(e.get('method')=='Fetch.requestPaused' for e in events), failures
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/os/build?task=2&package=55'},session)
                await wait("document.readyState==='complete' && !!document.querySelector('#select-package')")
                await js("document.querySelector('#token').value='ui-test-only';document.querySelector('#access').requestSubmit()")
                await wait("!document.querySelector('#workspace').hidden && !document.querySelector('#select-package button').disabled")
                await js("document.querySelector('#select-package').requestSubmit()")
                await wait("!document.querySelector('#run-form').hidden && !document.querySelector('#run-form button').disabled")
                await js("document.querySelector('#confirm').checked=true;document.querySelector('#run-form').requestSubmit()")
                await wait("document.querySelector('#message').textContent.includes('503')&&!document.querySelector('#run-form button').disabled")
                await js("document.querySelector('#run-form').requestSubmit()")
                await wait("document.querySelector('#runs').textContent.includes('Profil testowy zaliczony')&&!document.querySelector('#refresh').disabled")
                assert await js("runnerRequests.length===2&&runnerRequests[0].request_id===runnerRequests[1].request_id&&!document.querySelector('#runs img')&&document.querySelector('#runs').textContent.includes('<img')")
                assert await js("document.documentElement.scrollWidth<=innerWidth"), 'runner mobile overflow'
                await js("[...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Sprawdź gotowość do przekazania').click()")
                await wait("document.querySelector('#runs').textContent.includes('Wydanie wstrzymane')&&!document.querySelector('#refresh').disabled")
                assert await js("[...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Przygotuj i pobierz zatwierdzone wydanie').hidden&&!document.querySelector('#runs img')")
                await js("window.ownerAccepted=true;[...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Sprawdź gotowość do przekazania').click()")
                await wait("document.querySelector('#runs').textContent.includes('Wersja gotowa')&&!document.querySelector('#refresh').disabled")
                assert await js("![...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Przygotuj i pobierz zatwierdzone wydanie').hidden")
                await js("window.readinessUnavailable=true;[...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Sprawdź gotowość do przekazania').click()")
                await wait("document.querySelector('#message').textContent.includes('503')&&!document.querySelector('#refresh').disabled")
                assert await js("[...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Przygotuj i pobierz zatwierdzone wydanie').hidden")
                await js("[...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Zgłoś poprawkę do tej wersji').click()")
                await wait("!document.querySelector('#revision-editor').hidden")
                await js("document.querySelector('#revision-description').value='Popraw opis <img src=x onerror=alert(1)>';document.querySelector('#revision-expected').value='README podaje adres serwera';document.querySelector('#revision-evidence').value='Przegląd README paczki';document.querySelectorAll('#revision-form input[type=checkbox]').forEach(x=>x.checked=true);document.querySelector('#revision-form').requestSubmit()")
                await wait("document.querySelector('#message').textContent.includes('503')&&!document.querySelector('#refresh').disabled")
                await js("document.querySelector('#revision-form').requestSubmit()")
                await wait("document.querySelector('#message').textContent.includes('Nowa paczka: 56')&&!document.querySelector('#refresh').disabled")
                assert await js("revisionRequests.length===2&&revisionRequests[0].request_id===revisionRequests[1].request_id&&revisionRuns===1&&!document.querySelector('#revision-history img')&&document.querySelector('#revision-history').textContent.includes('<img')")
                await js("window.confirm=()=>true;[...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Testuj i napraw automatycznie').click()")
                await wait("document.querySelector('#message').textContent.includes('503')&&!document.querySelector('#refresh').disabled")
                await js("[...document.querySelectorAll('#runs button')].find(b=>b.textContent==='Testuj i napraw automatycznie').click()")
                await wait("document.querySelector('#quality-history').textContent.includes('Testy zaliczone')&&!document.querySelector('#refresh').disabled")
                assert await js("qualityRequests.length===2&&qualityRequests[0].request_id===qualityRequests[1].request_id&&qualityRuns===1&&!document.querySelector('#quality-history img')&&document.querySelector('#quality-history').textContent.includes('<img')&&document.querySelector('#quality-stop').hidden")
                await js("document.querySelector('#logout').click()")
                assert await js("document.querySelector('#workspace').hidden&&document.querySelector('#runs').textContent===''&&document.querySelector('#token').value===''")
                assert await js("document.querySelector('#revision-editor').hidden&&document.querySelector('#revision-description').value===''&&document.querySelector('#revision-history').textContent===''")
                assert await js("document.querySelector('#quality-history').textContent===''&&document.querySelector('#quality-stop').hidden")
                colors={'neutral':{'light':'rgb(255, 255, 255)','dark':'rgb(0, 0, 0)'},
                        'green':{'light':'rgb(237, 243, 238)','dark':'rgb(8, 18, 14)'},
                        'blue':{'light':'rgb(237, 244, 250)','dark':'rgb(7, 18, 34)'}}
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/os'},session)
                await wait("document.readyState==='complete' && !!document.querySelector('[data-palette-select]')")
                await js("document.querySelector('#workbench-shortcut').click()")
                await wait("location.pathname==='/os/work' && document.readyState==='complete' && !!document.querySelector('[data-palette-select]')")
                await js("document.querySelector('[data-back]').click()")
                await wait("location.pathname==='/os' && document.readyState==='complete' && !!document.querySelector('[data-palette-select]')")
                for palette, modes in colors.items():
                    for mode, background in modes.items():
                        await js(f"(()=>{{const s=document.querySelector('[data-palette-select]');s.value={json.dumps(palette)};s.dispatchEvent(new Event('change'));if(document.documentElement.dataset.theme!=={json.dumps(mode)})document.querySelector('[data-theme-toggle]').click()}})()")
                        for page in ('/os','/os/spatial?graphics=lite','/os/work','/client','/','/progress'):
                            await call('Page.navigate', {'url':'http://127.0.0.1:8000'+page},session)
                            await wait("document.readyState==='complete' && !!document.querySelector('[data-palette-select]')")
                            state=await js("({palette:document.documentElement.dataset.palette,mode:document.documentElement.dataset.theme,background:getComputedStyle(document.body).backgroundColor,home:document.querySelector('[data-home]').pathname,back:!!document.querySelector('[data-back]')})")
                            assert state==dict(palette=palette,mode=mode,background=background,home='/os',back=True),(page,state)
                            assert await js("(()=>{const n=document.querySelector('.app-navigation');return n.scrollWidth<=n.clientWidth})()"), ('navigation overflow',page)
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/os/help#automatic'},session)
                await wait("document.readyState==='complete' && !!document.querySelector('#automatic') && document.querySelector('#automatic').open")
                await wait("document.activeElement===document.querySelector('#automatic summary')")
                assert await js("document.documentElement.scrollWidth<=innerWidth"), 'help mobile overflow'
                await js("document.querySelector('#help-search').value='wlasciciela';document.querySelector('#help-search').dispatchEvent(new Event('input'))")
                assert await js("!document.querySelector('#access').closest('article').hidden && document.querySelector('#help-empty').hidden")
                await js("document.querySelector('#help-search').value='<img src=x onerror=alert(1)>';document.querySelector('#help-search').dispatchEvent(new Event('input'))")
                assert await js("!document.querySelector('#help-empty').hidden && !document.querySelector('.help-shell img')")
                await js("window.dispatchEvent(new Event('beforeprint'))")
                assert await js("[...document.querySelectorAll('.help-article')].every(a=>!a.hidden&&a.querySelector('details').open)")
                await js("window.dispatchEvent(new Event('afterprint'))")
                assert await js("[...document.querySelectorAll('.help-article')].every(a=>a.hidden)")
                await js("document.querySelector('a[href=\"#release\"]').click()")
                await wait("document.querySelector('#release').open && document.querySelector('#help-search').value===''")
                await js("document.querySelector('#help-clear').click()")
                assert await js("document.activeElement.id==='help-search' && document.querySelectorAll('.help-article:not([hidden])').length===11")
                for palette,modes in colors.items():
                    for mode,background in modes.items():
                        await js(f"(()=>{{const s=document.querySelector('[data-palette-select]');s.value={json.dumps(palette)};s.dispatchEvent(new Event('change'));if(document.documentElement.dataset.theme!=={json.dumps(mode)})document.querySelector('[data-theme-toggle]').click()}})()")
                        assert await js('getComputedStyle(document.body).backgroundColor')==background
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/client/help#access'},session)
                await wait("document.readyState==='complete' && !!document.querySelector('#access') && document.querySelector('#access').open")
                assert await js("!document.body.textContent.includes('Qwen') && !document.querySelector('a[href^=\"/os\"]') && document.querySelectorAll('.help-article').length===7")
                assert await js("document.documentElement.scrollWidth<=innerWidth"), 'client help mobile overflow'
                await call('Emulation.setScriptExecutionDisabled', {'value':True},session)
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/client/help'},session)
                await wait("document.readyState==='complete' && !!document.querySelector('#help-search')")
                assert await js("document.querySelectorAll('.help-article details').length===7 && document.querySelector('[data-home]').getAttribute('href')==='/client'")
                await call('Emulation.setScriptExecutionDisabled', {'value':False},session)
                for page in ['/os', '/os/spatial?graphics=lite']:
                    await call('Page.navigate', {'url':'http://127.0.0.1:8000'+page},session)
                    await wait("document.readyState==='complete' && !!document.querySelector('#site-search')")
                    assert await js("document.querySelector('[data-client-entry]').getAttribute('href')==='/client'")
                    for width in [1440,390]:
                        await call('Emulation.setDeviceMetricsOverride', {'width':width,'height':900,'deviceScaleFactor':1,'mobile':width==390},session)
                        await js("document.querySelector('#site-search').focus();document.querySelector('#site-search').value='panel klijenta';document.querySelector('#site-search').dispatchEvent(new Event('input'))")
                        assert await js("document.querySelector('#site-search-results a').getAttribute('href')==='/client' && document.querySelector('#site-search-results').textContent.includes('właściciela')")
                        assert await js("(()=>{const r=document.querySelector('#site-search-results').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight})()"), ('search bounds',page,width)
                    await js("document.querySelector('#site-search').value='wlasciciela podglad';document.querySelector('#site-search').dispatchEvent(new Event('input'))")
                    assert await js("document.querySelector('#site-search-results a').getAttribute('href')==='/os/client-preview'")
                    await js("document.querySelector('#site-search').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}))")
                    assert await js("document.activeElement.getAttribute('href')==='/os/client-preview'")
                    await js("document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
                    assert await js("document.activeElement.id==='site-search' && document.querySelector('#site-search-results').hidden")
                    await js("document.querySelector('#site-search').click()")
                    assert await js("!document.querySelector('#site-search-results').hidden")
                    await js("document.querySelector('#site-search').value='<img src=x onerror=alert(1)>';document.querySelector('#site-search').dispatchEvent(new Event('input'))")
                    assert await js("!document.querySelector('#site-search-results a') && !document.querySelector('#site-search-results img') && document.querySelector('#site-search-results').textContent.includes('Brak wyników')")
                    await js("document.body.click();document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true,cancelable:true}))")
                    assert await js("document.activeElement.id==='site-search'")
                    await js("document.querySelector('#site-search').value='panel klienta';document.querySelector('#site-search').dispatchEvent(new Event('input'));document.querySelector('#site-search').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}))")
                    await wait("location.pathname==='/client' && document.readyState==='complete' && !!document.querySelector('#client-login')")
                    assert await js("!document.querySelector('#site-search')")
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/os'},session)
                await wait("document.readyState==='complete' && !!document.querySelector('#owner-session-button')")
                await js("document.querySelector('#owner-session-button').click();document.querySelector('#owner-session-token').value='ui-test-only';document.querySelector('#owner-session-dialog form').requestSubmit()")
                await wait("window.OwnerSession?.active && document.querySelector('#owner-session-button').textContent.includes('Wyloguj')")
                for page in ['/os/work','/os/build']:
                    await call('Page.navigate', {'url':'http://127.0.0.1:8000'+page},session)
                    await wait("document.readyState==='complete' && window.OwnerSession?.active && !document.querySelector('#workspace').hidden")
                    assert await js("document.querySelector('#token').hidden && document.querySelector('#token').value==='' && Object.keys(localStorage).every(k=>['organization-theme','organization-palette'].includes(k))&&sessionStorage.length===0")
                    assert await js("calls.every(c=>!c.options.headers?.Authorization && c.options.credentials==='same-origin')")
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/os/clients'},session)
                await wait("window.OwnerSession?.active && !document.querySelector('#history-workspace').hidden")
                assert await js("document.querySelector('#history-token').hidden")
                for page,button,field in [('/os/review','open-delivery-center','delivery-token'),('/os/publishing','open-client-publishing','publishing-token')]:
                    await call('Page.navigate', {'url':'http://127.0.0.1:8000'+page},session)
                    await wait("document.readyState==='complete' && window.OwnerSession?.active")
                    await js(f"document.getElementById('{button}').click()")
                    assert await js(f"document.getElementById('{field}').hidden && !document.getElementById('{field}').required")
                    assert await js("calls.every(c=>!c.options.method||c.options.method==='GET')")
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/os/upwork'},session)
                await wait("window.OwnerSession?.active && !document.querySelector('#workspace').hidden")
                assert await js("calls.every(c=>!c.options.method||c.options.method==='GET')")
                await js(r"""(()=>{const f=document.querySelector('#upwork-intake');f.elements.title.value='Upwork <img src=x onerror=alert(1)>';f.elements.job_text.value='Build a small calculator with hours and rate, without accounts.';f.elements.criteria.value='8 * 322 = 2576';f.requestSubmit()})()""")
                await wait("document.querySelector('#message').textContent.includes('Niepewny zapis') && !document.querySelector('#upwork-intake button').disabled")
                await js("document.querySelector('#upwork-intake').requestSubmit()")
                await wait("!document.querySelector('#detail').hidden && !document.querySelector('#analyse').disabled")
                assert await js("upworkRequests.length===2 && upworkRequests[0].request_id===upworkRequests[1].request_id && !document.querySelector('#project-title img')")
                await js("document.querySelector('#analyse').click()")
                await wait("document.querySelector('#analysis-result').textContent.includes('Wymaga wyjaśnienia') && document.querySelector('#analyse').disabled")
                assert await js("!document.querySelector('#analysis-result img') && calls.filter(c=>c.path==='/api/local-inference/201/run').length===1")
                await js("document.querySelector('#refresh').click()")
                await wait("!document.querySelector('#refresh').disabled")
                assert await js("calls.filter(c=>c.path==='/api/local-inference/201/run').length===1 && document.querySelector('#analyse').disabled")
                for width in (1440,390):
                    await call('Emulation.setDeviceMetricsOverride', {'width':width,'height':900,'deviceScaleFactor':1,'mobile':width==390},session)
                    assert await js("document.documentElement.scrollWidth<=innerWidth+1")
                await js("document.querySelector('#continue').click()")
                await wait("location.pathname==='/os/work' && document.querySelector('#project-title')?.textContent==='#200 · Zlecenie Upwork'")
                assert await js("calls.every(c=>!c.options.method||c.options.method==='GET')")
                await call('Emulation.clearDeviceMetricsOverride',session=session)
                print(json.dumps(dict(upwork_intake=True, upwork_analysis=True, upwork_project_navigation=True, upwork_no_real_writes=True)))
                await call('Page.navigate', {'url':'http://127.0.0.1:8000/os/client-preview'},session)
                await wait("document.readyState==='complete' && window.OwnerSession?.active && !!document.querySelector('#client-preview-select')")
                assert await js("document.querySelector('#client-token').hidden && !document.querySelector('#client-token').required")
                await js("document.querySelector('#owner-session-button').click()")
                await wait("!document.cookie.includes('mock-owner-session=on') && !window.OwnerSession?.active && document.querySelector('#owner-session-button')?.textContent==='Zaloguj właściciela'")
                print(json.dumps(dict(owner_session_navigation=True, owner_session_logout=True, navigation_search=True, search_keyboard=True, client_entry=True, help_center=True, help_search=True, help_print_restore=True, help_no_js=True, help_client_separation=True, visible_navigation=True, navigation_without_js=True, form=True, duplicate_retry=True, four_tasks=True, package_action=True,
                                      static_check=True, saved_report=True, disk_export=True, disk_verify=True,
                                      preview_css=True, preview_sandbox=True, preview_network_blocked=True, preview_phone=True,
                                      shared_palettes_36_page_checks=True, same_origin_back=True, text_safety=True, handoff_and_review=True, delivery_readiness=True, automatic_quality=True, logout=True, mobile=True, real_api_writes=False, gpu=False)))
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)


if __name__ == '__main__':
    asyncio.run(check())
