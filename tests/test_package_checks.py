import json
from hashlib import sha256

import pytest
from sqlalchemy import select, func

from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.models.task import TaskAttempt
from app.services.package_checks import inspect_sources, CHECK_NAME
from app.services.workspace_packages import validate_files, canonical_json
from app.services.work_orders import website_starter
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS

GOOD = '<!doctype html><html lang="pl"><head><title>Test</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main id="main"><h1>Test</h1></main></body></html>'


def inspect(files):
    return inspect_sources({'files':validate_files(files)})


def save(client, task_repository, files=None):
    task = task_repository.create(title='Kontrola źródeł')
    response=client.post(f'/api/tasks/{task.id}/workspace-packages',headers=OWNER_HEADERS,
                         json={'purpose':'Kontrola bez wykonania','files':files or {'index.html':GOOD}})
    assert response.status_code==201, response.text
    return task, response.json()['artifact_id']


def run(client, task_id, package_id, headers=OWNER_HEADERS):
    return client.post(f'/api/tasks/{task_id}/workspace-packages/{package_id}/static-check',headers=headers)


def test_starter_passes_only_static_profile():
    files=website_starter(dict(title='Pracownia',goal='Oferta pracowni',audience='Klienci',constraints='Brak sieci',acceptance_criteria=['Mobile']))
    report=inspect(files)
    assert report['outcome']=='checks_passed'
    assert report['counts']['failed']==0
    assert report['counts']['warning']==0
    assert report['code_executed'] is False and report['product_accepted'] is False
    assert report['not_checked'] and report['inspected_documents']==2


@pytest.mark.parametrize('html,code', [
    ('<h1>Fragment</h1>','html.title'),
    (GOOD.replace('lang="pl"',''),'html.lang'),
    (GOOD.replace('id="main"','id="same"')+'<p id="same">x</p>','html.ids'),
    (GOOD+'<img src="missing.png">','html.alt'),
    (GOOD+'<link rel="stylesheet" href="no.css">','link.missing'),
    (GOOD+'<a href="#absent">Go</a>','link.fragment'),
    (GOOD+'<a href="../../../private">Go</a>','link.invalid'),
    (GOOD+'<script src="javascript:alert(1)"></script>','link.external'),
    (GOOD+'<a href="file:///etc/passwd">Go</a>','link.external'),
])
def test_detects_problems_without_executing(html,code):
    report=inspect({'index.html':html})
    assert report['outcome']=='issues_found'
    assert any(c['code']==code and c['status']=='failed' for c in report['checks'])


def test_relative_root_encoded_and_cross_document_links():
    html=GOOD+'<a href="../about.html#target">Go</a><a href="/%61bout.html?x=1#target">Go</a><a href="../">Home</a>'
    report=inspect({'pages/index.html':html,'about.html':GOOD+'<p id="target">x</p>','index.html':GOOD})
    assert report['counts']['failed']==0
    assert len([c for c in report['checks'] if c['code']=='link.local'])==3


def test_external_urls_and_active_content_not_reported_as_tested():
    report=inspect({'index.html':GOOD+'<script>alert("never")</script><a href="https://example.invalid/?token=secret">x</a>'})
    assert report['counts']['warning']==2
    assert 'secret' not in json.dumps(report)
    assert not report['code_executed']


@pytest.mark.parametrize('source',['{oops}', 'NaN', 'Infinity', '['*2000+'0'+']'*2000], ids=['syntax','nan','infinity','depth'])
def test_invalid_or_excessively_nested_json(source):
    report=inspect({'settings.json':source})
    assert report['outcome']=='issues_found'
    assert any(c['code']=='json.syntax' and c['status']=='failed' for c in report['checks'])


def test_unsupported_files_and_limits_never_get_clean_result():
    assert inspect({'main.py':'raise RuntimeError("never run")'})['outcome']=='incomplete'
    report=inspect({'index.html':GOOD+'<base href="https://example.invalid/"><a href="foo">x</a>'})
    assert report['outcome']=='incomplete'
    report=inspect({'index.html':GOOD+'<a href="#main">x</a>'*600})
    assert len(report['checks'])==400 and report['analysis_incomplete']
    assert report['outcome']=='incomplete'
    report=inspect({'index.html':GOOD+'<i></i>'*10001})
    assert report['outcome']=='incomplete'


def test_persisted_report_bound_to_version_no_task_progress(client,task_repository,tmp_path):
    target=tmp_path/'must-not-exist'
    task,package=save(client,task_repository,{'index.html':GOOD,'evil.py':f'open({str(target)!r}, "w").write("executed")'})
    before=task_repository.get_required(task.id)
    response=run(client,task.id,package)
    assert response.status_code==201, response.text
    data=response.json()
    assert data['package_id']==package and data['task_id']==task.id
    assert data['report_checksum'] and data['source_checksum']
    path=f"/api/tasks/{task.id}/static-checks/{data['report_id']}"
    fetched=client.get(path,headers=OWNER_HEADERS)
    assert fetched.status_code==200 and fetched.json()==data
    assert fetched.headers['cache-control']=='no-store'
    after=task_repository.get_required(task.id)
    assert (after.status,after.progress,after.approval_status)==(before.status,before.progress,before.approval_status)
    assert not target.exists()
    with task_repository._session_factory() as session:
        report=session.get(Artifact,data['report_id'])
        assert report.artifact_type==ArtifactType.TEST_RESULT
        assert report.name==CHECK_NAME
        assert session.scalar(select(func.count()).select_from(TaskAttempt))==0
        assert len(list(session.scalars(select(AuditEvent).where(AuditEvent.event_type=='package_static_check'))))==1
    second=run(client,task.id,package).json()
    assert second['report_id']!=data['report_id'] and second['report_checksum']==data['report_checksum']


def test_auth_and_cross_task_binding(client,task_repository):
    task,package=save(client,task_repository)
    other=task_repository.create(title='Inne')
    data=run(client,task.id,package).json()
    for headers,status in (({},401),(WORKER_HEADERS,403)):
        assert run(client,task.id,package,headers).status_code==status
        assert client.get(f"/api/tasks/{task.id}/static-checks/{data['report_id']}",headers=headers).status_code==status
    assert run(client,other.id,package).status_code==404
    assert client.get(f"/api/tasks/{other.id}/static-checks/{data['report_id']}",headers=OWNER_HEADERS).status_code==404
    assert run(client,task.id,999999).status_code==404
    assert client.get(f'/api/tasks/{task.id}/static-checks/99999',headers=OWNER_HEADERS).status_code==404


@pytest.mark.parametrize('kind',['report','source','binding'])
def test_corruption_is_rejected(client,task_repository,kind):
    task,package=save(client,task_repository)
    data=run(client,task.id,package).json()
    with task_repository._session_factory() as s:
        artifact=s.get(Artifact,package if kind=='source' else data['report_id'])
        if kind=='binding':
            payload=json.loads(artifact.content);payload['source_checksum']='0'*64
            artifact.content=canonical_json(payload);artifact.checksum=sha256(artifact.content.encode()).hexdigest()
        else:
            artifact.content+=' '
        s.commit()
    assert client.get(f"/api/tasks/{task.id}/static-checks/{data['report_id']}",headers=OWNER_HEADERS).status_code==409
    if kind=='source':
        assert run(client,task.id,package).status_code==409
        with task_repository._session_factory() as s:
            assert s.scalar(select(func.count()).select_from(Artifact).where(Artifact.name==CHECK_NAME))==1
