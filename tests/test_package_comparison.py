"""Read-only comparisons in isolated SQLite; no model/runner needed."""
from hashlib import sha256

import pytest
from sqlalchemy import func, select

from app.models.artifact import Artifact
from app.models.audit import AuditEvent
from app.services.workspace_packages import create_package
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


@pytest.fixture
def versions(task_repository):
    task = task_repository.create(title='Comparison')
    with task_repository._session_factory() as session:
        old = create_package(session, task.id, {'app.py': 'print(1)\n', 'gone.txt': 'old',
                                              'same.txt': 'unchanged'}, 'Before')
        new = create_package(session, task.id, {'app.py': 'print(2)\n', 'new.txt': '<script>inert</script>',
                                              'same.txt': 'unchanged'}, 'After')
        return task.id, old.id, new.id


def url(versions):
    task, old, new = versions
    return f'/api/tasks/{task}/workspace-packages/{new}/comparison?base_id={old}'


def test_inventory_is_read_only_exact_and_does_not_expose_sources(client, versions, task_repository):
    with task_repository._session_factory() as session:
        before = [session.scalar(select(func.count()).select_from(m)) for m in (Artifact, AuditEvent)]
    task = task_repository.get_required(versions[0])
    state = task.status, task.progress
    response = client.get(url(versions), headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    data = response.json()
    assert data['counts'] == dict(added=1, removed=1, modified=1, unchanged=1)
    assert not data['executed'] and not data['accepted']
    assert 'print(' not in response.text and '<script>' not in response.text
    assert data['files'][0]['before']['sha256'] == sha256(b'print(1)\n').hexdigest()
    assert client.get(url(versions), headers=OWNER_HEADERS).json() == data
    with task_repository._session_factory() as session:
        assert before == [session.scalar(select(func.count()).select_from(m)) for m in (Artifact, AuditEvent)]
    task = task_repository.get_required(versions[0])
    assert (task.status, task.progress) == state


@pytest.mark.parametrize('path, fragments', [('app.py', ['-print(1)', '+print(2)']),
    ('new.txt', ['+<script>inert</script>']), ('gone.txt', ['-old']), ('same.txt', [])])
def test_detail_handles_modified_added_removed_unchanged(client, versions, path, fragments):
    response = client.get(url(versions) + '&path=' + path, headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    detail = response.json()['detail']
    assert detail['available']
    for fragment in fragments:
        assert fragment in detail['diff']
    if not fragments:
        assert detail['diff'] == ''


@pytest.mark.parametrize('headers, status', [({}, 401), (WORKER_HEADERS, 403)])
def test_owner_only(client, versions, headers, status):
    assert client.get(url(versions), headers=headers).status_code == status


def test_task_binding_and_invalid_inputs(client, versions, task_repository):
    task, old, new = versions
    other = task_repository.create(title='Other task')
    for path in (url((other.id, old, new)), url((task, 999999, new)),
                 url(versions) + '&path=../../etc/passwd'):
        assert client.get(path, headers=OWNER_HEADERS).status_code == 404
    assert client.get(url((task, 0, new)), headers=OWNER_HEADERS).status_code == 422
    assert client.get(url(versions) + '&path=' + 'x' * 201, headers=OWNER_HEADERS).status_code == 422


@pytest.mark.parametrize('index', [1, 2])
def test_both_manifests_are_verified(client, versions, task_repository, index):
    with task_repository._session_factory() as session:
        session.get(Artifact, versions[index]).content = 'damaged'
        session.commit()
    assert client.get(url(versions), headers=OWNER_HEADERS).status_code == 409


@pytest.mark.parametrize('text', ['x' * 16385, 'x\n' * 301])
def test_large_input_skips_sequence_matcher(client, versions, task_repository, monkeypatch, text):
    with task_repository._session_factory() as session:
        large = create_package(session, versions[0], {'app.py': text}, 'Large')
        ids = versions[0], versions[1], large.id
    def forbidden(*args, **kwargs):
        raise AssertionError('Large input must not run diff')
    monkeypatch.setattr('app.services.package_comparison.unified_diff', forbidden)
    detail = client.get(url(ids) + '&path=app.py', headers=OWNER_HEADERS).json()['detail']
    assert not detail['available'] and detail['diff'] is None and detail['reason']


def test_newline_changes_and_same_version(client, versions, task_repository):
    with task_repository._session_factory() as session:
        crlf = create_package(session, versions[0], {'app.py': 'print(1)\r\n'}, 'CRLF')
        ids = versions[0], versions[1], crlf.id
    data = client.get(url(ids) + '&path=app.py', headers=OWNER_HEADERS).json()
    assert data['files'][0]['status'] == 'modified'
    assert data['detail']['line_endings_or_final_newline_only']
    data = client.get(url((versions[0], versions[2], versions[2])), headers=OWNER_HEADERS).json()
    assert data['counts'] == dict(unchanged=3, added=0, removed=0, modified=0)
