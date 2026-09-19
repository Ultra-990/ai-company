import json
from uuid import uuid4
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
import pytest

from app.models.artifact import Artifact
from app.models.task import TaskAttempt
from app.services.package_edits import assemble, protected_test
from app.services.workspace_packages import read_package
from app.services.application_layout import execution_profile
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_workspace_packages import save


def setup(client, repository):
    task = repository.create(title='Zmiana projektu wieloplikowego')
    package = save(client, task.id, files={'app.py':'# original', 'src/lib.py':'raise RuntimeError("never run")',
                                         'tests/test_logic.py':'# preserved', 'index.html':'old'}).json()
    root = f"/api/tasks/{task.id}/workspace-packages/{package['artifact_id']}"
    body = dict(request_id=str(uuid4()), base_checksum=package['checksum'], purpose='Poprawa logiki i stylów',
                changes={'src/lib.py':'# new text only', 'assets/style.css':'body {color: blue}'}, removals=['index.html'])
    return task, package, root, body


def test_multifile_edit_is_immutable_replayable_and_keeps_tests(client,task_repository):
    task,base,root,body=setup(client,task_repository)
    response=client.post(root+'/edits',json=body,headers=OWNER_HEADERS)
    assert response.status_code==200,response.text
    data=response.json()
    assert not data['executed'] and not data['accepted'] and not data['tests_inherited']
    assert data['package']['artifact_id']!=base['artifact_id']
    assert data['package']['execution_profile'] is None
    assert response.headers['cache-control']=='no-store'
    replay=client.post(root+'/edits',json=body,headers=OWNER_HEADERS)
    assert replay.json()==data
    with task_repository._session_factory() as session:
        _,old=read_package(session,task.id,base['artifact_id'])
        new,new_payload=read_package(session,task.id,data['package']['artifact_id'])
        before={e['path']:e['content'] for e in old['files']}
        after={e['path']:e['content'] for e in new_payload['files']}
        assert before['src/lib.py']=='raise RuntimeError("never run")'
        assert after['src/lib.py']=='# new text only'
        assert after['tests/test_logic.py']==before['tests/test_logic.py']
        assert 'index.html' not in after and 'index.html' in before
        assert new.task_attempt_id is None
        assert session.scalar(select(func.count()).select_from(TaskAttempt))==0
        assert session.scalar(select(func.count()).select_from(Artifact))==3
    assert task_repository.get_required(task.id).progress==task.progress


def test_source_endpoint_returns_inert_bound_text(client,task_repository):
    task,base,root,_=setup(client,task_repository)
    response=client.get(root+'/source',params={'path':'src/lib.py'},headers=OWNER_HEADERS)
    assert response.status_code==200
    assert response.json()['content']=='raise RuntimeError("never run")'
    assert response.json()['package_checksum']==base['checksum']
    assert response.headers['content-type']=='application/json'
    assert response.headers['cache-control']=='no-store'
    assert client.get(root+'/source',params={'path':'tests/test_logic.py'},headers=OWNER_HEADERS).json()['protected_test']
    for path in ('/etc/passwd','../secret','missing.py'):
        assert client.get(root+'/source',params={'path':path},headers=OWNER_HEADERS).status_code==404


@pytest.mark.parametrize('changes,removals', [
    ({},[]), ({'../escape.py':'x'},[]), ({'tests/test_logic.py':'pass'},[]),
    ({},['tests/test_logic.py']), ({},['missing.py']), ({'src/lib.py':'x'},['src/lib.py']),
    ({'app.py':'# original'},[]), ({'SRC/LIB.py':'x'},[]), ({'src':'x'},[]),
    ({'src/x.py':'x'},['index.html','index.html']),
])
def test_invalid_edits_do_not_create_versions(client,task_repository,changes,removals):
    _,_,root,body=setup(client,task_repository)
    response=client.post(root+'/edits',json=body|dict(changes=changes,removals=removals),headers=OWNER_HEADERS)
    assert response.status_code==409,response.text
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Artifact))==1


def test_conflict_and_authorization(client,task_repository):
    task,base,root,body=setup(client,task_repository)
    for headers,status in (({},401),(WORKER_HEADERS,403)):
        assert client.post(root+'/edits',json=body,headers=headers).status_code==status
        assert client.get(root+'/source?path=app.py',headers=headers).status_code==status
    assert client.post(root+'/edits',json=body|{'base_checksum':'f'*64},headers=OWNER_HEADERS).status_code==409
    assert client.post(root+'/edits',json=body,headers=OWNER_HEADERS).status_code==200
    assert client.post(root+'/edits',json=body|{'purpose':'Different'},headers=OWNER_HEADERS).status_code==409
    other=task_repository.create(title='Other')
    other_root=f"/api/tasks/{other.id}/workspace-packages/{base['artifact_id']}"
    assert client.get(other_root+'/source?path=app.py',headers=OWNER_HEADERS).status_code==404
    assert client.post(other_root+'/edits',json=body,headers=OWNER_HEADERS).status_code==404


def test_validation_size_limit_and_receipt_integrity(client,task_repository,monkeypatch):
    _,_,root,body=setup(client,task_repository)
    assert client.post(root+'/edits',json=body|{'command':'run'},headers=OWNER_HEADERS).status_code==422
    result=client.post(root+'/edits',json=body,headers=OWNER_HEADERS).json()
    with task_repository._session_factory() as session:
        session.get(Artifact,result['receipt_id']).content='{}'
        session.commit()
    assert client.post(root+'/edits',json=body,headers=OWNER_HEADERS).status_code==409
    monkeypatch.setattr('app.api.workspace_packages.MAX_REQUEST_BYTES',32)
    assert client.post(root+'/edits',json=body,headers=OWNER_HEADERS).status_code==413


def test_rollback_then_retry(client,task_repository,monkeypatch):
    import app.services.package_edits as service
    original=service.create_package
    _,_,root,body=setup(client,task_repository)
    def fail(*args,**kwargs):
        original(*args,**kwargs)
        raise SQLAlchemyError('Synthetic failure')
    monkeypatch.setattr(service,'create_package',fail)
    assert client.post(root+'/edits',json=body,headers=OWNER_HEADERS).status_code==503
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Artifact))==1
    monkeypatch.setattr(service,'create_package',original)
    assert client.post(root+'/edits',json=body,headers=OWNER_HEADERS).status_code==200


@pytest.mark.parametrize('path',['test_app.py','tests.py','src/__tests__/logic.js','web/logic.spec.ts','test/conftest.py'])
def test_recognized_tests_are_preserved(path):
    assert protected_test(path)
    with pytest.raises(ValueError):assemble({path:'assert result'}, {path:'pass'}, [])


def test_layout_compatibility_is_not_expanded_by_multifile_storage():
    files={path:'nonempty source' for path in ['app.py','test_app.py','index.html','README.md']}
    assert execution_profile(files)=='python-web-v1'
    assert execution_profile(files|{'src/lib.py':'module'}) is None
    assert execution_profile(files|{'app.py':''}) is None
