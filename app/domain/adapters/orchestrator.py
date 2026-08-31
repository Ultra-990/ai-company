from __future__ import annotations
from app.domain.contracts import ContractError
from app.domain.contracts import ContractError
from app.domain.contracts import ContractError

from typing import Any

from app.domain.contracts import TaskContract, TaskStatus

from app.domain.contracts import Department, MemoryRecord
from app.domain.repositories import (
    InMemoryMemoryRepository,
    MemoryRepository,
)


class DomainRegistry:
    """Lekki rejestr kontraktów domenowych używany przez Orchestrator."""

    def __init__(
        self,
        memory_repository: MemoryRepository | None = None,
    ) -> None:
        self._tasks: dict[str, TaskContract] = {}
        self._departments: dict[str, Department] = {}
        self._memory_repository = (
            memory_repository
            if memory_repository is not None
            else InMemoryMemoryRepository()
        )

    @property
    def memory_repository(self) -> MemoryRepository:
        return self._memory_repository

    def register_department(self, department: Department) -> Department:
        if department.id in self._departments:
            raise ValueError(
                f"Department '{department.id}' is already registered"
            )

        self._departments[department.id] = department
        return department

    def get_department(self, department_id: str) -> Department | None:
        return self._departments.get(department_id)

    def list_departments(self) -> list[Department]:
        return list(self._departments.values())

    def register_memory(self, memory: MemoryRecord) -> MemoryRecord:
        if self.get_memory(memory.id) is not None:
            raise ValueError(
                f"Memory '{memory.id}' is already registered"
            )

        return self._memory_repository.save(memory)

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        return self._memory_repository.get(memory_id)

    def list_memories(self) -> list[MemoryRecord]:
        return list(self._memory_repository.list())

    def delete_memory(self, memory_id: str) -> bool:
        return self._memory_repository.delete(memory_id)

    def register_task(self, task: TaskContract) -> None:
        if task.id in self._tasks:
            raise ContractError(
                f"Task '{task.id}' is already registered"
            )
        self._tasks[task.id] = task

    def get_task(self, task_id: str) -> TaskContract:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise ContractError(
                f"Task '{task_id}' is not registered"
            ) from exc


class TaskContractAdapter:
    """Adapter izolujący TaskContract od istniejącego Orchestratora."""

    def __init__(self, task: TaskContract) -> None:
        self.task = task

    @property
    def task_id(self) -> str:
        return self.task.id

    @property
    def status(self) -> TaskStatus:
        return self.task.status

    def transition(self, target: TaskStatus) -> None:
        self.task.transition(target)

    def retry(self) -> None:
        self.task.retry()

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.task.id,
            "title": self.task.title,
            "status": self.task.status.value,
            "parent_id": self.task.parent_id,
            "retry_count": self.task.retry_count,
            "max_retries": self.task.max_retries,
            "metadata": dict(self.task.metadata),
        }


