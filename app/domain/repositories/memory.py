from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from app.domain.contracts import MemoryRecord


class MemoryRepository(ABC):
    @abstractmethod
    def save(self, record: MemoryRecord) -> MemoryRecord:
        """Zapisuje rekord pamięci i zwraca zapisany rekord."""
        raise NotImplementedError

    @abstractmethod
    def get(self, record_id: str) -> MemoryRecord | None:
        """Zwraca rekord o podanym ID albo None."""
        raise NotImplementedError

    @abstractmethod
    def list(self) -> Iterable[MemoryRecord]:
        """Zwraca wszystkie rekordy pamięci."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, record_id: str) -> bool:
        """Usuwa rekord i zwraca informację, czy istniał."""
        raise NotImplementedError
