from __future__ import annotations

from hashlib import sha256

from sqlalchemy import Engine, Select, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import (
    Base,
    create_database_engine,
    create_session_factory,
)
from app.models.audit import AuditEvent
from app.models.task import (
    ApprovalStatus,
    ResourceClass,
    RiskLevel,
    Task,
    TaskAttempt,
    TaskPriority,
    TaskStatus,
    TaskTransitionError,
    utc_now,
)
from app.services.documentation import generate_status_document


from app.db.migrations import (
    migrate_task_attempt_schema,
    migrate_task_queue_schema,
    migrate_task_roadmap_item_schema,
)


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
            migrate_task_roadmap_item_schema(self._engine)
            migrate_task_attempt_schema(self._engine)
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
        roadmap_item_id: str | None = None,
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

        normalized_roadmap_item_id = (
            roadmap_item_id.strip()
            if roadmap_item_id is not None
            else None
        )

        if normalized_roadmap_item_id == "":
            normalized_roadmap_item_id = None

        if (
            normalized_roadmap_item_id is not None
            and len(normalized_roadmap_item_id) > 200
        ):
            raise ValueError(
                "Identyfikator punktu roadmapy nie może przekraczać "
                "200 znaków"
            )

        task = Task(
            title=normalized_title,
            description=description,
            status=TaskStatus.PENDING,
            approval_status=ApprovalStatus.PENDING,
            priority=priority,
            resource_class=resource_class,
            risk_level=risk_level,
            assigned_agent=normalized_agent,
            roadmap_item_id=normalized_roadmap_item_id,
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
        approval_status: ApprovalStatus | None = None,
        priority: TaskPriority | None = None,
        resource_class: ResourceClass | None = None,
        risk_level: RiskLevel | None = None,
        assigned_agent: str | None = None,
        roadmap_item_id: str | None = None,
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

        normalized_roadmap_item_id: str | None = None

        if roadmap_item_id is not None:
            normalized_roadmap_item_id = roadmap_item_id.strip()

            if not normalized_roadmap_item_id:
                raise ValueError(
                    "Filtr punktu roadmapy nie może być pusty"
                )

        statement: Select[tuple[Task]] = select(Task)

        if status is not None:
            statement = statement.where(Task.status == status)

        if approval_status is not None:
                statement = statement.where(
                    Task.approval_status == approval_status
            )

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

        if normalized_roadmap_item_id is not None:
            statement = statement.where(
                Task.roadmap_item_id == normalized_roadmap_item_id
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

    def list_ready(
        self,
        *,
        limit: int = 50,
    ) -> list[Task]:
        """Zwraca zatwierdzone zadania oczekujące na wykonanie."""
        if not 1 <= limit <= 100:
            raise ValueError("limit musi mieścić się w zakresie 1–100")

        statement = (
            select(Task)
            .where(
                Task.status == TaskStatus.PENDING,
                Task.approval_status == ApprovalStatus.APPROVED,
                Task.queued_at.is_not(None),
            )
            .order_by(
                Task.queued_at.asc(),
                Task.id.asc(),
            )
            .limit(limit)
        )

        with self._session_factory() as session:
            tasks = list(session.scalars(statement).all())

            for task in tasks:
                session.expunge(task)

        return tasks

    def _set_approval_status(
        self,
        task_id: int,
        approval_status: ApprovalStatus,
        *,
        decision: str,
        reason: str,
    ) -> Task:
        with self._session_factory() as session:
            task = session.get(Task, task_id)

            if task is None:
                raise TaskNotFoundError(
                    f"Nie znaleziono zadania o identyfikatorze {task_id}"
                )

            task.approval_status = approval_status
            task.updated_at = utc_now()

            audit_event = AuditEvent(
                event_type="task_approval",
                operation=decision,
                decision=decision,
                allowed=approval_status == ApprovalStatus.APPROVED,
                reason=reason,
            )

            session.add(audit_event)
            session.commit()
            session.refresh(task)
            session.expunge(task)

        self._refresh_documentation()
        return task

    def approve(
        self,
        task_id: int,
        *,
        reason: str = "Zadanie zatwierdzone przez właściciela",
    ) -> Task:
        return self._set_approval_status(
            task_id,
            ApprovalStatus.APPROVED,
            decision="approve",
            reason=reason,
        )

    def reject(
        self,
        task_id: int,
        *,
        reason: str = "Zadanie odrzucone przez właściciela",
    ) -> Task:
        return self._set_approval_status(
            task_id,
            ApprovalStatus.REJECTED,
            decision="reject",
            reason=reason,
        )

    def claim(
        self,
        task_id: int,
        *,
        worker_id: str | None = None,
        reason: str = "Zadanie pobrane do wykonania",
    ) -> Task:
        """Atomowo pobiera zatwierdzone zadanie z kolejki do wykonania."""

        normalized_worker = (
            worker_id.strip()
            if worker_id is not None
            else None
        )

        if normalized_worker == "":
            normalized_worker = None

        if normalized_worker is not None and len(normalized_worker) > 100:
            raise ValueError(
                "Identyfikator workera nie może przekraczać 100 znaków"
            )

        audit_reason = reason
        if normalized_worker is not None:
            audit_reason = f"{reason}; worker={normalized_worker}"

        now = utc_now()

        with self._session_factory() as session:
            task_exists = session.get(Task, task_id)

            if task_exists is None:
                raise TaskNotFoundError(
                    f"Nie znaleziono zadania o identyfikatorze {task_id}"
                )

            result = session.execute(
                update(Task)
                .where(
                    Task.id == task_id,
                    Task.status == TaskStatus.PENDING,
                    Task.approval_status == ApprovalStatus.APPROVED,
                    Task.queued_at.is_not(None),
                )
                .values(
                    status=TaskStatus.IN_PROGRESS,
                    started_at=now,
                    updated_at=now,
                )
            )

            if result.rowcount != 1:
                session.rollback()
                raise TaskTransitionError(
                    "Zadanie nie jest gotowe do wykonania "
                    "albo zostało już przejęte"
                )

            attempt = TaskAttempt(
                task_id=task_id,
                worker_id=normalized_worker or "unknown",
                status="started",
                started_at=now,
            )
            session.add(attempt)

            audit_event = AuditEvent(
                event_type="task_execution",
                operation="claim",
                decision="claim",
                allowed=True,
                reason=audit_reason,
            )
            session.add(audit_event)

            session.commit()

            task = session.get(Task, task_id)
            assert task is not None
            session.expunge(task)

        self._refresh_documentation()
        return task

    def _finish_execution(
        self,
        task_id: int,
        new_status: TaskStatus,
        *,
        reason: str,
        result_content: str | None = None,
    ) -> Task:
        """Kończy wykonanie zadania i zapisuje zmianę w audycie."""

        normalized_reason = reason.strip()

        if not normalized_reason:
            raise ValueError("Powód operacji nie może być pusty")

        normalized_result: str | None = None

        if new_status is TaskStatus.COMPLETED:
            if result_content is None or not result_content.strip():
                raise ValueError(
                    "Wynik wykonania jest wymagany do ukończenia zadania"
                )

            normalized_result = result_content.strip()

        with self._session_factory() as session:
            task = session.get(Task, task_id)

            if task is None:
                raise TaskNotFoundError(
                    f"Nie znaleziono zadania o identyfikatorze {task_id}"
                )

            if task.status is not TaskStatus.IN_PROGRESS:
                raise TaskTransitionError(
                    "Zadanie musi mieć status IN_PROGRESS, "
                    f"aby wykonać operację {new_status.value}"
                )

            active_attempt = session.scalar(
                select(TaskAttempt)
                .where(
                    TaskAttempt.task_id == task_id,
                    TaskAttempt.status == "started",
                    TaskAttempt.finished_at.is_(None),
                )
                .order_by(
                    TaskAttempt.started_at.desc(),
                    TaskAttempt.id.desc(),
                )
                .limit(1)
            )

            # Zadania rozpoczęte przed wdrożeniem TaskAttempt mogą nie mieć
            # rekordu próby. Pozostają możliwe do poprawnego zakończenia.
            if active_attempt is not None:
                finished_at = utc_now()

                active_attempt.status = new_status.value
                active_attempt.finished_at = finished_at
                active_attempt.error_summary = (
                    normalized_reason
                    if new_status is TaskStatus.BLOCKED
                    else None
                )

                if new_status is TaskStatus.COMPLETED:
                    assert normalized_result is not None

                    active_attempt.result_content = normalized_result
                    active_attempt.result_checksum = sha256(
                        normalized_result.encode("utf-8")
                    ).hexdigest()
                    # Ukończenie wykonania i weryfikacja wyniku są
                    # rozdzielonymi etapami. Wynik oczekuje na niezależną
                    # kontrolę przez verify_attempt().
                    active_attempt.verification_status = "pending"
                    active_attempt.verification_reason = None
                    active_attempt.verified_at = None

            task.transition_to(new_status)

            audit_event = AuditEvent(
                event_type="task_execution",
                operation=new_status.value,
                decision=new_status.value,
                allowed=True,
                reason=normalized_reason,
            )

            session.add(audit_event)
            session.commit()
            session.refresh(task)
            session.expunge(task)

        self._refresh_documentation()
        return task

    def complete(
        self,
        task_id: int,
        *,
        reason: str = "Zadanie wykonane",
        result_content: str | None = None,
    ) -> Task:
        """
        Oznacza wykonywane zadanie jako ukończone.

        Ukończenie wymaga jawnego, niepustego rezultatu. Rezultat wraz
        z sumą SHA-256 jest zapisywany w aktywnej próbie ze statusem
        weryfikacji ``pending``.
        """
        return self._finish_execution(
            task_id,
            TaskStatus.COMPLETED,
            reason=reason,
            result_content=result_content,
        )

    def verify_attempt(
        self,
        task_id: int,
        *,
        result_content: str,
        verifier_id: str,
        reason: str = "Wynik wykonania został zweryfikowany",
    ) -> TaskAttempt:
        """
        Weryfikuje ostatnią ukończoną próbę zadania.

        Akceptacja wymaga zgodności przekazanej treści z trwale zapisanym
        rezultatem oraz zgodności ponownie obliczonej sumy SHA-256.
        Niezgodność odrzuca próbę, ale nie zmienia statusu wykonania zadania.
        """

        normalized_result = result_content.strip()
        normalized_verifier = verifier_id.strip()
        normalized_reason = reason.strip()

        if not normalized_result:
            raise ValueError("Wynik do weryfikacji nie może być pusty")

        if not normalized_verifier:
            raise ValueError("Identyfikator weryfikatora nie może być pusty")

        if len(normalized_verifier) > 100:
            raise ValueError(
                "Identyfikator weryfikatora nie może przekraczać 100 znaków"
            )

        if not normalized_reason:
            raise ValueError("Powód weryfikacji nie może być pusty")

        supplied_checksum = sha256(
            normalized_result.encode("utf-8")
        ).hexdigest()

        with self._session_factory() as session:
            task = session.get(Task, task_id)

            if task is None:
                raise TaskNotFoundError(
                    f"Nie znaleziono zadania o identyfikatorze {task_id}"
                )

            attempt = session.scalar(
                select(TaskAttempt)
                .where(
                    TaskAttempt.task_id == task_id,
                    TaskAttempt.status == TaskStatus.COMPLETED.value,
                )
                .order_by(
                    TaskAttempt.finished_at.desc(),
                    TaskAttempt.id.desc(),
                )
                .limit(1)
            )

            if attempt is None:
                raise TaskTransitionError(
                    "Zadanie nie ma ukończonej próby do weryfikacji"
                )

            if attempt.verification_status != "pending":
                raise TaskTransitionError(
                    "Próba wykonania została już zweryfikowana"
                )

            verification_failed_reason: str | None = None

            if not attempt.result_content or not attempt.result_checksum:
                verification_failed_reason = (
                    "Brak trwale zapisanego wyniku lub sumy kontrolnej"
                )
            else:
                stored_checksum = sha256(
                    attempt.result_content.encode("utf-8")
                ).hexdigest()

                if stored_checksum != attempt.result_checksum:
                    verification_failed_reason = (
                        "Zapisana suma SHA-256 nie odpowiada trwałemu wynikowi"
                    )
                elif (
                    attempt.result_content != normalized_result
                    or attempt.result_checksum != supplied_checksum
                ):
                    verification_failed_reason = (
                        "Przekazany wynik nie odpowiada zapisanemu rezultatowi"
                    )

            verified_at = utc_now()
            accepted = verification_failed_reason is None
            decision = "verified" if accepted else "rejected"
            verification_reason = (
                normalized_reason
                if accepted
                else f"{normalized_reason}; {verification_failed_reason}"
            )

            attempt.verification_status = decision
            attempt.verification_reason = verification_reason
            attempt.verified_at = verified_at

            audit_event = AuditEvent(
                event_type="task_verification",
                operation="verify",
                decision=decision,
                allowed=accepted,
                reason=(
                    f"{verification_reason}; "
                    f"verifier_id={normalized_verifier}"
                ),
            )
            session.add(audit_event)
            session.commit()
            session.refresh(attempt)
            session.expunge(attempt)

        return attempt

    def block(
        self,
        task_id: int,
        *,
        reason: str,
    ) -> Task:
        """Blokuje wykonywane zadanie i zapisuje powód w audycie."""

        return self._finish_execution(
            task_id,
            TaskStatus.BLOCKED,
            reason=reason,
        )

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

    def assign_roadmap_item(
        self,
        task_id: int,
        roadmap_item_id: str | None,
    ) -> Task:
        """Przypisuje zadanie do punktu roadmapy lub usuwa przypisanie."""
        normalized_roadmap_item_id = (
            roadmap_item_id.strip()
            if roadmap_item_id is not None
            else None
        )

        if normalized_roadmap_item_id == "":
            normalized_roadmap_item_id = None

        if (
            normalized_roadmap_item_id is not None
            and len(normalized_roadmap_item_id) > 200
        ):
            raise ValueError(
                "Identyfikator punktu roadmapy nie może przekraczać "
                "200 znaków"
            )

        with self._session_factory() as session:
            task = session.get(Task, task_id)

            if task is None:
                raise TaskNotFoundError(
                    f"Nie znaleziono zadania o identyfikatorze {task_id}"
                )

            task.roadmap_item_id = normalized_roadmap_item_id
            task.updated_at = utc_now()
            session.commit()
            session.refresh(task)
            session.expunge(task)

        self._refresh_documentation()
        return task

    def summary(self) -> dict[str, int]:
        """Zwraca pełne statystyki zadań bez limitu listowania."""
        with self._session_factory() as session:
            total = session.scalar(
                select(func.count()).select_from(Task)
            ) or 0

            pending = session.scalar(
                select(func.count())
                .select_from(Task)
                .where(
                    Task.approval_status == ApprovalStatus.PENDING
                )
            ) or 0

            approved = session.scalar(
                select(func.count())
                .select_from(Task)
                .where(
                    Task.approval_status == ApprovalStatus.APPROVED
                )
            ) or 0

            rejected = session.scalar(
                select(func.count())
                .select_from(Task)
                .where(
                    Task.approval_status == ApprovalStatus.REJECTED
                )
            ) or 0

        return {
            "total": int(total),
            "pending": int(pending),
            "approved": int(approved),
            "rejected": int(rejected),
        }

    def progress_summary(self) -> dict[str, int | float | dict[str, int]]:
        """Zwraca agregaty postępu dla wszystkich zadań."""
        with self._session_factory() as session:
            task_count = session.scalar(
                select(func.count()).select_from(Task)
            ) or 0

            average_progress = session.scalar(
                select(func.avg(Task.progress))
            ) or 0

            counts = {}
            for status in TaskStatus:
                counts[status.value] = int(
                    session.scalar(
                        select(func.count())
                        .select_from(Task)
                        .where(Task.status == status)
                    ) or 0
                )

        return {
            "task_count": int(task_count),
            "total_progress": round(float(average_progress)),
            "counts": counts,
        }

    def close(self) -> None:
        self._engine.dispose()
