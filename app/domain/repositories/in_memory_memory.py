from __future__ import annotations

from collections.abc import Iterable

from app.domain.contracts import MemoryRecord
from app.domain.repositories.memory import MemoryRepository


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    def save(self, record: MemoryRecord) -> MemoryRecord:
        self._records[record.id] = record
        return record

    def get(self, record_id: str) -> MemoryRecord | None:
        return self._records.get(record_id)

    def list(self) -> Iterable[MemoryRecord]:
        return tuple(self._records.values())

    def delete(self, record_id: str) -> bool:
        return self._records.pop(record_id, None) is not None
