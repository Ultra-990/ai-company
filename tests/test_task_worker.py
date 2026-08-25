from pathlib import Path

import pytest

from app.models.task import TaskStatus
from app.services.tasks import TaskRepository
from app.services.worker import TaskWorker


@pytest.fixture
def task_repository(tmp_path: Path):
    repository = TaskRepository(
        f"sqlite:///{tmp_path / 'tasks_test.sqlite3'}",
    )

    try:
        yield repository
    finally:
        repository.close()


def test_worker_claims_oldest_ready_task(
    task_repository: TaskRepository,
) -> None:
    first = task_repository.create(title="Pierwsze")
    second = task_repository.create(title="Drugie")

    task_repository.approve(first.id)
    task_repository.approve(second.id)

    worker = TaskWorker(task_repository, worker_id="worker-1")

    claimed = worker.claim_next()

    assert claimed is not None
    assert claimed.id == first.id
    assert claimed.status is TaskStatus.IN_PROGRESS
    assert task_repository.get_required(first.id).status is TaskStatus.IN_PROGRESS
    assert task_repository.get_required(second.id).status is TaskStatus.PENDING


def test_worker_returns_none_when_queue_is_empty(
    task_repository: TaskRepository,
) -> None:
    worker = TaskWorker(task_repository, worker_id="worker-1")

    assert worker.claim_next() is None


def test_worker_does_not_claim_unapproved_task(
    task_repository: TaskRepository,
) -> None:
    task_repository.create(title="Niezaakceptowane")

    worker = TaskWorker(task_repository, worker_id="worker-1")

    assert worker.claim_next() is None


def test_worker_validates_worker_id(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(ValueError, match="nie może być pusty"):
        TaskWorker(task_repository, worker_id="   ")

    with pytest.raises(ValueError, match="100 znaków"):
        TaskWorker(task_repository, worker_id="x" * 101)
