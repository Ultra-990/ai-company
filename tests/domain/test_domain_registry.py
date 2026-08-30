from app.domain.repositories import InMemoryMemoryRepository
import pytest

from app.domain.adapters import DomainRegistry
from app.domain.contracts import Department, MemoryRecord


def test_registers_and_reads_department():
    registry = DomainRegistry()
    department = Department(id="tech", name="Technical")

    assert registry.register_department(department) == department
    assert registry.get_department("tech") == department
    assert registry.list_departments() == [department]


def test_rejects_duplicate_department():
    registry = DomainRegistry()
    department = Department(id="tech", name="Technical")

    registry.register_department(department)

    with pytest.raises(ValueError, match="already registered"):
        registry.register_department(department)


def test_registers_and_reads_memory():
    registry = DomainRegistry()
    memory = MemoryRecord(id="m-1", content="Important decision")

    assert registry.register_memory(memory) == memory
    assert registry.get_memory("m-1") == memory
    assert registry.list_memories() == [memory]


def test_rejects_duplicate_memory():
    registry = DomainRegistry()
    memory = MemoryRecord(id="m-1", content="Important decision")

    registry.register_memory(memory)

    with pytest.raises(ValueError, match="already registered"):
        registry.register_memory(memory)


def test_domain_registry_uses_injected_memory_repository():

    repository = InMemoryMemoryRepository()
    registry = DomainRegistry(memory_repository=repository)

    assert registry.memory_repository is repository


def test_domain_registry_delegates_memory_operations_to_repository():
    memory = MemoryRecord(id="memory-1", content="Ważna informacja")
    repository = InMemoryMemoryRepository()
    registry = DomainRegistry(memory_repository=repository)

    assert registry.register_memory(memory) == memory
    assert registry.get_memory("memory-1") == memory
    assert tuple(registry.list_memories()) == (memory,)
    assert registry.delete_memory("memory-1") is True
    assert registry.get_memory("memory-1") is None
