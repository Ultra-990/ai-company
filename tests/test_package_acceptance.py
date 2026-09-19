import io
import json
from hashlib import sha256
from uuid import uuid4
from zipfile import ZipFile

import pytest

from app.models.artifact import Artifact
from app.models.package_run import PackageRun
from app.models.task import Task, TaskStatus
from app.services import package_acceptance, package_runner, acceptance_gate
from app.services.workspace_packages import canonical_json
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_multifile_execution import fake, package, MULTI


def make_candidate(client, repo):
    body=package(client,repo)
    run=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body).json()
    assert run['state']=='passed'
    return body,run


def decision(client,run):
    response=client.get(f"/api/package-runs/{run['id']}/package-review",headers=OWNER_HEADERS)
    assert response.status_code==200,response.text
    return dict(request_id=str(uuid4()),context_checksum=response.json()['context_checksum'],
        accepted=True,confirm_review=True,criteria='Calculation and agreed synthetic scope reviewed.',
        evidence='Reviewed test report and application preview; synthetic owner decision only.')


def post(client,run,payload):
    return client.post(f"/api/package-runs/{run['id']}/package-review",headers=OWNER_HEADERS,json=payload)


def test_review_release_handoff_and_replay_without_task_progress(client,task_repository,fake):
    body,run=make_candidate(client,task_repository)
    payload=decision(client,run)
    review=post(client,run,payload)
    assert review.status_code==200,review.text
    assert post(client,run,payload).json()==review.json()
    assert not task_repository.get_required(body['task_id']).progress
    base=f"/api/package-runs/{run['id']}"
    assert client.get(base+'/delivery-readiness',headers=OWNER_HEADERS).json()['ready']
    released=client.post(base+'/release',headers=OWNER_HEADERS)
    assert released.status_code==200,released.text
    assert client.post(base+'/release',headers=OWNER_HEADERS).json()==released.json()
    handoff=client.get(base+'/handoff',headers=OWNER_HEADERS)
    assert handoff.status_code==200,handoff.text
    assert not handoff.json()['client_accepted'] and not handoff.json()['deployed']
    zip_response=client.get(base+'/released.zip',headers=OWNER_HEADERS)
    assert zip_response.status_code==200
    with ZipFile(io.BytesIO(zip_response.content)) as archive:
        manifest=json.loads(archive.read('delivery.json'))
        assert manifest['accepted'] and manifest['owner_review']['review_id']==review.json()['review_id']
        assert 'unittest discover -s tests -t .' in archive.read('CLIENT-START-HERE.md').decode()
        assert 'python-web-multifile-v1' in archive.read('DELIVERY-SUMMARY.md').decode()
        assert payload['evidence'].encode() not in zip_response.content
    assert fake.calls==1  # Review/download never executes models, code or additional tests.


def test_revocation_blocks_saved_release_and_old_replay_does_not_reaccept(client,task_repository,fake):
    _,run=make_candidate(client,task_repository);payload=decision(client,run)
    post(client,run,payload);base=f"/api/package-runs/{run['id']}"
    old_release=client.post(base+'/release',headers=OWNER_HEADERS).json()
    revoked=post(client,run,payload|{'request_id':str(uuid4()),'accepted':False})
    assert revoked.status_code==200
    assert post(client,run,payload).json()['current'] is False
    assert not client.get(base+'/delivery-readiness',headers=OWNER_HEADERS).json()['ready']
    for suffix in ('released.zip','handoff'):
        assert client.get(base+'/'+suffix,headers=OWNER_HEADERS).status_code==409
    assert client.post(base+'/release',headers=OWNER_HEADERS).status_code==409
    assert post(client,run,payload|{'request_id':str(uuid4())}).status_code==200
    fresh=client.post(base+'/release',headers=OWNER_HEADERS).json()
    assert fresh['release_id']!=old_release['release_id']


