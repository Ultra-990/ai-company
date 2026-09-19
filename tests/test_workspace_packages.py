import io
import json
from hashlib import sha256
from zipfile import ZipFile

import pytest
from sqlalchemy import select

from app.models.artifact import Artifact
from app.models.audit import AuditEvent
from app.services.workspace_packages import validate_files, MAX_FILE_BYTES, MAX_TOTAL_BYTES
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


@pytest.mark.parametrize("path", ["../secret", "/etc/passwd", "a/../x", "a//b", "a/", "a/.env", ".env", "C:/file", "a\\b", "a\x00b"])
def test_unsafe_paths_rejected(path):
    with pytest.raises(ValueError):
        validate_files({path: "content"})


@pytest.mark.parametrize("files", [{}, {"a": "x", "a/b": "y"}, {"A": "x", "a": "y"},
                                  {"a": "\x00"}, {"a": "\ud800"}, {"a": "ą" * MAX_FILE_BYTES}])
def test_invalid_contents_and_collisions(files):
    with pytest.raises(ValueError):
        validate_files(files)


def test_limits_and_utf8_hashes():
    with pytest.raises(ValueError):
        validate_files({f"f{i}": "" for i in range(101)})
    with pytest.raises(ValueError):
        validate_files({f"f{i}": "x" * MAX_FILE_BYTES for i in range(5)})
    accepted = validate_files({f"f{i}": "x" * MAX_FILE_BYTES for i in range(4)})
    assert sum(e["size_bytes"] for e in accepted) == MAX_TOTAL_BYTES
    entry = validate_files({"src/text.txt": "Zażółć"})[0]
    assert entry["size_bytes"] == len("Zażółć".encode())
    assert entry["sha256"] == sha256("Zażółć".encode()).hexdigest()


def save(client, task_id, **changes):
    data = {"purpose": "Test paczki", "files": {"index.html": "<h1>Test</h1>", "src/main.py": "raise RuntimeError('never execute')"}}
    return client.post(f"/api/tasks/{task_id}/workspace-packages", json=data | changes, headers=OWNER_HEADERS)


def test_roundtrip_immutable_audited_and_no_progress_change(client, task_repository):
    task = task_repository.create(title="Paczka strony")
    first = save(client, task.id)
    assert first.status_code == 201, first.text
    one = first.json()
    second = save(client, task.id).json()
    assert one["artifact_id"] != second["artifact_id"]
    assert one["checksum"] == second["checksum"]
    assert one["file_count"] == 2
    assert one["execution_status"] == "not_executed"
    assert one["review_status"] == "not_reviewed"
    assert all("content" not in e for e in one["files"])
    path = f'/api/tasks/{task.id}/workspace-packages/{one["artifact_id"]}'
    assert client.get(path, headers=OWNER_HEADERS).json() == one
    response = client.get(path + "/download", headers=OWNER_HEADERS)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in response.headers["content-disposition"]
    assert client.get(path + "/download", headers=OWNER_HEADERS).content == response.content
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == ["index.html", "src/main.py"]
        assert archive.read("src/main.py") == b"raise RuntimeError('never execute')"
        assert all(i.file_size == i.compress_size for i in archive.infolist())
        assert all(i.external_attr >> 16 == 0o100644 for i in archive.infolist())
    assert task_repository.get_required(task.id).status == task.status
    assert task_repository.get_required(task.id).progress == task.progress
    with task_repository._session_factory() as session:
        events = list(session.scalars(select(AuditEvent).where(AuditEvent.event_type == "workspace_package")))
        assert len(events) == 2
        assert one["checksum"] in events[0].reason


