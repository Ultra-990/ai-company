import json
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.main import app
from app.api.local_inference import get_provider_factory
from app.models.artifact import Artifact
from app.services.workspace_packages import PACKAGE_NAME,read_package
from app.services.application_profile import parse_sources, SOURCE_SCHEMA
from tests.test_local_inference import config_and_no_network,CONFIG
from tests.test_agent_packets import assigned,packet,submit,review
from tests.test_package_runner import FILES
from tests.test_package_runner import fake_runner
from tests.conftest import OWNER_HEADERS


def builder_packet(client):
    tasks=assigned(client)['tasks'];first=packet(client,tasks[0]['id'])
    assert submit(client,first).status_code==200
    assert review(client,tasks[0]['id'],True).status_code==200
    return packet(client,tasks[1]['id'])


def test_qwen_json_creates_atomic_package_and_attempt(client,task_repository):
    p=builder_packet(client)
    class Provider:
        calls=0
        def __init__(self,c):assert c['format']==SOURCE_SCHEMA
        def complete(self,m):
            Provider.calls+=1;assert 'OUTPUT CONTRACT' in m[0]['content']
            return {'content':json.dumps({'files':FILES}),'model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    app.dependency_overrides[get_provider_factory]=lambda:Provider
    body={'request_id':str(uuid4()),'task_id':p['task_id'],'packet_id':p['packet_id'],'packet_checksum':p['checksum'],'output_profile':'python-web-v1'}
    r=client.post('/api/local-inference',headers=OWNER_HEADERS,json=body)
    assert r.status_code==200,r.text
    run=r.json();assert run['limits']['output_profile']=='python-web-v1'
    result=client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS)
    assert result.status_code==200,result.text
    data=result.json();assert data['state']=='awaiting_review' and data['metrics']['package_id']
    with task_repository._session_factory() as s:
        artifact,payload=read_package(s,p['task_id'],data['metrics']['package_id'])
        assert artifact.created_by=='local-ollama' and {f['path']:f['content'] for f in payload['files']}==FILES
        assert artifact.checksum==data['metrics']['package_checksum']
        assert s.scalar(select(func.count()).select_from(Artifact).where(Artifact.name==PACKAGE_NAME))==1
    assert client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS).json()==data
    assert Provider.calls==1 and task_repository.get(p['task_id']).progress==0
    tested=client.post('/api/package-runs',headers=OWNER_HEADERS,json={
        'request_id':str(uuid4()),'task_id':p['task_id'],'package_id':data['metrics']['package_id'],
        'package_checksum':data['metrics']['package_checksum'],'confirm_execution':True})
    assert tested.status_code==200,tested.text
    run_id=tested.json()['id'];assert tested.json()['state']=='passed'
    readiness_path=f'/api/package-runs/{run_id}/delivery-readiness'
    with task_repository._session_factory() as s:
        artifacts_before=s.scalar(select(func.count()).select_from(Artifact))
    readiness=client.get(readiness_path,headers=OWNER_HEADERS)
    assert readiness.status_code==200 and readiness.headers['cache-control']=='no-store'
    assert readiness.json()['ready'] is False
    assert readiness.json()['checks'][0]['passed'] is True
    assert readiness.json()['checks'][1]['passed'] is False
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Artifact))==artifacts_before
    assert client.post(f'/api/package-runs/{run_id}/release',headers=OWNER_HEADERS).status_code==409
    assert review(client,p['task_id'],True).status_code==200
    ready=client.get(readiness_path,headers=OWNER_HEADERS).json()
    assert ready['ready'] and ready['release_id'] is None
    assert not ready['client_accepted'] and not ready['deployed']
    approved=client.post(f'/api/package-runs/{run_id}/release',headers=OWNER_HEADERS)
    assert approved.status_code==200,approved.text
    assert client.post(f'/api/package-runs/{run_id}/release',headers=OWNER_HEADERS).json()['release_id']==approved.json()['release_id']
    ready=client.get(readiness_path,headers=OWNER_HEADERS).json()
    assert ready['ready'] and ready['release_id']==approved.json()['release_id']
    with task_repository._session_factory() as s:
        release=s.get(Artifact,ready['release_id']);original=release.content
        release.content='corrupt';s.commit()
    assert client.get(readiness_path,headers=OWNER_HEADERS).json()['ready'] is False
    with task_repository._session_factory() as s:
        s.get(Artifact,ready['release_id']).content=original;s.commit()
    import io
    from zipfile import ZipFile
    downloaded=client.get(f'/api/package-runs/{run_id}/released.zip',headers=OWNER_HEADERS)
    assert downloaded.status_code==200
    with ZipFile(io.BytesIO(downloaded.content)) as archive:
        manifest=json.loads(archive.read('delivery.json'))
        assert manifest['accepted'] and not manifest['client_accepted'] and not manifest['deployed']
    from app.models.package_run import PackageRun
    with task_repository._session_factory() as s:
        previous=s.get(PackageRun,run_id)
        s.add(PackageRun(request_id=str(uuid4()),task_id=p['task_id'],package_id=previous.package_id,
            package_checksum=previous.package_checksum,container_name='aic-package-'+uuid4().hex,
            state='failed',profile=previous.profile,result={}));s.commit()
    assert client.get(f'/api/package-runs/{run_id}/released.zip',headers=OWNER_HEADERS).status_code==409
    assert client.get(readiness_path,headers=OWNER_HEADERS).json()['ready'] is False


def test_generation_rejects_wrong_role(client):
    p=packet(client,assigned(client)['tasks'][0]['id'])
    body={'request_id':str(uuid4()),'task_id':p['task_id'],'packet_id':p['packet_id'],'packet_checksum':p['checksum'],'output_profile':'python-web-v1'}
    assert client.post('/api/local-inference',headers=OWNER_HEADERS,json=body).status_code==409


@pytest.mark.parametrize('source',[
    '```json\n{}\n```','{"files":{},"files":{}}',
    json.dumps({'files':FILES|{'../escape.py':'x'}}),
    json.dumps({'files':FILES|{'runner_harness.py':'override'}}),
    json.dumps({'files':FILES|{'app.py':''}}),json.dumps({'files':FILES,'command':'danger'}),
])
def test_strict_source_contract(source):
    with pytest.raises(ValueError):parse_sources(source)