@pytest.mark.parametrize('change',['scope','profile','new_test','report','review','release','cancelled'])
def test_changes_invalidate_acceptance(client,task_repository,fake,monkeypatch,change):
    body,run=make_candidate(client,task_repository);payload=decision(client,run)
    review=post(client,run,payload).json();base=f"/api/package-runs/{run['id']}"
    released=client.post(base+'/release',headers=OWNER_HEADERS).json()
    if change=='profile':monkeypatch.setattr(package_runner,'multifile_configuration',lambda: MULTI|{'harness_checksum':'d'*64})
    elif change=='new_test':
        assert client.post('/api/package-runs',headers=OWNER_HEADERS,json=body|{'request_id':str(uuid4())}).status_code==200
    else:
        with task_repository._session_factory() as session:
            if change=='scope':session.get(Task,body['task_id']).description='New scope after review'
            elif change=='cancelled':session.get(Task,body['task_id']).status=TaskStatus.CANCELLED
            else:
                identifier={'report':run['report_id'],'review':review['review_id'],'release':released['release_id']}[change]
                session.get(Artifact,identifier).content='{}'
            session.commit()
    assert not client.get(base+'/delivery-readiness',headers=OWNER_HEADERS).json()['ready']
    assert client.get(base+'/released.zip',headers=OWNER_HEADERS).status_code==409


def test_stale_context_and_request_conflict_are_not_written(client,task_repository,fake):
    _,run=make_candidate(client,task_repository);payload=decision(client,run)
    assert post(client,run,payload|{'context_checksum':'f'*64}).status_code==409
    assert post(client,run,payload).status_code==200
    assert post(client,run,payload|{'accepted':False}).status_code==409


def test_selected_http_plan_cannot_be_bypassed(client,task_repository,fake,monkeypatch):
    _,run=make_candidate(client,task_repository);payload=decision(client,run)
    monkeypatch.setattr(acceptance_gate,'selected',lambda *args: ('selected','plan'))
    assert post(client,run,payload).status_code==409
    assert not client.get(f"/api/package-runs/{run['id']}/delivery-readiness",headers=OWNER_HEADERS).json()['ready']


def test_auth_and_explicit_confirmation(client,task_repository,fake):
    _,run=make_candidate(client,task_repository);payload=decision(client,run)
    url=f"/api/package-runs/{run['id']}/package-review"
    for headers,status in (({},401),(WORKER_HEADERS,403)):
        assert client.get(url,headers=headers).status_code==status
        assert client.post(url,headers=headers,json=payload).status_code==status
    for invalid in ({'confirm_review':False},{'criteria':' '},{'accepted':'true'},{'extra':'value'}):
        assert post(client,run,payload|invalid).status_code==422


def test_new_edited_version_does_not_inherit_acceptance(client,task_repository,fake):
    body,run=make_candidate(client,task_repository);post(client,run,decision(client,run))
    changed=client.post(f"/api/tasks/{body['task_id']}/workspace-packages/{body['package_id']}/edits",
        headers=OWNER_HEADERS,json={'request_id':str(uuid4()),'base_checksum':body['package_checksum'],
            'purpose':'Documentation clarification for the next immutable candidate',
            'changes':{'README.md':'New instructions for this synthetic version.'},'removals':[]})
    assert changed.status_code in (200,201),changed.text
    assert changed.json()['accepted'] is False
    saved=changed.json()['package']
    fake.expected_files=fake.expected_files|{'README.md':'New instructions for this synthetic version.'}
    new_run=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body|{
        'package_id':saved['artifact_id'],'package_checksum':saved['checksum'],'request_id':str(uuid4())}).json()
    assert new_run['state']=='passed'
    new_base=f"/api/package-runs/{new_run['id']}"
    assert not client.get(new_base+'/delivery-readiness',headers=OWNER_HEADERS).json()['ready']
    assert client.post(new_base+'/release',headers=OWNER_HEADERS).status_code==409
    assert post(client,new_run,decision(client,new_run)).status_code==200
    assert client.post(new_base+'/release',headers=OWNER_HEADERS).status_code==200
    with task_repository._session_factory() as session:
        assert session.get(Task,body['task_id']).progress==0
