from pathlib import Path

import pytest

from app.models.task import (
    ApprovalStatus,
    TaskPriority,
    TaskStatus,
    TaskTransitionError,
)
from app.services.audit import AuditRepository

from app.services.tasks import (
    TaskNotFoundError,
    TaskRepository,
)


@pytest.fixture
def task_repository(tmp_path: Path):
    database_path = tmp_path / "tasks_test.sqlite3"
    repository = TaskRepository(
        f"sqlite:///{database_path}",
    )

    try:
        yield repository
    finally:
        repository.close()


def test_create_and_read_task(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(
        title="  Przygotuj raport  ",
        description="Raport tygodniowy",
        priority=TaskPriority.HIGH,
        assigned_agent=" analyst ",
    )

    loaded = task_repository.get(created.id)

    assert loaded is not None
    assert loaded.title == "Przygotuj raport"
    assert loaded.description == "Raport tygodniowy"
    assert loaded.status is TaskStatus.PENDING
    assert loaded.priority is TaskPriority.HIGH
    assert loaded.assigned_agent == "analyst"
    assert loaded.created_at is not None
    assert loaded.updated_at is not None


def test_empty_title_is_rejected(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(ValueError, match="nie może być pusty"):
        task_repository.create(title="   ")


def test_transition_is_persisted(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Wykonaj analizę")

    started = task_repository.transition(
        created.id,
        TaskStatus.IN_PROGRESS,
    )
    loaded = task_repository.get_required(created.id)

    assert started.status is TaskStatus.IN_PROGRESS
    assert loaded.status is TaskStatus.IN_PROGRESS


def test_invalid_transition_does_not_change_database(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Wykonaj analizę")

    with pytest.raises(TaskTransitionError):
        task_repository.transition(
            created.id,
            TaskStatus.COMPLETED,
        )

    loaded = task_repository.get_required(created.id)
    assert loaded.status is TaskStatus.PENDING


def test_missing_task_raises_domain_error(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(TaskNotFoundError):
        task_repository.transition(
            999999,
            TaskStatus.IN_PROGRESS,
        )


def test_list_recent_respects_limit(
    task_repository: TaskRepository,
) -> None:
    first = task_repository.create(title="Pierwsze zadanie")
    second = task_repository.create(title="Drugie zadanie")

    tasks = task_repository.list_recent(limit=1)

    assert len(tasks) == 1
    assert tasks[0].id == second.id
    assert tasks[0].id != first.id


@pytest.mark.parametrize("limit", [0, 101])
def test_list_recent_rejects_invalid_limit(
    task_repository: TaskRepository,
    limit: int,
) -> None:
    with pytest.raises(ValueError):
        task_repository.list_recent(limit=limit)


def test_list_recent_filters_tasks_by_status_priority_and_agent(
    task_repository: TaskRepository,
) -> None:
    matching = task_repository.create(
        title="Pasujące zadanie",
        priority=TaskPriority.HIGH,
        assigned_agent="analyst",
    )
    task_repository.transition(
        matching.id,
        TaskStatus.IN_PROGRESS,
    )

    task_repository.create(
        title="Inny status",
        priority=TaskPriority.HIGH,
        assigned_agent="analyst",
    )
    task_repository.create(
        title="Inny priorytet",
        priority=TaskPriority.LOW,
        assigned_agent="analyst",
    )
    task_repository.create(
        title="Inny agent",
        priority=TaskPriority.HIGH,
        assigned_agent="writer",
    )

    tasks = task_repository.list_recent(
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        assigned_agent=" analyst ",
    )

    assert [task.id for task in tasks] == [matching.id]


def test_assign_sets_and_removes_agent(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Przypisz zadanie")

    assigned = task_repository.assign(created.id, " analyst ")
    assert assigned.assigned_agent == "analyst"
    assert (
        task_repository.get_required(created.id).assigned_agent
        == "analyst"
    )

    unassigned = task_repository.assign(created.id, "   ")
    assert unassigned.assigned_agent is None
    assert task_repository.get_required(created.id).assigned_agent is None


def test_assign_rejects_agent_name_longer_than_100_characters(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Przypisz zadanie")

    with pytest.raises(ValueError, match="100 znaków"):
        task_repository.assign(created.id, "a" * 101)

    assert task_repository.get_required(created.id).assigned_agent is None


def test_assign_raises_error_for_missing_task(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(TaskNotFoundError):
        task_repository.assign(999999, "analyst")


def test_list_recent_rejects_blank_agent_filter(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(ValueError, match="nie może być pusty"):
        task_repository.list_recent(assigned_agent="   ")


def test_create_persists_queue_resource_and_risk_data(
    task_repository: TaskRepository,
) -> None:
    from app.models.task import ResourceClass, RiskLevel

    created = task_repository.create(
        title="Przetwarzanie wymagające CPU",
        resource_class=ResourceClass.CPU_HEAVY,
        risk_level=RiskLevel.HIGH,
    )
    loaded = task_repository.get_required(created.id)

    assert created.resource_class is ResourceClass.CPU_HEAVY
    assert created.risk_level is RiskLevel.HIGH
    assert created.queued_at is not None
    assert created.started_at is None
    assert created.completed_at is None

    assert loaded.resource_class is ResourceClass.CPU_HEAVY
    assert loaded.risk_level is RiskLevel.HIGH
    assert loaded.queued_at is not None
    assert loaded.started_at is None
    assert loaded.completed_at is None

def test_approve_sets_approval_status(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Zadanie do akceptacji")

    approved = task_repository.approve(created.id)
    loaded = task_repository.get_required(created.id)

    assert approved.approval_status is ApprovalStatus.APPROVED
    assert loaded.approval_status is ApprovalStatus.APPROVED


def test_reject_sets_approval_status(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Zadanie do odrzucenia")

    rejected = task_repository.reject(created.id)
    loaded = task_repository.get_required(created.id)

    assert rejected.approval_status is ApprovalStatus.REJECTED
    assert loaded.approval_status is ApprovalStatus.REJECTED


def test_approval_status_filter(
    task_repository: TaskRepository,
) -> None:
    approved = task_repository.create(title="Zaakceptowane")
    rejected = task_repository.create(title="Odrzucone")
    pending = task_repository.create(title="Oczekujące")

    task_repository.approve(approved.id)
    task_repository.reject(rejected.id)

    approved_tasks = task_repository.list_recent(
        approval_status=ApprovalStatus.APPROVED,
    )
    rejected_tasks = task_repository.list_recent(
        approval_status=ApprovalStatus.REJECTED,
    )
    pending_tasks = task_repository.list_recent(
        approval_status=ApprovalStatus.PENDING,
    )

    assert [task.id for task in approved_tasks] == [approved.id]
    assert [task.id for task in rejected_tasks] == [rejected.id]
    assert [task.id for task in pending_tasks] == [pending.id]

def test_approve_and_reject_record_audit_events(
    task_repository: TaskRepository,
) -> None:
    approved_task = task_repository.create(
        title="Zadanie do akceptacji",
    )
    rejected_task = task_repository.create(
        title="Zadanie do odrzucenia",
    )

    task_repository.approve(approved_task.id)
    task_repository.reject(rejected_task.id)

    audit_repository = AuditRepository(
        str(task_repository._engine.url),
    )

    try:
        events = audit_repository.list_recent(limit=20)
    finally:
        audit_repository.close()

    decisions = [event.decision for event in events]

    assert "approve" in decisions
    assert "reject" in decisions


def test_list_ready_returns_only_approved_pending_tasks(
    task_repository: TaskRepository,
) -> None:
    ready_first = task_repository.create(title="Gotowe pierwsze")
    ready_second = task_repository.create(title="Gotowe drugie")
    pending_approval = task_repository.create(
        title="Czeka na akceptację",
    )
    started = task_repository.create(title="Już rozpoczęte")

    task_repository.approve(ready_first.id)
    task_repository.approve(ready_second.id)
    task_repository.approve(started.id)
    task_repository.transition(started.id, TaskStatus.IN_PROGRESS)

    ready_tasks = task_repository.list_ready()

    assert [task.id for task in ready_tasks] == [
        ready_first.id,
        ready_second.id,
    ]
    assert pending_approval.id not in {task.id for task in ready_tasks}
    assert started.id not in {task.id for task in ready_tasks}


def test_list_ready_respects_limit(
    task_repository: TaskRepository,
) -> None:
    created_tasks = [
        task_repository.create(title=f"Gotowe {index}")
        for index in range(3)
    ]

    for task in created_tasks:
        task_repository.approve(task.id)

    ready_tasks = task_repository.list_ready(limit=2)

    assert [task.id for task in ready_tasks] == [
        created_tasks[0].id,
        created_tasks[1].id,
    ]


def test_list_ready_rejects_invalid_limit(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(ValueError, match="limit"):
        task_repository.list_ready(limit=0)

    with pytest.raises(ValueError, match="limit"):
        task_repository.list_ready(limit=101)


def test_claim_moves_approved_task_to_in_progress(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Zadanie do wykonania")
    task_repository.approve(created.id)

    claimed = task_repository.claim(
        created.id,
        worker_id="worker-1",
    )
    loaded = task_repository.get_required(created.id)

    assert claimed.status is TaskStatus.IN_PROGRESS
    assert claimed.started_at is not None
    assert loaded.status is TaskStatus.IN_PROGRESS
    assert loaded.started_at is not None


def test_claim_rejects_unapproved_task(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Niezaakceptowane zadanie")

    with pytest.raises(TaskTransitionError, match="nie jest gotowe"):
        task_repository.claim(created.id)

    loaded = task_repository.get_required(created.id)
    assert loaded.status is TaskStatus.PENDING
    assert loaded.started_at is None


def test_claim_cannot_be_repeated(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Jednorazowe pobranie")
    task_repository.approve(created.id)

    task_repository.claim(created.id)

    with pytest.raises(TaskTransitionError, match="zostało już przejęte"):
        task_repository.claim(created.id)


def test_claim_records_audit_event(
    task_repository: TaskRepository,
    tmp_path: Path,
) -> None:
    created = task_repository.create(title="Audytowane pobranie")
    task_repository.approve(created.id)

    task_repository.claim(created.id, worker_id="worker-7")

    audit_repository = AuditRepository(
        f"sqlite:///{tmp_path / 'tasks_test.sqlite3'}",
    )
    try:
        events = audit_repository.list_recent(limit=10)
    finally:
        audit_repository.close()

    claim_events = [
        event
        for event in events
        if event.event_type == "task_execution"
        and event.operation == "claim"
    ]

    assert len(claim_events) == 1
    assert claim_events[0].decision == "claim"
    assert claim_events[0].allowed is True
    assert "worker=worker-7" in claim_events[0].reason


def test_claim_rejects_missing_task(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(TaskNotFoundError):
        task_repository.claim(999999)
