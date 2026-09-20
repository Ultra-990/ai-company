from pathlib import Path
import os
import stat
from unittest.mock import patch

import pytest
from sqlalchemy import select, func

from app.main import app
from app.api.workspace_exports import get_workspace_storage
from app.models.artifact import Artifact
from app.models.audit import AuditEvent
from app.services.workspace_exports import WorkspaceStorage, EXPORT_NAME, MARKER
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


@pytest.fixture
def storage(tmp_path):
    root=tmp_path/'storage';root.mkdir(mode=0o700)
    (root/'packages').mkdir(mode=0o700)
    instance=WorkspaceStorage(root, tmp_path, min_free_bytes=0)
    app.dependency_overrides[get_workspace_storage]=lambda:instance
    yield instance
    app.dependency_overrides.pop(get_workspace_storage,None)


def package(client, repo, files=None):
    task=repo.create(title='Eksport Linux')
    data=client.post(f'/api/tasks/{task.id}/workspace-packages',json={'purpose':'Wersja robocza','files':files or {'index.html':'<h1>Test</h1>','src/app.py':'raise RuntimeError("do not run")'}},headers=OWNER_HEADERS).json()
    return task,data


def path(task,pkg):return f"/api/tasks/{task.id}/workspace-packages/{pkg['artifact_id']}/disk-export"


def test_media_export_preserves_png_bytes_and_detects_changed_image(client,task_repository,storage):
    import base64
    from tests.test_media_packages import payload
    task=task_repository.create(title='Synthetic image disk export')
    request=payload()
    response=client.post(f'/api/tasks/{task.id}/workspace-media-packages',json=request,headers=OWNER_HEADERS)
    assert response.status_code==201,response.text
    pkg=response.json()
    exported=client.post(path(task,pkg),headers=OWNER_HEADERS)
    assert exported.status_code==200,exported.text
    data=exported.json();image=Path(data['directory'])/'static/image.png'
    assert image.read_bytes()==base64.b64decode(request['images']['static/image.png'])
    retry=client.post(path(task,pkg),headers=OWNER_HEADERS).json()
    assert retry['verified'] and not retry['created'] and retry['receipt_id']==data['receipt_id']
    image.write_bytes(b'changed image')
    assert client.get(path(task,pkg),headers=OWNER_HEADERS).status_code==409
    assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==409
    assert image.read_bytes()==b'changed image'


def test_export_bytes_private_modes_no_overwrite_and_receipt(client,task_repository,storage):
    task,pkg=package(client,task_repository)
    response=client.post(path(task,pkg),headers=OWNER_HEADERS)
    assert response.status_code==200,response.text
    data=response.json();folder=Path(data['directory'])
    assert folder.is_relative_to(storage.root/'packages')
    assert data['created'] and data['verified'] and not data['code_executed']
    assert (folder/'index.html').read_text()=='<h1>Test</h1>'
    assert (folder/'src/app.py').read_text()=='raise RuntimeError("do not run")'
    assert stat.S_IMODE(folder.stat().st_mode)==0o700
    assert stat.S_IMODE((folder/'src/app.py').stat().st_mode)==0o600
    ino=(folder/'index.html').stat().st_ino
    replay=client.post(path(task,pkg),headers=OWNER_HEADERS).json()
    assert not replay['created'] and replay['receipt_id']==data['receipt_id']
    assert (folder/'index.html').stat().st_ino==ino
    assert client.get(path(task,pkg),headers=OWNER_HEADERS).json()['verified']
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Artifact).where(Artifact.name==EXPORT_NAME))==1
        assert s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.event_type=='workspace_export'))==1
    after=task_repository.get_required(task.id)
    assert (after.status,after.progress)==(task.status,task.progress)
    assert response.headers['cache-control']=='no-store'


def test_owner_only_and_task_binding(client,task_repository,storage):
    task,pkg=package(client,task_repository)
    for headers,status in (({},401),(WORKER_HEADERS,403)):
        assert client.post(path(task,pkg),headers=headers).status_code==status
        assert client.get(path(task,pkg),headers=headers).status_code==status
        assert client.get('/api/workspace-storage',headers=headers).status_code==status
    assert client.get(path(task,pkg),headers=OWNER_HEADERS).status_code==404
    other=task_repository.create(title='Inne zadanie')
    assert client.post(path(other,pkg),headers=OWNER_HEADERS).status_code==404
    assert list((storage.root/'packages').iterdir())==[]


