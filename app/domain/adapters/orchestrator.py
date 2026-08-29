from __future__ import annotations

from app.domain.contracts import Department, MemoryRecord


class DomainRegistry:
    """Lekki rejestr kontraktów domenowych niezależny od SQLAlchemy."""

    def __init__(self) -> None:
        self._departments: dict[str, Department] = {}
        self._memories: dict[str, MemoryRecord] = {}

    def register_department(self, department: Department) -> Department:
        if department.id in self._departments:
            raise ValueError(
                f"Department already registered: {department.id}"
            )

        self._departments[department.id] = department
        return department

    def get_department(self, department_id: str) -> Department | None:
        return self._departments.get(department_id)

    def list_departments(self) -> list[Department]:
        return list(self._departments.values())

    def register_memory(self, memory: MemoryRecord) -> MemoryRecord:
        if memory.id in self._memories:
            raise ValueError(f"Memory already registered: {memory.id}")

        self._memories[memory.id] = memory
        return memory

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        return self._memories.get(memory_id)

    def list_memories(self) -> list[MemoryRecord]:
        return list(self._memories.values())
