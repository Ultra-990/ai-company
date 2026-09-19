import json
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.main import app
from app.api.package_runner import get_runner
from app.api.local_inference import get_provider_factory
from app.models.artifact import Artifact
from app.models.task import TaskAttempt
from app.services import application_quality as service
from app.services.package_runner import ISOLATION_KEYS
from tests.conftest import OWNER_HEADERS,WORKER_HEADERS
from tests.test_application_revisions import generated
from tests.test_local_inference import config_and_no_network,CONFIG
from tests.test_package_runner import fake_runner,FILES


@pytest.fixture(autouse=True)
def isolated_locks(monkeypatch,tmp_path):monkeypatch.setattr(service,'LOCK_ROOT',tmp_path/'locks')


def body(generated):
    base=generated[0]
    return {k:base[k] for k in ('task_id','package_id','package_checksum','request_id')}|{'max_repairs':2,'confirm_automatic_repairs':True}


def result(passed=True,reason=None,cleanup=True):
    return {'exit_code':0 if passed else 1,'cli_exit_code':0 if passed else 1,'reason':reason,'cleanup_confirmed':cleanup,
        'log':json.dumps({'schema':'python-web-test.v1','tests_ok':passed,'http_ok':True,'source_not_exposed':True,
             'isolation':{k:True for k in ISOLATION_KEYS},'tests_log':'AssertionError: expected multiplication, got addition' if not passed else 'OK','errors':[]})}


def create(client,data):
    r=client.post('/api/application-quality',headers=OWNER_HEADERS,json=data)
    assert r.status_code==200,r.text
    return r.json()


def run(client,id_):
    r=client.post(f'/api/application-quality/{id_}/run',headers=OWNER_HEADERS)
    assert r.status_code==200,r.text
    return r.json()


def test_failing_test_is_repaired_and_retested_without_manual_review(client,generated,task_repository):
    params=body(generated)
    class Runner:
        calls=0
        def run(self,files,config,name):
            Runner.calls+=1
            return result(Runner.calls>1)
    app.dependency_overrides[get_runner]=Runner
    cycle=create(client,params)
    assert create(client,params)['id']==cycle['id']
    done=run(client,cycle['id'])
    assert done['state']=='passed',done
    assert [s['kind'] for s in done['steps']]==['test','repair','test']
    assert Runner.calls==2 and len(generated[2].calls)==2
    assert 'AssertionError' in str(generated[2].calls[-1])
    assert done['final_package_id']!=params['package_id'] and not done['owner_accepted']
    assert run(client,cycle['id'])==done and Runner.calls==2
    with task_repository._session_factory() as s:
        assert s.get(Artifact,params['package_id']).checksum==params['package_checksum']
        assert s.get(TaskAttempt,generated[1]['attempt_id']).verification_status=='rejected'
        reviews=list(s.scalars(select(Artifact).where(Artifact.created_by=='automated_qa',Artifact.name=='Odbiór wyniku zadania')))
        assert json.loads(reviews[0].content)['review_method']=='automatic_test_feedback'


def test_healthy_version_does_not_call_model(client,generated,fake_runner):
    cycle=create(client,body(generated));done=run(client,cycle['id'])
    assert done['state']=='passed' and len(generated[2].calls)==1 and fake_runner.calls==1


def test_locked_decoder_is_exact_bounded_and_does_not_modify_sources():
    from copy import deepcopy
    from app.services.application_profile import SOURCE_SCHEMA
    original=deepcopy(SOURCE_SCHEMA)
    tests='import unittest\n# Unicode: zażółć; quotes: " and \\\n'
    output={'content':'unchanged model response'}
    configs=[]
    class Provider:
        def __init__(self,c):configs.append(c)
        def complete(self,m):return output
    factory=service.locked_test_provider(Provider,tests,service.digest(tests))
    config={'num_predict':4096,'format':'json'}
    assert factory(config).complete([]) is output
    assert configs[0]['format']['properties']['files']['properties']['test_app.py']=={'type':'string','const':tests}
    assert config=={'num_predict':4096,'format':'json'} and SOURCE_SCHEMA==original
    with pytest.raises(ValueError):service.locked_test_provider(Provider,tests,'0'*64)
    with pytest.raises(ValueError):service.locked_test_provider(Provider,'x'*17000,service.digest('x'*17000))


