import json
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.api.local_inference import get_provider_factory
from app.main import app
from app.models.artifact import Artifact
from app.models.local_inference import LocalInference
from app.models.task import Task, TaskAttempt, utc_now
from app.services import local_inference
from app.services.application_profile import REPAIR_PROFILE
from app.services.filewise_application_provider import FILES, FilewiseApplicationProvider
from app.services import multifile_generation
from tests.conftest import OWNER_HEADERS
from tests.test_application_generation import builder_packet
from tests.test_local_inference import CONFIG

FILEWISE_CONFIG=CONFIG|{'num_ctx':32768,'num_predict':4096,
    'application_generation_strategy':'filewise-v1'}
SOURCES={'app.py':'print("server")','test_app.py':'import unittest\nclass T(unittest.TestCase):\n pass',
    'index.html':'<!doctype html><html></html>','style.css':'body{color:navy}',
    'app.js':'document.body.dataset.ready="1"','README.md':'# Demo\nRun python app.py'}

class Provider:
    calls=[]
    fail_at=None
    def __init__(self,config):self.config=config
    def complete(self,messages):
        context=json.loads(messages[-1]['content']);name=context['requested_filename']
        Provider.calls.append(name)
        if len(Provider.calls)==Provider.fail_at:raise TimeoutError('ambiguous transport')
        return {'content':json.dumps({'content':SOURCES[name]}),'model':FILEWISE_CONFIG['model'],
            'digest':FILEWISE_CONFIG['digest'],'done_reason':'stop','elapsed_seconds':.1,
            'eval_count':2,'prompt_eval_count':3}

@pytest.fixture(autouse=True)
def configured(tmp_path,monkeypatch):
    Provider.calls=[];Provider.fail_at=None
    monkeypatch.setattr(local_inference,'enabled_config',lambda:dict(FILEWISE_CONFIG))
    monkeypatch.setattr(local_inference,'ensure_idle',lambda:None)
    monkeypatch.setattr(local_inference,'FILEWISE_EVIDENCE_ROOT',tmp_path/'private-evidence')
    app.dependency_overrides[get_provider_factory]=lambda:Provider
    yield
    app.dependency_overrides.pop(get_provider_factory,None)

def queue(client):
    packet=builder_packet(client)
    response=client.post('/api/local-inference',headers=OWNER_HEADERS,json={
        'request_id':str(uuid4()),'task_id':packet['task_id'],'packet_id':packet['packet_id'],
        'packet_checksum':packet['checksum'],'output_profile':'python-web-v1'})
    assert response.status_code==200,response.text
    return response.json()

def test_normal_api_filewise_snapshots_budgets_and_preserves_evidence(client,task_repository):
    queued=queue(client)
    assert queued['limits']['application_generation_strategy']=='filewise-v1'
    assert queued['limits']['filewise_total_timeout_seconds']==600
    assert queued['limits']['filewise_max_calls']==6
    assert queued['limits']['filewise_max_call_num_predict']==3000
    assert queued['limits']['filewise_assembled_bytes']==32000
    result=client.post(f"/api/local-inference/{queued['id']}/run",headers=OWNER_HEADERS)
    assert result.status_code==200,result.text
    run=result.json();assert run['state']=='awaiting_review' and tuple(Provider.calls)==FILES
    assert run['metrics']['filewise']['attempted_model_calls']==6
    assert run['metrics']['filewise']['assembled'] is True
    assert 'path' not in json.dumps(run['metrics']['filewise'])
    with task_repository._session_factory() as session:
        row=session.get(LocalInference,run['id']);artifact=session.get(
            Artifact,row.metrics['filewise']['artifact_id'])
        assert artifact.checksum==row.metrics['filewise']['artifact_checksum']
        bundle=json.loads(artifact.content)
        assert bundle['schema']=='local-inference-filewise-evidence.v1'
        manifest=json.loads(next(item['content'] for item in bundle['files']
            if item['name']=='manifest.json'))
        assert manifest['status']=='assembled' and manifest['attempted_model_calls']==6
        assert artifact.task_attempt_id==run['attempt_id']

