from app.domain.adapters.orchestrator import DomainRegistry
from app.domain.contracts import Department, MemoryRecord
from app.brain.orchestrator import Orchestrator


def test_orchestrator_creates_default_domain_registry():
    orchestrator = Orchestrator()

    assert isinstance(orchestrator.domain_registry, DomainRegistry)


def test_orchestrator_uses_injected_domain_registry():
    registry = DomainRegistry()
    orchestrator = Orchestrator(domain_registry=registry)

    assert orchestrator.domain_registry is registry


def test_orchestrator_registers_department_through_registry():
    orchestrator = Orchestrator()
    department = Department(id="engineering", name="Engineering")

    result = orchestrator.register_department(department)

    assert result == department
    assert orchestrator.get_department("engineering") == department


def test_orchestrator_registers_memory_through_registry():
    orchestrator = Orchestrator()
    memory = MemoryRecord(
        id="memory-1",
        content="Ważna informacja",
    )

    result = orchestrator.register_memory(memory)

    assert result == memory
    assert orchestrator.get_memory("memory-1") == memory
