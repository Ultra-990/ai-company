from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import (
    Base,
    create_database_engine,
    create_session_factory,
)
from app.models.approval import (
    ApprovalRequest,
    ApprovalRequestStatus,
    utc_now,
)
from app.models.audit import AuditEvent


class ApprovalRequestNotFoundError(LookupError):
    """Wniosek o zatwierdzenie nie istnieje."""


class ApprovalStateConflictError(RuntimeError):
    """Wniosek ma już rozstrzygnięty status."""


class ApprovalRepository:
    """Trwałe repozytorium wniosków o zatwierdzenie."""

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
            Base.metadata.create_all(self._engine)

    def create(
        self,
        *,
        task_id: int,
        operation_type: str,
        description: str,
    ) -> ApprovalRequest:
        if task_id <= 0:
            raise ValueError("task_id musi być dodatni")

        operation = operation_type.strip()
        text = description.strip()

        if not operation:
            raise ValueError("Typ operacji nie może być pusty")
        if len(operation) > 64:
            raise ValueError("Typ operacji nie może przekraczać 64 znaków")
        if not text:
            raise ValueError("Opis nie może być pusty")

        request = ApprovalRequest(
            task_id=task_id,
            operation_type=operation,
            description=text,
            status=ApprovalRequestStatus.PENDING,
        )

        with self._session_factory() as session:
            session.add(request)
            session.commit()
            session.refresh(request)
            session.expunge(request)

        return request

    def get(self, request_id: int) -> ApprovalRequest | None:
        with self._session_factory() as session:
            request = session.get(ApprovalRequest, request_id)
            if request is not None:
                session.expunge(request)
            return request

    def get_required(self, request_id: int) -> ApprovalRequest:
        request = self.get(request_id)
        if request is None:
            raise ApprovalRequestNotFoundError(
                f"Nie znaleziono wniosku {request_id}"
            )
        return request

    def list_pending(self, *, limit: int = 50) -> list[ApprovalRequest]:
        if not 1 <= limit <= 100:
            raise ValueError("limit musi mieścić się w zakresie 1–100")

        statement = (
            select(ApprovalRequest)
            .where(
                ApprovalRequest.status
                == ApprovalRequestStatus.PENDING
            )
            .order_by(
                ApprovalRequest.created_at.asc(),
                ApprovalRequest.id.asc(),
            )
            .limit(limit)
        )

        with self._session_factory() as session:
            requests = list(session.scalars(statement).all())
            for request in requests:
                session.expunge(request)
            return requests

    def _resolve(
        self,
        request_id: int,
        new_status: ApprovalRequestStatus,
        *,
        reason: str,
    ) -> ApprovalRequest:
        safe_reason = reason.strip()
        if not safe_reason:
            raise ValueError("Powód decyzji nie może być pusty")
        if len(safe_reason) > 500:
            raise ValueError("Powód decyzji nie może przekraczać 500 znaków")

        now = utc_now()

        with self._session_factory() as session:
            result = session.execute(
                update(ApprovalRequest)
                .where(
                    ApprovalRequest.id == request_id,
                    ApprovalRequest.status
                    == ApprovalRequestStatus.PENDING,
                )
                .values(
                    status=new_status,
                    resolved_at=now,
                    reason=safe_reason,
                )
            )

            if result.rowcount != 1:
                if session.get(ApprovalRequest, request_id) is None:
                    raise ApprovalRequestNotFoundError(
                        f"Nie znaleziono wniosku {request_id}"
                    )
                raise ApprovalStateConflictError(
                    "Wniosek został już rozstrzygnięty"
                )

            session.add(
                AuditEvent(
                    event_type="approval_request",
                    operation=new_status.value,
                    decision=new_status.value,
                    allowed=new_status
                    == ApprovalRequestStatus.APPROVED,
                    reason=(
                        f"approval_request_id={request_id}; "
                        f"status={new_status.value}; reason={safe_reason}"
                    ),
                )
            )

            session.commit()
            request = session.get(ApprovalRequest, request_id)
            assert request is not None
            session.expunge(request)
            return request

    def approve(
        self,
        request_id: int,
        *,
        reason: str = "Wniosek zatwierdzony przez właściciela",
    ) -> ApprovalRequest:
        return self._resolve(
            request_id,
            ApprovalRequestStatus.APPROVED,
            reason=reason,
        )

    def reject(
        self,
        request_id: int,
        *,
        reason: str = "Wniosek odrzucony przez właściciela",
    ) -> ApprovalRequest:
        return self._resolve(
            request_id,
            ApprovalRequestStatus.REJECTED,
            reason=reason,
        )

    def expire(
        self,
        request_id: int,
        *,
        reason: str = "Wniosek wygasł",
    ) -> ApprovalRequest:
        return self._resolve(
            request_id,
            ApprovalRequestStatus.EXPIRED,
            reason=reason,
        )

    def close(self) -> None:
        self._engine.dispose()