def test_attempted_timeout_is_uncertain_and_keeps_partial_evidence(client,task_repository):
    Provider.fail_at=2;queued=queue(client)
    result=client.post(f"/api/local-inference/{queued['id']}/run",headers=OWNER_HEADERS).json()
    assert result['state']=='uncertain' and result['attempt_id'] is None
    assert Provider.calls==['app.py','test_app.py']
    with task_repository._session_factory() as session:
        row=session.get(LocalInference,result['id'])
        assert row.metrics['filewise']['attempted_model_calls']==2
        artifact=session.get(Artifact,row.metrics['filewise']['artifact_id'])
        assert artifact.task_attempt_id is None

def test_idle_rejection_after_completed_call_is_finished_failure(client,task_repository,monkeypatch):
    checks=[]
    def idle():
        checks.append(True)
        if len(checks)==2:raise ValueError('not idle')
    monkeypatch.setattr(local_inference,'ensure_idle',idle)
    queued=queue(client);result=client.post(
        f"/api/local-inference/{queued['id']}/run",headers=OWNER_HEADERS).json()
    assert result['state']=='failed' and result['attempt_id'] is None
    assert Provider.calls==['app.py']
    with task_repository._session_factory() as session:
        row=session.get(LocalInference,result['id'])
        assert row.metrics['filewise']['attempted_model_calls']==1
        assert row.metrics['filewise']['rejected_before_model']==1


def test_enqueue_uses_exact_first_call_gate_before_any_model(client,monkeypatch):
    monkeypatch.setattr(local_inference,'enabled_config',lambda:dict(
        FILEWISE_CONFIG,num_ctx=4096,num_predict=3000))
    packet=builder_packet(client)
    response=client.post('/api/local-inference',headers=OWNER_HEADERS,json={
        'request_id':str(uuid4()),'task_id':packet['task_id'],'packet_id':packet['packet_id'],
        'packet_checksum':packet['checksum'],'output_profile':'python-web-v1'})
    assert response.status_code==409 and Provider.calls==[]


def test_running_filewise_reservation_uses_whole_batch_deadline(client,task_repository):
    queued=queue(client)
    with task_repository._session_factory() as session:
        row=session.get(LocalInference,queued['id']);row.state='running'
        row.started_at=utc_now()-timedelta(seconds=200);session.commit()
        with pytest.raises(ValueError,match='Nie upłynął'):
            local_inference.requeue(session,row.id,str(uuid4()))


def test_later_growing_context_fails_before_next_transport_and_has_no_product_attempt(
        client,task_repository,monkeypatch):
    large=dict(SOURCES,**{'app.py':'x'*8500})
    monkeypatch.setattr(local_inference,'enabled_config',lambda:dict(
        FILEWISE_CONFIG,num_ctx=14000,num_predict=3000))
    original=SOURCES.copy();SOURCES.update(large)
    try:
        queued=queue(client)
        result=client.post(f"/api/local-inference/{queued['id']}/run",headers=OWNER_HEADERS).json()
    finally:SOURCES.clear();SOURCES.update(original)
    assert result['state']=='failed' and result['error_code']=='filewise_context_limit'
    assert Provider.calls==['app.py'] and result['attempt_id'] is None
    assert 'package_id' not in result['metrics']
    with task_repository._session_factory() as session:
        assert session.scalar(select(TaskAttempt).where(TaskAttempt.id==result['attempt_id'])) is None
        assert session.get(Artifact,result['metrics']['filewise']['artifact_id']) is not None


def test_configuration_change_before_reservation_never_invokes_provider(client,monkeypatch):
    queued=queue(client)
    monkeypatch.setattr(local_inference,'enabled_config',lambda:dict(FILEWISE_CONFIG,num_thread=3))
    result=client.post(f"/api/local-inference/{queued['id']}/run",headers=OWNER_HEADERS).json()
    assert result['state']=='stale' and result['error_code']=='configuration_changed'
    assert Provider.calls==[] and result['attempt_id'] is None


def test_stale_after_filewise_calls_still_persists_valid_evidence(client,task_repository):
    queued=queue(client)
    class Changing(Provider):
        def complete(self,messages):
            result=super().complete(messages)
            if len(Provider.calls)==len(FILES):
                with task_repository._session_factory() as session:
                    task=session.get(Task,queued['task_id']);task.title='changed while model ran';session.commit()
            return result
    with task_repository._session_factory() as session:
        result=local_inference.execute(session,queued['id'],Changing)
        assert result['state']=='stale' and result['attempt_id'] is None
        artifact=session.get(Artifact,result['metrics']['filewise']['artifact_id'])
        assert artifact is not None and artifact.task_attempt_id is None


