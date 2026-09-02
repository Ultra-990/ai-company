from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_database_engine, create_session_factory
from app.models.pending_tool_execution import PendingToolExecution
from app.services.approvals import (
    ApprovalArgumentsMismatchError,
    ApprovalExecutionDeniedError,
    ApprovalRepository,
    canonical_arguments_digest,
)
from app.tools.registry import get_tool


class PendingToolExecutionStore:
    """
    Trwały magazyn argumentów, używany wyłącznie po stronie serwera.

    Ta klasa nie może być wystawiona bezpośrednio przez API właściciela.
    """

    def __init__(self, database_url: str) -> None:
        self._engine = create_database_engine(database_url)
        self._session_factory: sessionmaker[Session] = (
            create_session_factory(self._engine)
        )

    def get_arguments(
        self,
        approval_request_id: int,
    ) -> tuple[str, dict[str, Any], str]:
        with self._session_factory() as session:
            record = session.scalar(
                select(PendingToolExecution).where(
                    PendingToolExecution.approval_request_id
                    == approval_request_id
                )
            )

            if record is None:
                raise ApprovalExecutionDeniedError(
                    "Brak serwerowego kontraktu wykonania."
                )

            try:
                arguments = json.loads(record.arguments_json)
            except json.JSONDecodeError as exc:
                raise ApprovalExecutionDeniedError(
                    "Uszkodzony kontrakt wykonania."
                ) from exc

            if not isinstance(arguments, dict):
                raise ApprovalExecutionDeniedError(
                    "Argumenty kontraktu nie są obiektem JSON."
                )

            return (
                record.tool_name,
                arguments,
                record.arguments_digest,
            )

    def delete(self, approval_request_id: int) -> None:
        with self._session_factory() as session:
            session.execute(
                delete(PendingToolExecution).where(
                    PendingToolExecution.approval_request_id
                    == approval_request_id
                )
            )
            session.commit()

    def close(self) -> None:
        self._engine.dispose()


class ApprovedToolExecutionService:
    """
    Wykonuje narzędzie wyłącznie na podstawie zatwierdzonego kontraktu.

    Argumenty nie są pobierane z request body. Przejście APPROVED →
    EXECUTING następuje przed uruchomieniem handlera, a EXECUTED jest
    ustawiane wyłącznie po sukcesie handlera.
    """

    def __init__(
        self,
        approval_repository: ApprovalRepository,
        pending_store: PendingToolExecutionStore,
    ) -> None:
        self._approval_repository = approval_repository
        self._pending_store = pending_store

    def execute(self, approval_request_id: int) -> Any:
        tool_name, arguments, stored_digest = (
            self._pending_store.get_arguments(approval_request_id)
        )
        actual_digest = canonical_arguments_digest(arguments)

        if actual_digest != stored_digest:
            raise ApprovalArgumentsMismatchError(
                "Argumenty w magazynie nie spełniają kontraktu integralności."
            )

        request = self._approval_repository.get_required(
            approval_request_id
        )

        if request.arguments_digest != actual_digest:
            raise ApprovalArgumentsMismatchError(
                "Argumenty w magazynie różnią się od zatwierdzonych."
            )

        self._approval_repository.begin_execution(
            approval_request_id,
            tool_name=tool_name,
            arguments_digest=actual_digest,
        )

        try:
            tool = get_tool(tool_name)

            if not tool.requires_approval:
                raise ApprovalExecutionDeniedError(
                    "Kontrakt dotyczy narzędzia bez wymaganego zatwierdzenia."
                )

            result = tool.execute(**arguments)
        except Exception:
            self._approval_repository.fail_execution(
                approval_request_id,
                reason="Wykonanie narzędzia zakończyło się błędem.",
            )
            self._pending_store.delete(approval_request_id)
            raise

        self._approval_repository.finish_execution(approval_request_id)
        self._pending_store.delete(approval_request_id)
        return result