def test_cycle_supplies_locked_schema_to_repair_provider(client,generated,task_repository):
    configs=[]
    class Provider:
        def __init__(self,c):configs.append(c)
        def complete(self,m):
            return {'content':json.dumps({'changes':{'README.md':'Corrected implementation instructions'}}),
                    'model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    class Runner:
        calls=0
        def run(self,*args):Runner.calls+=1;return result(Runner.calls>1)
    app.dependency_overrides[get_provider_factory]=lambda:Provider
    app.dependency_overrides[get_runner]=Runner
    cycle=create(client,body(generated))
    assert run(client,cycle['id'])['state']=='passed'
    assert len(configs)==1
    assert 'test_app.py' not in configs[0]['format']['properties']['changes']['properties']
    with task_repository._session_factory() as s:
        assert service.read_json(s.get(Artifact,cycle['id']))['repair_decoder']==service.REPAIR_PROFILE


def test_failure_feedback_keeps_errors_ahead_of_successful_test_noise():
    raw=json.dumps({'tests_log':'passed\n'*4000,'errors':['discount= expected HTTP400 got200'],
                    'tests_ok':True,'http_ok':False})
    feedback=service.failure_feedback(raw)
    assert 'discount= expected HTTP400 got200' in feedback
    assert feedback.index('expected HTTP400')<feedback.index('tests_log_tail')
    assert 'niezaufane dane' in feedback and len(feedback)<2200
    for log in ('invalid json','[]','null',json.dumps({'errors':'wrong type'}),'x'*50000):
        assert 0<len(service.failure_feedback(log))<2200


@pytest.mark.parametrize('decoder',[None,service.REPAIR_DECODER])
def test_legacy_cycles_keep_full_source_decoder(client,generated,task_repository,decoder):
    class Runner:
        calls=0
        def run(self,*args):Runner.calls+=1;return result(Runner.calls>1)
    app.dependency_overrides[get_runner]=Runner
    cycle=create(client,body(generated))
    with task_repository._session_factory() as s:
        row=s.get(Artifact,cycle['id']);data=service.read_json(row)
        if decoder is None:data.pop('repair_decoder')
        else:data['repair_decoder']=decoder
        row.content=service.canonical_json(data);row.checksum=service.digest(row.content);s.commit()
    assert run(client,cycle['id'])['state']=='passed'


@pytest.mark.parametrize('case',['uncertain','infrastructure','stop','lock'])
def test_unsafe_execution_does_not_trigger_blind_repairs(client,generated,task_repository,case):
    class Runner:
        def run(self,*args):return result(False,'runner_error' if case=='infrastructure' else None,case!='uncertain')
    app.dependency_overrides[get_runner]=Runner
    cycle=create(client,body(generated))
    if case=='stop':
        assert client.post(f"/api/application-quality/{cycle['id']}/stop",headers=OWNER_HEADERS).status_code==200
    if case=='lock':
        with task_repository._session_factory() as s,service.task_lock(s,body(generated)['task_id']):
            assert client.post(f"/api/application-quality/{cycle['id']}/run",headers=OWNER_HEADERS).status_code==409
        return
    done=run(client,cycle['id'])
    assert done['state']==('stopped' if case=='stop' else 'needs_attention')
    assert len(generated[2].calls)==1


def test_changed_tests_cannot_make_cycle_green_and_budget_is_bounded(client,generated):
    class Provider:
        calls=0
        def __init__(self,c):pass
        def complete(self,m):
            Provider.calls+=1
            files=FILES|{'app.py':f'print({Provider.calls})','test_app.py':'# deleted failing tests'}
            return {'content':json.dumps({'changes':{'app.py':files['app.py'],'test_app.py':files['test_app.py']}}),'model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    class Runner:
        calls=0
        def run(self,*args):Runner.calls+=1;return result(False)
    app.dependency_overrides[get_provider_factory]=lambda:Provider
    app.dependency_overrides[get_runner]=Runner
    cycle=create(client,body(generated));done=run(client,cycle['id'])
    assert done['state']=='needs_attention',done
    assert Provider.calls==1 and Runner.calls==1


def test_auth_policy_version_and_active_cycle_guards(client,generated):
    params=body(generated)
    for headers,status in (({},401),(WORKER_HEADERS,403)):
        for method,path in (('get','/api/application-quality'),('post','/api/application-quality/1/run'),('post','/api/application-quality/1/stop')):
            assert getattr(client,method)(path,headers=headers).status_code==status
    for change in ({'max_repairs':3},{'confirm_automatic_repairs':False},{'command':'run anything'}):
        assert client.post('/api/application-quality',headers=OWNER_HEADERS,json=params|change).status_code==422
    assert client.post('/api/application-quality',headers=OWNER_HEADERS,json=params|{'package_checksum':'a'*64}).status_code==409
    cycle=create(client,params)
    assert client.post('/api/application-quality',headers=OWNER_HEADERS,json=params|{'request_id':str(uuid4())}).status_code==409
    assert client.post('/api/application-quality',headers=OWNER_HEADERS,json=params|{'max_repairs':1}).status_code==409
    assert client.get('/api/application-quality',headers=OWNER_HEADERS).json()['cycles'][0]['id']==cycle['id']


def test_resume_after_generation_does_not_reject_twice(client,generated,monkeypatch):
    class Runner:
        calls=0
        def run(self,*args):Runner.calls+=1;return result(Runner.calls>1)
    app.dependency_overrides[get_runner]=Runner
    original=service.revisions.execute
    def crash(*args):
        original(*args)
        raise RuntimeError('test process interrupted after commit')
    monkeypatch.setattr(service.revisions,'execute',crash)
    cycle=create(client,body(generated))
    with pytest.raises(RuntimeError):run(client,cycle['id'])
    monkeypatch.setattr(service.revisions,'execute',original)
    done=run(client,cycle['id'])
    assert done['state']=='passed' and Runner.calls==2 and len(generated[2].calls)==2


@pytest.mark.parametrize('case',['deadline','profile','stop_during_test','unchanged_sources'])
def test_control_changes_and_no_progress(client,generated,task_repository,monkeypatch,case):
    params=body(generated);cycle=create(client,params)
    if case=='deadline':
        from datetime import datetime,timezone,timedelta
        with task_repository._session_factory() as s:
            row=s.get(Artifact,cycle['id']);data=service.read_json(row)
            data['deadline']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
            row.content=service.canonical_json(data);row.checksum=service.digest(row.content);s.commit()
    if case=='profile':monkeypatch.setattr(service.package_runner,'configuration',lambda:{'different':True})
    if case=='stop_during_test':
        class Runner:
            def run(self,*args):
                assert client.post(f"/api/application-quality/{cycle['id']}/stop",headers=OWNER_HEADERS).status_code==200
                return result(False)
        app.dependency_overrides[get_runner]=Runner
    if case=='unchanged_sources':
        class Provider:
            def __init__(self,c):pass
            def complete(self,m):return {'content':json.dumps({'files':FILES}),'model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
        class Runner:
            def run(self,*args):return result(False)
        app.dependency_overrides[get_provider_factory]=lambda:Provider
        app.dependency_overrides[get_runner]=Runner
    done=run(client,cycle['id'])
    assert done['state']=={'deadline':'limit_reached','profile':'needs_attention','stop_during_test':'stopped','unchanged_sources':'needs_attention'}[case]
    assert len(generated[2].calls)==1


import os
@pytest.mark.skipif(os.environ.get('AIC_QUALITY_PILOT')!='1',reason='Opt-in real Qwen and Docker pilot')
def test_real_qwen_automatic_repair_pilot(client,generated,task_repository,monkeypatch):
    from pathlib import Path
    from app.models.task import Task
    from app.models.delegation import TaskDelegation
    from app.models.package_run import PackageRun
    from app.models.local_inference import LocalInference
    from app.services import local_inference,container_runner,package_runner
    from app.services.local_ollama import OllamaProvider,configuration
    from app.services.workspace_packages import read_package
    params=body(generated)
    with task_repository._session_factory() as s:
        task=s.get(Task,params['task_id']);delegation=s.get(TaskDelegation,task.id)
        task.title='Testowa kopia kalkulatora — automatyczna naprawa'
        task.description='Polska aplikacja kalkulatora godzin i stawki. GET /api/estimate?hours=8&rate=322 zwraca total=2576. Napraw wykryte błędy bez zmiany API, interfejsu i testów. Zachowaj zakres małego kalkulatora.'
        delegation.execution_brief=task.description
        delegation.completion_criterion='Koszt to godziny razy stawka; nieujemne skończone liczby; błędne dane dają 400. Istniejące testy regresji muszą przechodzić bez modyfikacji.'
        s.commit()
    monkeypatch.setattr(local_inference,'enabled_config',configuration)
    monkeypatch.setattr(package_runner,'configuration',container_runner.configuration)
    app.dependency_overrides[get_provider_factory]=lambda:OllamaProvider
    app.dependency_overrides[get_runner]=container_runner.ContainerRunner
    cycle=create(client,params)
    done=run(client,cycle['id'])
    with task_repository._session_factory() as s:
        tests=[s.get(PackageRun,x['id']) for x in done['steps'] if x['kind']=='test']
        models=list(s.scalars(select(LocalInference).where(LocalInference.task_id==params['task_id'])))
        report={'cycle':done,'tests':[{'id':t.id,'state':t.state,'result':t.result} for t in tests],
                'model_metrics':[m.metrics for m in models],
                'scope':'Isolated database; deliberately broken copy, no production task/package mutation.'}
    destination=Path(os.environ['AIC_REVISION_PILOT_OUTPUT'])
    (destination/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    assert done['state']=='passed',done
    assert tests[0].state=='failed' and tests[-1].state=='passed'
    assert any(x['kind']=='repair' for x in done['steps'])
    with task_repository._session_factory() as s:
        old_art,old=read_package(s,params['task_id'],params['package_id'])
        new_art,new=read_package(s,params['task_id'],done['final_package_id'])
        old_files={f['path']:f['content'] for f in old['files']};new_files={f['path']:f['content'] for f in new['files']}
        assert old_files['test_app.py']==new_files['test_app.py']
        assert old_art.checksum==params['package_checksum']
        new_checksum=new_art.checksum
    # Independent HTTP assertion, not generated/edited by the repairing model.
    probe=client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json={
        'request_id':str(uuid4()),'task_id':params['task_id'],'package_id':done['final_package_id'],
        'package_checksum':new_checksum,'confirm_execution':True,'path':'/api/estimate?hours=8&rate=322'})
    assert probe.status_code==200,probe.text
    assert json.loads(probe.json()['response']['body'])['total']==2576
    report['independent_http_probe']=probe.json()
    (destination/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    download=client.get(f"/api/package-runs/{done['test_run_id']}/candidate.zip",headers=OWNER_HEADERS)
    assert download.status_code==200
    (destination/'repaired-candidate.zip').write_bytes(download.content)
