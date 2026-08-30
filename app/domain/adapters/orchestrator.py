from __future__ import annotations

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