@pytest.mark.parametrize('change',['file','extra','marker','symlink','hardlink','fifo'])
def test_changed_export_is_never_overwritten(client,task_repository,storage,tmp_path,change):
    task,pkg=package(client,task_repository)
    folder=Path(client.post(path(task,pkg),headers=OWNER_HEADERS).json()['directory'])
    if change=='file': (folder/'index.html').write_text('changed')
    if change=='extra': (folder/'extra.txt').write_text('added')
    if change=='marker': (folder/MARKER).unlink()
    if change in {'symlink','hardlink','fifo'}:
        victim=tmp_path/'untouched';victim.write_text('private')
        (folder/'index.html').unlink()
        if change=='symlink': (folder/'index.html').symlink_to(victim)
        elif change=='hardlink': os.link(victim,folder/'index.html')
        else: os.mkfifo(folder/'index.html')
    for method in (client.get,client.post):
        response=method(path(task,pkg),headers=OWNER_HEADERS)
        assert response.status_code==409,response.text
    if change in {'symlink','hardlink','fifo'}:assert victim.read_text()=='private'
    if change=='file': assert (folder/'index.html').read_text()=='changed'


def test_root_symlink_permissions_device_and_capacity(client,task_repository,storage,tmp_path,monkeypatch):
    task,pkg=package(client,task_repository)
    with patch.object(storage,'_available',return_value=0):
        assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==503
    assert list((storage.root/'packages').iterdir())==[]
    (storage.root/'packages').chmod(0o755)
    assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==503
    (storage.root/'packages').chmod(0o700)
    original=storage.root
    alias=tmp_path/'alias';alias.symlink_to(original,target_is_directory=True)
    storage.root=alias
    assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==503
    storage.root=original
    # A reference on a different filesystem must fail without mounting anything.
    if os.stat('/proc').st_dev != original.stat().st_dev:
        storage.device_reference=Path('/proc')
        assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==503
        storage.device_reference=tmp_path
    monkeypatch.setattr('app.services.workspace_exports.MAX_EXPORTS',0)
    assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==503
    assert list((storage.root/'packages').iterdir())==[]


def test_partial_write_is_preserved_and_not_claimed_as_complete(client,task_repository,storage):
    task,pkg=package(client,task_repository)
    real=storage._write
    def fail(fd,name,raw):
        if name==MARKER:raise OSError('simulated interruption')
        real(fd,name,raw)
    with patch.object(storage,'_write',side_effect=fail):
        assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==409
    folders=list((storage.root/'packages').iterdir())
    assert len(folders)==1 and not (folders[0]/MARKER).exists()
    assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==409
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Artifact).where(Artifact.name==EXPORT_NAME))==0


def test_storage_status_and_source_corruption(client,task_repository,storage):
    response=client.get('/api/workspace-storage',headers=OWNER_HEADERS)
    assert response.status_code==200
    assert response.json()['root']==str(storage.root/'packages')
    assert not response.json()['hard_quota']
    task,pkg=package(client,task_repository)
    with task_repository._session_factory() as s:
        a=s.get(Artifact,pkg['artifact_id']);a.content+=' ';s.commit()
    assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==409
    assert list((storage.root/'packages').iterdir())==[]


def test_export_folder_symlink_cannot_redirect_to_other_disk(client,task_repository,storage,tmp_path):
    task,pkg=package(client,task_repository)
    outside=tmp_path/'other-disk';outside.mkdir()
    folder=storage.root/'packages'/f"task-{task.id}-package-{pkg['artifact_id']}-{pkg['checksum']}"
    folder.symlink_to(outside,target_is_directory=True)
    assert client.post(path(task,pkg),headers=OWNER_HEADERS).status_code==409
    assert list(outside.iterdir())==[]


def test_database_failure_can_recover_receipt_without_overwriting_files(client,task_repository,storage,monkeypatch):
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session
    from app.services.workspace_exports import export_package
    task,pkg=package(client,task_repository)
    with task_repository._session_factory() as session:
        with patch.object(session,'commit',side_effect=OperationalError('commit',{},RuntimeError('test failure'))):
            with pytest.raises(OperationalError):export_package(session,storage,task.id,pkg['artifact_id'])
        session.rollback()
    folders=list((storage.root/'packages').iterdir())
    assert len(folders)==1
    inode=(folders[0]/'index.html').stat().st_ino
    retried=client.post(path(task,pkg),headers=OWNER_HEADERS)
    assert retried.status_code==200,retried.text
    assert not retried.json()['created'] and retried.json()['receipt_id']
    assert (folders[0]/'index.html').stat().st_ino==inode
