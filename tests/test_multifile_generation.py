import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.main import app
from app.api.local_inference import get_provider_factory
from app.models.artifact import Artifact
from app.models.task import TaskAttempt
from app.services import multifile_generation as contract
from app.services.workspace_packages import read_package, PACKAGE_NAME
from tests.test_local_inference import config_and_no_network, CONFIG
from tests.test_application_generation import builder_packet
from tests.test_agent_packets import assigned, packet, submit, review
from tests.test_multifile_preview import preview_sources
from tests.conftest import OWNER_HEADERS


def generation_sources():
    files=preview_sources()
    files['tests/test_logic.py']=files.pop('tests/nested/test_logic.py')
    return files


def enqueue(client,p):
    response=client.post('/api/local-inference',headers=OWNER_HEADERS,json={
        'request_id':str(uuid4()),'task_id':p['task_id'],'packet_id':p['packet_id'],
        'packet_checksum':p['checksum'],'output_profile':contract.PROFILE})
    return response


def test_multifile_generation_records_one_version_without_executing_code(client,task_repository):
    p=builder_packet(client);files=generation_sources()
    class Provider:
        calls=0
        def __init__(self,c):assert c['format']==contract.SOURCE_SCHEMA
        def complete(self,m):
            Provider.calls+=1
            assert 'OUTPUT CONTRACT python-web-multifile-v1' in m[0]['content']
            return dict(content=json.dumps({'files':files}),model=CONFIG['model'],digest=CONFIG['digest'],done_reason='stop')
    app.dependency_overrides[get_provider_factory]=lambda:Provider
    queued=enqueue(client,p);assert queued.status_code==200,queued.text
    path=f"/api/local-inference/{queued.json()['id']}/run"
    result=client.post(path,headers=OWNER_HEADERS)
    assert result.status_code==200,result.text
    data=result.json();assert data['state']=='awaiting_review',data
    assert data['metrics']['output_profile']==contract.PROFILE
    assert Provider.calls==1 and task_repository.get_required(p['task_id']).progress==0
    with task_repository._session_factory() as session:
        source,payload=read_package(session,p['task_id'],data['metrics']['package_id'])
        assert {f['path']:f['content'] for f in payload['files']}==files
        assert source.task_attempt_id==data['attempt_id']
        assert session.get(TaskAttempt,data['attempt_id']).verification_status=='pending'
        assert session.scalar(select(func.count()).select_from(Artifact).where(Artifact.name==PACKAGE_NAME))==1
    assert client.post(path,headers=OWNER_HEADERS).json()==data
    assert Provider.calls==1


@pytest.mark.parametrize('change',[
    lambda f:f.update({'../../escape.py':'x'}),
    lambda f:f.update({'modules/logic.py':'def broken(:'}),
    lambda f:f.pop('tests/test_logic.py'),
    lambda f:f.update({'requirements.txt':'install this'}),
    lambda f:f.update({'app.py':''}),
])
def test_invalid_model_sources_do_not_create_package(client,task_repository,change):
    p=builder_packet(client);files=generation_sources();change(files)
    class Provider:
        def __init__(self,c):pass
        def complete(self,m):return dict(content=json.dumps({'files':files}),model=CONFIG['model'],digest=CONFIG['digest'],done_reason='stop')
    app.dependency_overrides[get_provider_factory]=lambda:Provider
    queued=enqueue(client,p);assert queued.status_code==200,queued.text
    data=client.post(f"/api/local-inference/{queued.json()['id']}/run",headers=OWNER_HEADERS).json()
    assert data['state']=='failed' and data['attempt_id'] is None
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Artifact).where(Artifact.name==PACKAGE_NAME))==0


def test_generation_requires_builder(client):
    p=packet(client,assigned(client)['tasks'][0]['id'])
    assert enqueue(client,p).status_code==409


def test_revision_cannot_regenerate_and_replace_tests(client):
    original=builder_packet(client)
    assert submit(client,original).status_code==200
    assert review(client,original['task_id'],False).status_code==200
    revised=packet(client,original['task_id'])
    assert revised['packet']['revision']['previous_attempt_id'] is not None
    response=enqueue(client,revised)
    assert response.status_code==409 and 'Nie regeneruj' in response.text


@pytest.mark.parametrize('raw',['{"files":{},"files":{}}','[]','```json\n{}\n```','{"files":{},"command":"x"}'])
def test_duplicate_or_extra_contract_keys_are_rejected(raw):
    with pytest.raises(ValueError):contract.parse_sources(raw)
