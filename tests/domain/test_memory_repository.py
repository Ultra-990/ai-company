from app.domain.contracts import MemoryRecord
from app.domain.repositories import (
    InMemoryMemoryRepository,
    MemoryRepository,
)


def test_in_memory_repository_implements_repository_contract():
    repository = InMemoryMemoryRepository()

    assert isinstance(repository, MemoryRepository)


def test_save_and_get_memory_record():
    repository = InMemoryMemoryRepository()
    record = MemoryRecord(id="memory-1", content="Ważna informacja")

    result = repository.save(record)

    assert result == record
    assert repository.get("memory-1") == record


def test_get_missing_memory_record_returns_none():
    repository = InMemoryMemoryRepository()

    assert repository.get("missing") is None


def test_save_replaces_record_with_the_same_id():
    repository = InMemoryMemoryRepository()
    first = MemoryRecord(id="memory-1", content="Pierwsza wersja")
    second = MemoryRecord(id="memory-1", content="Druga wersja")

    repository.save(first)
    repository.save(second)

    assert repository.get("memory-1") == second
    assert tuple(repository.list()) == (second,)


def test_delete_existing_memory_record():
    repository = InMemoryMemoryRepository()
    record = MemoryRecord(id="memory-1", content="Do usunięcia")
    repository.save(record)

    assert repository.delete("memory-1") is True
    assert repository.get("memory-1") is None


def test_delete_missing_memory_record_returns_false():
    repository = InMemoryMemoryRepository()

    assert repository.delete("missing") is False


def test_list_returns_all_records():
    repository = InMemoryMemoryRepository()
    first = MemoryRecord(id="memory-1", content="Pierwsza")
    second = MemoryRecord(id="memory-2", content="Druga")

    repository.save(first)
    repository.save(second)

    assert tuple(repository.list()) == (first, second)
