from __future__ import annotations

from app.models.task import Task
from app.services.tasks import TaskRepository


class TaskWorker:
    """Pobiera gotowe zadania z kolejki i atomowo je przejmuje."""

    def __init__(
        self,
        repository: TaskRepository,
        *,
        worker_id: str,
    ) -> None:
        normalized_worker_id = worker_id.strip()

        if not normalized_worker_id:
            raise ValueError("Identyfikator workera nie może być pusty")

        if len(normalized_worker_id) > 100:
            raise ValueError(
                "Identyfikator workera nie może przekraczać 100 znaków"
            )

        self.repository = repository
        self.worker_id = normalized_worker_id

    def claim_next(self) -> Task | None:
        """Przejmuje najstarsze dostępne zadanie albo zwraca None."""

        return self.repository.claim_next(worker_id=self.worker_id)
