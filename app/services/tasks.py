from __future__ import annotations

from sqlalchemy import Engine, Select, case, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import (
    Base,
    create_database_engine,
    create_session_factory,
)
from app.models.task import (
    ResourceClass,
    RiskLevel,
    Task,
    TaskPriority,
    TaskStatus,
    utc_now,
)
from app.services.documentation import generate_status_document

from app.db.migrations import migrate_task_queue_schema


class TaskNotFoundError(LookupError):
    """Zadanie o podanym identyfikatorze nie istnieje."""


class TaskRepository:
    """Warstwa trwałego zapisu i odczytu zadań."""
    def _refresh_documentation(self) -> None:
        """Aktualizuje automatyczną dokumentację na podstawie zadań."""
        tasks = self.list_recent(limit=100)
        generate_status_document(tasks)

    def __init__(
        self,
        database_url: str,
        *,
        initialize: bool = True,
    ) -> None:
        self._engine: Engine = create_database_engine(database_url)
        self._session_factory: sessionmaker[Session] = (
            create_session_factory(self._engine)
        )

        if initialize:
            migrate_task_queue_schema(self._engine)
            Base.metadata.create_all(self._engine)

    def create(
        self,
        *,
        title: str,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        resource_class: ResourceClass = ResourceClass.LIGHT,
        risk_level: RiskLevel = RiskLevel.LOW,
        assigned_agent: str | None = None,
    ) -> Task:
        normalized_title = title.strip()

        if not normalized_title:
            raise ValueError("Tytuł zadania nie może być pusty")

        if len(normalized_title) > 200:
            raise ValueError(
                "Tytuł zadania nie może przekraczać 200 znaków"
            )

        normalized_agent = (
            assigned_agent.strip()
            if assigned_agent is not None
            else None
        )

        if normalized_agent == "":
            normalized_agent = None

        if normalized_agent is not None and len(normalized_agent) > 100:
            raise ValueError(
                "Nazwa przypisanego agenta nie może przekraczać 100 znaków"
            )

        task = Task(
            title=normalized_title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            resource_class=resource_class,
            risk_level=risk_level,
            assigned_agent=normalized_agent,
            queued_at=utc_now(),
        )

        with self._session_factory() as session:
            session.add(task)
            session.commit()
            session.refresh(task)
            session.expunge(task)

        self._refresh_documentation()

        return task

    def get(self, task_id: int) -> Task | None:
        with self._session_factory() as session:
            task = session.get(Task, task_id)

            if task is not None:
                session.expunge(task)

        return task

    def get_required(self, task_id: int) -> Task:
        task = self.get(task_id)

        if task is None:
            raise TaskNotFoundError(
                f"Nie znaleziono zadania o identyfikatorze {task_id}"
            )

        return task

    def list_recent(
        self,
        *,
        limit: int = 50,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        resource_class: ResourceClass | None = None,
        risk_level: RiskLevel | None = None,
        assigned_agent: str | None = None,
    ) -> list[Task]:
        if not 1 <= limit <= 100:
            raise ValueError("limit musi mieścić się w zakresie 1–100")

        normalized_agent: str | None = None

        if assigned_agent is not None:
            normalized_agent = assigned_agent.strip()

            if not normalized_agent:
                raise ValueError(
                    "Filtr przypisanego agenta nie może być pusty"
                )

        statement: Select[tuple[Task]] = select(Task)

        if status is not None:
            statement = statement.where(Task.status == status)

        if priority is not None:
            statement = statement.where(Task.priority == priority)

        if resource_class is not None:
            statement = statement.where(
                Task.resource_class == resource_class
            )

        if risk_level is not None:
            statement = statement.where(Task.risk_level == risk_level)

        if normalized_agent is not None:
            statement = statement.where(
                Task.assigned_agent == normalized_agent
            )

        statement = statement.order_by(
            Task.created_at.desc(),
            Task.id.desc(),
        ).limit(limit)

        with self._session_factory() as session:
            tasks = list(session.scalars(statement).all())

            for task in tasks:
                session.expunge(task)

        return tasks

    def transition(
        self,
        task_id: int,
        new_status: TaskStatus,
    ) -> Task:
        with self._session_factory() as session:
            task = session.get(Task, task_id)

            if task is None:
                raise TaskNotFoundError(
                    f"Nie znaleziono zadania o identyfikatorze {task_id}"
                )

            task.transition_to(new_status)
            session.commit()
            session.refresh(task)
            session.expunge(task)

        self._refresh_documentation()

        return task

    def assign(
        self,
        task_id: int,
        assigned_agent: str | None,
    ) -> Task:
        normalized_agent = (
            assigned_agent.strip()
            if assigned_agent is not None
            else None
        )

        if normalized_agent == "":
            normalized_agent = None

        if normalized_agent is not None and len(normalized_agent) > 100:
            raise ValueError(
                "Nazwa przypisanego agenta nie może przekraczać 100 znaków"
            )

        with self._session_factory() as session:
            task = session.get(Task, task_id)

            if task is None:
                raise TaskNotFoundError(
                    f"Nie znaleziono zadania o identyfikatorze {task_id}"
                )

            task.assigned_agent = normalized_agent
            task.updated_at = utc_now()
            session.commit()
            session.refresh(task)
            session.expunge(task)

        self._refresh_documentation()

        return task

    def claim_next_pending_task(self) -> Task | None:
        """
        Wybiera i rezerwuje następne oczekujące zadanie.

        Kolejność:
        1. tylko zadania pending,
        2. critical, high, normal, low,
        3. najstarsze queued_at,
        4. najniższe id.
        """
        priority_order = case(
            (Task.priority == TaskPriority.CRITICAL, 0),
            (Task.priority == TaskPriority.HIGH, 1),
            (Task.priority == TaskPriority.NORMAL, 2),
            (Task.priority == TaskPriority.LOW, 3),
            else_=4,
        )

        statement: Select[tuple[Task]] = (
            select(Task)
            .where(Task.status == TaskStatus.PENDING)
            .order_by(
                priority_order.asc(),
                Task.queued_at.asc(),
                Task.id.asc(),
            )
            .limit(1)
        )

        with self._session_factory() as session:
            task = session.scalar(statement)

            if task is None:
                return None

            task.transition_to(TaskStatus.IN_PROGRESS)
            session.commit()
            session.refresh(task)
            session.expunge(task)

        self._refresh_documentation()

        return task

    def close(self) -> None:
        self._engine.dispose()
