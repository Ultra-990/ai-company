import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from app.models.artifact import Artifact
from app.models.audit import AuditEvent
from app.models.task import TaskAttempt, TaskStatus, TaskTransitionError
from app.models.project import Project
from app.models.organization import OrganizationUnit
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


def submitted(repository):
    task = repository.create(title="Aplikacja do odbioru")
    repository.approve(task.id)
    repository.claim(task.id, worker_id="builder")
    repository.submit_result(task.id, result_content="Rezultat v1", reason="Przekazanie")
    return task.id, repository.pending_review(task.id)


def decision(attempt, **changes):
    data = dict(attempt_id=attempt.id, result_checksum=attempt.result_checksum,
                accepted=True, reason="Sprawdzono kryteria odbioru",
                evidence=["Raport testów i ręczna kontrola scenariusza użytkownika"])
    return data | changes


def test_submission_persists_without_completing_and_cannot_be_bypassed(task_repository):
    task_id, attempt = submitted(task_repository)
    task = task_repository.get_required(task_id)
    assert task.status is TaskStatus.IN_PROGRESS
    assert task.progress < 100
    assert task.completed_at is None
    assert attempt.status == "awaiting_review"
    assert attempt.result_content == "Rezultat v1"
    assert not task_repository.list_ready()
    with pytest.raises(TaskTransitionError, match="odbiór"):
        task_repository.complete(task_id, result_content="Inny wynik")
    with pytest.raises(TaskTransitionError, match="odbiór"):
        task_repository.transition(task_id, TaskStatus.COMPLETED)
    with pytest.raises(TaskTransitionError, match="odbiór"):
        task_repository.submit_result(task_id, result_content="Nadpisanie", reason="Ponowienie")
    assert task_repository.pending_review(task_id).result_content == "Rezultat v1"


def test_owner_acceptance_is_authenticated_versioned_and_audited(client, task_repository):
    task_id, attempt = submitted(task_repository)
    path = f"/api/tasks/{task_id}/review"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=WORKER_HEADERS).status_code == 403
    data = client.get(path, headers=OWNER_HEADERS).json()
    assert data["id"] == attempt.id
    assert data["result_content"] == "Rezultat v1"
    assert client.post(path, json=decision(attempt), headers=WORKER_HEADERS).status_code == 403
    assert client.post(path, json=decision(attempt, result_checksum="0" * 64), headers=OWNER_HEADERS).status_code == 409
    response = client.post(path, json=decision(attempt), headers=OWNER_HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["progress"] == 100
    assert client.post(path, json=decision(attempt), headers=OWNER_HEADERS).status_code == 409
    with task_repository._session_factory() as session:
        record = session.scalar(select(Artifact).where(Artifact.task_attempt_id == attempt.id))
        assert record.created_by == "owner"
        assert json.loads(record.content)["result_checksum"] == attempt.result_checksum
        assert json.loads(record.content)["review_method"] == "owner_attestation"
        audit = session.scalar(select(AuditEvent).where(AuditEvent.event_type == "task_acceptance"))
        assert audit.decision == "accepted"


@pytest.mark.parametrize("evidence", [[], [""], ["   "], ["ok", " "]])
def test_review_requires_actual_evidence_entries(task_repository, evidence):
    task_id, attempt = submitted(task_repository)
    with pytest.raises(ValueError):
        task_repository.review_result(task_id, **decision(attempt, evidence=evidence))
    assert task_repository.pending_review(task_id).id == attempt.id


def test_rejection_retry_and_second_attempt_preserve_history(client, task_repository):
    task_id, first = submitted(task_repository)
    path = f"/api/tasks/{task_id}/review"
    rejected = client.post(path, json=decision(first, accepted=False, reason="Testy wykazały błąd"), headers=OWNER_HEADERS)
    assert rejected.json()["status"] == "blocked"
    assert client.post(path + "/retry", headers=WORKER_HEADERS).status_code == 403
    assert client.post(path + "/retry", headers=OWNER_HEADERS).json()["status"] == "pending"
    task_repository.claim(task_id, worker_id="builder-2")
    task_repository.submit_result(task_id, result_content="Poprawiony rezultat v2", reason="Poprawki")
    second = task_repository.pending_review(task_id)
    assert second.id != first.id
    assert client.post(path, json=decision(first), headers=OWNER_HEADERS).status_code == 409
    assert client.post(path, json=decision(second), headers=OWNER_HEADERS).status_code == 200
    with task_repository._session_factory() as session:
        attempts = list(session.scalars(select(TaskAttempt).where(TaskAttempt.task_id == task_id).order_by(TaskAttempt.id)))
        assert [a.verification_status for a in attempts] == ["rejected", "accepted"]
        assert len(list(session.scalars(select(Artifact).where(Artifact.task_id == task_id)))) == 2


def test_tampered_result_is_not_accepted(task_repository):
    task_id, attempt = submitted(task_repository)
    with task_repository._session_factory() as session:
        session.get(TaskAttempt, attempt.id).result_content = "Zmieniona treść"
        session.commit()
    with pytest.raises(TaskTransitionError, match="integralność"):
        task_repository.review_result(task_id, **decision(attempt))


def test_parallel_review_only_records_one_decision(task_repository, monkeypatch):
    task_id, attempt = submitted(task_repository)
    monkeypatch.setattr(task_repository, "_refresh_documentation", lambda: None)
    def review(_):
        try:
            task_repository.review_result(task_id, **decision(attempt))
            return "accepted"
        except TaskTransitionError:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(review, range(2))) == ["accepted", "conflict"]
    with task_repository._session_factory() as session:
        assert len(list(session.scalars(select(Artifact).where(Artifact.task_id == task_id)))) == 1


def test_review_count_is_visible_in_organization_overview(client, task_repository):
    submitted(task_repository)
    assert client.get("/api/organization-os/overview").json()["awaiting_review_tasks"] == 1


def test_next_move_routes_to_review_and_department_shows_pending_count(client, task_repository):
    task_id, attempt = submitted(task_repository)
    with task_repository._session_factory() as session:
        unit = session.scalar(select(OrganizationUnit).where(OrganizationUnit.os_key == "platform.organization-os"))
        project = Project(name="Odbiór produktu", business_goal="Działający produkt", organization_unit_id=unit.id)
        session.add(project)
        session.flush()
        session.get(TaskAttempt, attempt.id).task.project_id = project.id
        session.commit()
    move = client.get("/api/organization-os/next-move").json()
    assert move["type"] == "review"
    assert move["target"]["attempt_id"] == attempt.id
    assert move["target"]["task_id"] == task_id
    tree = client.get("/api/organization-os/tree").json()["nodes"][0]
    platform = next(node for node in tree["children"] if node["key"] == "platform")
    assert platform["awaiting_review_count"] == 1
