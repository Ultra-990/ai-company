from dataclasses import dataclass

from app.brain.orchestrator import Orchestrator
from app.models.task import ApprovalStatus, TaskStatus
from app.services.executor import ExecutionResult
from app.services.tasks import TaskRepository


@dataclass
class SuccessfulExecutor:
    def execute(self, task):
        return ExecutionResult(
            success=True,
            reason=f"Wykonano zadanie {task.id}",
            result_content="Trwały rezultat testowego wykonania",
        )


@dataclass
class FailingExecutor:
    def execute(self, task):
        return ExecutionResult(
            success=False,
            reason="Wykonanie zakończyło się błędem",
        )


def make_repository(tmp_path):
    return TaskRepository(
        f"sqlite:///{tmp_path / 'executor.db'}",
    )


def prepare_task(repository):
    task = repository.create(title="Zadanie wykonawcze")
    repository.approve(task.id)
    return task


def test_orchestrator_executes_and_submits_task_for_review(tmp_path):
    repository = make_repository(tmp_path)
    try:
        task = prepare_task(repository)
        orchestrator = Orchestrator()

        result = orchestrator.execute_next_task(
            repository,
            SuccessfulExecutor(),
            worker_id="executor-1",
        )

        loaded = repository.get_required(task.id)
        assert result is not None
        assert result.success is True
        assert loaded.status is TaskStatus.IN_PROGRESS
        assert loaded.progress < 100
        assert repository.pending_review(task.id).result_content == "Trwały rezultat testowego wykonania"
    finally:
        repository.close()


def test_orchestrator_blocks_task_after_failed_execution(tmp_path):
    repository = make_repository(tmp_path)
    try:
        task = prepare_task(repository)
        orchestrator = Orchestrator()

        result = orchestrator.execute_next_task(
            repository,
            FailingExecutor(),
            worker_id="executor-1",
        )

        loaded = repository.get_required(task.id)
        assert result is not None
        assert result.success is False
        assert loaded.status is TaskStatus.BLOCKED
    finally:
        repository.close()


def test_orchestrator_returns_none_when_queue_is_empty(tmp_path):
    repository = make_repository(tmp_path)
    try:
        orchestrator = Orchestrator()

        result = orchestrator.execute_next_task(
            repository,
            SuccessfulExecutor(),
            worker_id="executor-1",
        )

        assert result is None
    finally:
        repository.close()

def test_orchestrator_blocks_task_when_executor_raises(
    task_repository,
    approved_task,
):
    from app.brain.orchestrator import Orchestrator
    from app.models.task import TaskStatus

    class ExplodingExecutor:
        def execute(self, task):
            raise RuntimeError("sekretny szczegół błędu wykonawcy")

    orchestrator = Orchestrator()

    result = orchestrator.execute_next_task(
        task_repository,
        ExplodingExecutor(),
        worker_id="orchestrator-worker",
    )

    assert result is not None
    assert result.success is False
    assert result.reason == (
        "Wykonanie zadania przerwano z powodu błędu wykonawcy."
    )

    refreshed_task = task_repository.get_required(approved_task.id)
    assert refreshed_task.status is TaskStatus.BLOCKED
