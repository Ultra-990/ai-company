from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import (
    Base,
    create_database_engine,
    create_session_factory,
)
from app.db.migrations import migrate_approval_request_schema
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


class ApprovalExecutionDeniedError(PermissionError):
    """Wniosek nie może autoryzować wykonania narzędzia."""


class ApprovalArgumentsMismatchError(ApprovalExecutionDeniedError):
    """Argumenty wykonania różnią się od zatwierdzonych."""


def canonical_arguments_digest(arguments: Mapping[str, Any]) -> str:
    """Zwraca SHA-256 kanonicznej reprezentacji JSON argumentów."""
    if not isinstance(arguments, Mapping):
        raise ValueError("Argumenty muszą być obiektem mapującym.")

    try:
        canonical = json.dumps(
            dict(arguments),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Argumenty narzędzia muszą być serializowalne do JSON."
        ) from exc

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_tool_approval_preview(
    tool_name: str,
    arguments: Mapping[str, Any],
) -> str:
    """
    Buduje bezpieczny, deterministyczny podgląd dla właściciela.

    Podgląd nie może zależeć od opisu dostarczonego przez klienta i nie
    zawiera wrażliwej treści argumentu ``content``.
    """
    if not isinstance(tool_name, str):
        raise ValueError("Nazwa narzędzia musi być tekstem.")
    if not isinstance(arguments, Mapping):
        raise ValueError("Argumenty muszą być obiektem mapującym.")

    normalized_tool_name = tool_name.strip()

    if normalized_tool_name != "write_project_file":
        raise ValueError(
            "Tworzenie wniosków jest dozwolone wyłącznie dla obsługiwanych "
            "narzędzi wymagających zatwierdzenia."
        )

    path = arguments.get("path")
    content = arguments.get("content")

    if not isinstance(path, str) or not path.strip():
        raise ValueError("Argument path musi być niepustym tekstem.")
    if not isinstance(content, str):
        raise ValueError("Argument content musi być tekstem.")

    encoded_content = content.encode("utf-8")
    content_digest = hashlib.sha256(encoded_content).hexdigest()

    return (
        "Zapis pliku projektu:\n"
        f"- ścieżka: {path.strip()}\n"
        "- operacja: utworzenie lub nadpisanie pliku\n"
        f"- rozmiar treści UTF-8: {len(encoded_content)} B\n"
        f"- SHA-256 treści: {content_digest}"
    )


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
            migrate_approval_request_schema(self._engine)

    def create(
        self,
        *,
        task_id: int,
        operation_type: str,
        description: str,
    ) -> ApprovalRequest:
        if not isinstance(task_id, int) or isinstance(task_id, bool) or task_id <= 0:
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

    def create_tool_request(
        self,
        *,
        task_id: int,
        tool_name: str,
        arguments: Mapping[str, Any],
        description: str | None = None,
    ) -> ApprovalRequest:
        """
        Tworzy kompletny kontrakt wykonania narzędzia w jednej transakcji.

        Parametr ``description`` pozostaje tymczasowo dla zgodności wstecznej,
        lecz nie jest zaufany i nie wpływa na opis widoczny dla właściciela.
        """
        if (
            not isinstance(task_id, int)
            or isinstance(task_id, bool)
            or task_id <= 0
        ):
            raise ValueError("task_id musi być dodatni")

        if not isinstance(tool_name, str):
            raise ValueError("Nazwa narzędzia musi być tekstem.")

        normalized_tool_name = tool_name.strip()
        if not normalized_tool_name:
            raise ValueError("Nazwa narzędzia nie może być pusta.")
        if len(normalized_tool_name) > 128:
            raise ValueError("Nazwa narzędzia nie może przekraczać 128 znaków.")

        preview = build_tool_approval_preview(
            normalized_tool_name,
            arguments,
        )
        arguments_digest = canonical_arguments_digest(arguments)

        request = ApprovalRequest(
            task_id=task_id,
            operation_type="tool_call",
            description=preview,
            status=ApprovalRequestStatus.PENDING,
            tool_name=normalized_tool_name,
            arguments_digest=arguments_digest,
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
            .where(ApprovalRequest.status == ApprovalRequestStatus.PENDING)
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
                    ApprovalRequest.status == ApprovalRequestStatus.PENDING,
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
                    allowed=new_status == ApprovalRequestStatus.APPROVED,
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

    def consume_approved_request(
        self,
        request_id: int,
        *,
        tool_name: str,
        arguments_digest: str,
    ) -> ApprovalRequest:
        if not isinstance(request_id, int) or isinstance(request_id, bool) or request_id <= 0:
            raise ApprovalExecutionDeniedError("Niepoprawny approval_request_id.")
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ApprovalExecutionDeniedError("Niepoprawna nazwa narzędzia.")
        if not isinstance(arguments_digest, str) or len(arguments_digest) != 64:
            raise ApprovalExecutionDeniedError("Niepoprawny odcisk argumentów.")

        normalized_tool_name = tool_name.strip()
        now = utc_now()

        with self._session_factory() as session:
            result = session.execute(
                update(ApprovalRequest)
                .where(
                    ApprovalRequest.id == request_id,
                    ApprovalRequest.status == ApprovalRequestStatus.APPROVED,
                    ApprovalRequest.tool_name == normalized_tool_name,
                    ApprovalRequest.arguments_digest == arguments_digest,
                    ApprovalRequest.executed_at.is_(None),
                )
                .values(
                    status=ApprovalRequestStatus.EXECUTED,
                    executed_at=now,
                )
            )

            if result.rowcount != 1:
                request = session.get(ApprovalRequest, request_id)

                if request is None:
                    raise ApprovalRequestNotFoundError(
                        f"Nie znaleziono wniosku {request_id}"
                    )
                if request.arguments_digest != arguments_digest:
                    raise ApprovalArgumentsMismatchError(
                        "Argumenty różnią się od zatwierdzonych."
                    )
                if request.tool_name != normalized_tool_name:
                    raise ApprovalExecutionDeniedError(
                        "Zgoda dotyczy innego narzędzia."
                    )
                if request.status == ApprovalRequestStatus.EXECUTED:
                    raise ApprovalExecutionDeniedError(
                        "Wniosek został już zużyty."
                    )
                raise ApprovalExecutionDeniedError(
                    "Wniosek nie jest zatwierdzony lub nie może zostać użyty."
                )

            session.add(
                AuditEvent(
                    event_type="approval_request",
                    operation="executed",
                    decision="executed",
                    allowed=True,
                    reason=(
                        f"approval_request_id={request_id}; "
                        f"tool_name={normalized_tool_name}; status=executed"
                    ),
                )
            )
            session.commit()

            request = session.get(ApprovalRequest, request_id)
            assert request is not None
            session.expunge(request)
            return request

    def close(self) -> None:
        self._engine.dispose()
