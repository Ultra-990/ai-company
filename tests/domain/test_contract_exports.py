from app.domain.contracts import Department, MemoryRecord


def test_domain_contracts_are_publicly_exported():
    assert Department is not None
    assert MemoryRecord is not None
