from app.models.task import Task
from app.services.tasks import TaskRepository


class TaskScheduler:
    """Wybiera i rezerwuje kolejne zadania z kolejki."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def schedule_next(self) -> Task | None:
        """Zwraca kolejne zadanie i oznacza je jako wykonywane."""
        return self._repository.claim_next_pending_task()
