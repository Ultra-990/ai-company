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