@pytest.mark.parametrize('tamper', ['request','manifest','oversize','symlink',
    'request_bytes','response_bytes','orphan','state'])
def test_evidence_validator_rejects_tampering_before_db_import(tmp_path,monkeypatch,tamper):
    root=tmp_path/'root';monkeypatch.setattr(local_inference,'FILEWISE_EVIDENCE_ROOT',root)
    directory=root/'run-1-token'
    FilewiseApplicationProvider(FILEWISE_CONFIG,directory,provider_factory=Provider,
        idle_check=lambda:None).complete([{'role':'system','content':'role\n'+
        __import__('app.services.application_profile',fromlist=['INSTRUCTION']).INSTRUCTION},
        {'role':'user','content':'brief'}])
    if tamper=='request':
        path=directory/'01-app.py.request.json';raw=path.read_bytes()
        path.write_bytes(raw.replace(b'"config"',b'"confjg"',1))
    elif tamper=='manifest':
        path=directory/'manifest.json';data=json.loads(path.read_text());data['calls'][0]['source_sha256']='0'*64
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    elif tamper=='oversize':
        (directory/'01-app.py.request.json').write_bytes(b'x'*(1024*1024+1))
    elif tamper=='symlink':
        path=directory/'01-app.py.response.json';path.unlink();path.symlink_to(directory/'manifest.json')
    else:
        path=directory/'manifest.json';data=json.loads(path.read_text())
        if tamper in {'request_bytes','response_bytes'}:
            data['calls'][0][tamper]+=1
        elif tamper=='state':data['calls'][0]['model_attempted']=False
        else:
            data['calls'].pop();data['files'].pop();data['attempted_model_calls']-=1
            data['status']='failed';data['assembled']=False;data.pop('assembled_sha256')
        # Keep aggregate byte accounting consistent so the semantic check must
        # detect an orphan response, false status, or dishonest declared size.
        for _ in range(5):
            raw=json.dumps(data,ensure_ascii=False,indent=2).encode()
            data['evidence_bytes']=sum(p.stat().st_size for p in directory.iterdir()
                if p!=path)+len(raw)
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    with pytest.raises(ValueError,match='invalid_filewise_evidence'):
        local_inference._filewise_bundle(directory)


def test_disk_manifest_is_bound_to_in_memory_execution(tmp_path,monkeypatch):
    root=tmp_path/'root';monkeypatch.setattr(local_inference,'FILEWISE_EVIDENCE_ROOT',root)
    provider=FilewiseApplicationProvider(FILEWISE_CONFIG,root/'run-1-token',
        provider_factory=Provider,idle_check=lambda:None)
    from app.services.application_profile import INSTRUCTION
    provider.complete([{'role':'system','content':'role\n'+INSTRUCTION},
        {'role':'user','content':'brief'}])
    manifest_path=provider.evidence/'manifest.json'
    data=json.loads(manifest_path.read_text())
    data['model']='x'*len(data['model'])
    manifest_path.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    # Internal file/hash accounting alone cannot attest which model ran.
    local_inference._filewise_bundle(provider.evidence)
    with pytest.raises(ValueError,match='invalid_filewise_evidence'):
        local_inference._filewise_bundle(provider.evidence,provider.manifest)


def test_evidence_validator_rejects_symlinked_root_ancestry(tmp_path,monkeypatch):
    real=tmp_path/'real';real.mkdir();alias=tmp_path/'alias';alias.symlink_to(real,target_is_directory=True)
    FilewiseApplicationProvider(FILEWISE_CONFIG,real/'root'/'run-1-token',provider_factory=Provider,
        idle_check=lambda:None).complete([{'role':'system','content':'role\n'+
        __import__('app.services.application_profile',fromlist=['INSTRUCTION']).INSTRUCTION},
        {'role':'user','content':'brief'}])
    root=alias/'root';directory=root/'run-1-token'
    monkeypatch.setattr(local_inference,'FILEWISE_EVIDENCE_ROOT',root)
    with pytest.raises(ValueError,match='invalid_filewise_evidence'):
        local_inference._filewise_bundle(directory)