def test_auth_task_binding_and_no_overwrite(client, task_repository):
    task = task_repository.create(title="Pierwsze zadanie")
    other = task_repository.create(title="Drugie zadanie")
    base = f"/api/tasks/{task.id}/workspace-packages"
    assert client.post(base, json={}).status_code == 401
    assert client.post(base, json={}, headers=WORKER_HEADERS).status_code == 403
    artifact_id = save(client, task.id).json()["artifact_id"]
    path = base + f"/{artifact_id}"
    for suffix in ("", "/download"):
        assert client.get(path + suffix).status_code == 401
        assert client.get(path + suffix, headers=WORKER_HEADERS).status_code == 403
        assert client.get(f"/api/tasks/{other.id}/workspace-packages/{artifact_id}" + suffix, headers=OWNER_HEADERS).status_code == 404
    assert client.patch(path, json={}, headers=OWNER_HEADERS).status_code == 405
    assert save(client, 999999).status_code == 404


def test_bad_requests_never_write_artifacts(client, task_repository, monkeypatch):
    task = task_repository.create(title="Walidacja")
    for data in ({"purpose": " "}, {"files": {"../bad": "x"}}, {"files": {"a": 123}}, {"unexpected": "x"}):
        assert save(client, task.id, **data).status_code == 422
    monkeypatch.setattr("app.api.workspace_packages.MAX_REQUEST_BYTES", 32)
    assert save(client, task.id).status_code == 413
    with task_repository._session_factory() as session:
        assert session.scalar(select(Artifact).where(Artifact.task_id == task.id)) is None


@pytest.mark.parametrize("corruption", ["checksum", "file_hash", "task_id", "duplicate"])
def test_corrupted_package_cannot_be_downloaded(client, task_repository, corruption):
    task = task_repository.create(title="Integralność")
    saved = save(client, task.id).json()
    with task_repository._session_factory() as session:
        artifact = session.get(Artifact, saved["artifact_id"])
        if corruption == "checksum":
            artifact.content += " "
        else:
            payload = json.loads(artifact.content)
            if corruption == "file_hash":
                payload["files"][0]["sha256"] = "0" * 64
            elif corruption == "task_id":
                payload["task_id"] += 1
            else:
                payload["files"].append(payload["files"][0])
            artifact.content = json.dumps(payload)
            artifact.checksum = sha256(artifact.content.encode()).hexdigest()
        session.commit()
    path = f'/api/tasks/{task.id}/workspace-packages/{saved["artifact_id"]}'
    assert client.get(path, headers=OWNER_HEADERS).status_code == 409
    assert client.get(path + "/download", headers=OWNER_HEADERS).status_code == 409


def test_openapi_describes_bounded_body(client):
    spec = client.get("/openapi.json").json()
    schema = spec["paths"]["/api/tasks/{task_id}/workspace-packages"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert set(schema["required"]) == {"purpose", "files"}


def test_list_packages_is_private_paginated_and_bound_to_task(client, task_repository):
    task = task_repository.create(title="Historia wersji")
    other = task_repository.create(title="Inny projekt")
    path = f"/api/tasks/{task.id}/workspace-packages"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=WORKER_HEADERS).status_code == 403
    assert client.get(path, headers=OWNER_HEADERS).json() == {"packages": [], "next_cursor": None}
    ids = [save(client, task.id).json()["artifact_id"] for _ in range(3)]
    save(client, other.id)
    response = client.get(path + "?limit=2", headers=OWNER_HEADERS)
    assert response.headers["cache-control"] == "no-store"
    first = response.json()
    assert [p["artifact_id"] for p in first["packages"]] == ids[:0:-1]
    assert first["next_cursor"] == ids[1]
    last = client.get(path + f'?limit=2&before={first["next_cursor"]}', headers=OWNER_HEADERS).json()
    assert [p["artifact_id"] for p in last["packages"]] == ids[:1]
    assert last["next_cursor"] is None
    assert all("content" not in file for p in first["packages"] for file in p["files"])
    assert client.get(path + "?limit=51", headers=OWNER_HEADERS).status_code == 422
    assert client.get("/api/tasks/999999/workspace-packages", headers=OWNER_HEADERS).status_code == 404


def test_os_exposes_delivery_dialog_without_embedded_credentials(client):
    response = client.get("/os/review")
    assert response.status_code == 200
    assert 'id="open-delivery-center"' in response.text
    assert 'id="delivery-center"' in response.text
    assert "delivery-center.js" in response.text
    assert "test-owner-token" not in response.text