def test_non_filewise_profiles_keep_single_provider_call(client,task_repository,monkeypatch):
    class Single:
        calls=[]
        def __init__(self,config):self.config=config
        def complete(self,messages):
            Single.calls.append(self.config.get('format'))
            if self.config.get('format')==multifile_generation.SOURCE_SCHEMA:
                files={'app.py':'a','index.html':'<!doctype html>','README.md':'r',
                    'modules/__init__.py':'','modules/logic.py':'x=1','tests/__init__.py':'',
                    'tests/test_logic.py':'import unittest'}
                content=json.dumps({'files':files})
            elif self.config.get('format'):
                content=json.dumps({'changes':{'app.py':'print(2)'}})
            else:content='plain text result'
            return {'content':content,'model':FILEWISE_CONFIG['model'],'digest':FILEWISE_CONFIG['digest'],
                'done_reason':'stop'}
    def run_profile(profile,queued_profile=None):
        packet=builder_packet(client)
        response=client.post('/api/local-inference',headers=OWNER_HEADERS,json={
            'request_id':str(uuid4()),'task_id':packet['task_id'],'packet_id':packet['packet_id'],
            'packet_checksum':packet['checksum'],'output_profile':queued_profile or profile})
        assert response.status_code==200,response.text
        with task_repository._session_factory() as session:
            if queued_profile:
                row=session.get(LocalInference,response.json()['id'])
                row.limits=dict(row.limits)|{'output_profile':profile};session.commit()
            return local_inference.execute(session,response.json()['id'],Single)
    assert run_profile('text')['state']=='awaiting_review'
    assert run_profile(multifile_generation.PROFILE)['state']=='awaiting_review'
    monkeypatch.setattr(local_inference,'repair_base',lambda packet:dict(SOURCES))
    real_messages_for=local_inference.messages_for
    monkeypatch.setattr(local_inference,'messages_for',lambda messages,profile:
        messages if profile==REPAIR_PROFILE else real_messages_for(messages,profile))
    monkeypatch.setattr(local_inference,'assemble_repair',lambda raw,base:(
        json.dumps({'files':base|{'app.py':'print(2)'}}),base|{'app.py':'print(2)'},['app.py']))
    assert run_profile(REPAIR_PROFILE,'text')['state']=='awaiting_review'
    assert len(Single.calls)==3


def test_requeue_filewise_deadline_boundary_is_615_seconds(
        client,task_repository,monkeypatch):
    queued=queue(client);now=utc_now()
    monkeypatch.setattr(local_inference,'utc_now',lambda:now)
    with task_repository._session_factory() as session:
        row=session.get(LocalInference,queued['id']);row.state='running';row.started_at=now-timedelta(seconds=615)
        session.commit()
        with pytest.raises(ValueError,match='Nie upłynął'):
            local_inference.requeue(session,row.id,str(uuid4()))
        session.rollback();row=session.get(LocalInference,queued['id'])
        row.started_at=now-timedelta(seconds=615,microseconds=1);session.commit()
        assert local_inference.requeue(session,row.id,str(uuid4()))['state']=='queued'


def test_response_after_total_deadline_is_evidenced_but_never_packaged(
        client,task_repository,monkeypatch):
    class Clock:
        value=0
        def __call__(self):return self.value
    clock=Clock()
    class LateFinal(Provider):
        def complete(self,messages):
            response=super().complete(messages)
            if len(Provider.calls)==len(FILES):clock.value=601
            return response
    class TimedFilewise(FilewiseApplicationProvider):
        def __init__(self,*args,**kwargs):super().__init__(*args,clock=clock,**kwargs)
    monkeypatch.setattr(local_inference,'FilewiseApplicationProvider',TimedFilewise)
    queued=queue(client)
    with task_repository._session_factory() as session:
        result=local_inference.execute(session,queued['id'],LateFinal)
        assert result['state']=='failed' and result['error_code']=='model_timeout'
        assert result['attempt_id'] is None and 'package_id' not in result['metrics']
        artifact=session.get(Artifact,result['metrics']['filewise']['artifact_id'])
        bundle=json.loads(artifact.content)
        manifest=json.loads(next(item['content'] for item in bundle['files']
            if item['name']=='manifest.json'))
        assert manifest['attempted_model_calls']==6
        assert manifest['calls'][-1]['response_sha256']
        assert manifest['calls'][-1]['status']=='model_attempted'
