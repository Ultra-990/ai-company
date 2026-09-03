#!/usr/bin/env bash
set -euo pipefail

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir=".migration-backup-${timestamp}"

mkdir -p "$backup_dir"
cp \
  app/tools/registry.py \
  app/services/approved_tool_execution.py \
  app/services/approvals.py \
  "$backup_dir/"

echo "Utworzono kopię zapasową: $backup_dir"

cat > app/tools/registry.py <<'PYTHON'
from __future__ import annotations

from typing import Any

from .base import Tool
from .filesystem import (
    list_project_files,
    read_project_file,
    write_project_file,
)


TOOLS = {
    "read_project_file": Tool(
        name="read_project_file",
        description="Odczytuje tekstowy plik znajdujący się w katalogu projektu.",
        handler=read_project_file,
        risk_level="low",
        requires_approval=False,
    ),
    "list_project_files": Tool(
        name="list_project_files",
        description="Wyświetla dozwolone pliki projektu.",
        handler=list_project_files,
        risk_level="low",
        requires_approval=False,
    ),
    "write_project_file": Tool(
        name="write_project_file",
        description="Zapisuje tekst do dozwolonego pliku projektu.",
        handler=write_project_file,
        risk_level="high",
        requires_approval=True,
    ),
}


def get_tool(name: str) -> Tool:
    try:
        return TOOLS[name]
    except KeyError as exc:
        raise KeyError(f"Nieznane narzędzie: {name}") from exc


def execute_tool(
    name: str,
    **arguments: Any,
) -> Any:
    """
    Wykonuje wyłącznie narzędzie niewymagające zatwierdzenia.

    Narzędzia wysokiego ryzyka muszą zostać wykonane przez
    ApprovedToolExecutionService, wyłącznie z kontraktem zapisanym
    po stronie serwera.
    """
    tool = get_tool(name)

    if tool.requires_approval:
        raise PermissionError(
            f"Narzędzie {name} wymaga zatwierdzonego serwerowego "
            "kontraktu wykonania."
        )

    return tool.execute(**arguments)
PYTHON

cat > app/services/approved_tool_execution.py <<'PYTHON'
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

        request = self._approval_repository.get_required(approval_request_id)

        if request.arguments_digest != actual_digest:
            raise ApprovalArgumentsMismatchError(
                "Argumenty w magazynie różnią się od zatwierdzonych."
            )

        tool = get_tool(tool_name)

        if not tool.requires_approval:
            raise ApprovalExecutionDeniedError(
                "Kontrakt dotyczy narzędzia bez wymaganego zatwierdzenia."
            )

        self._approval_repository.begin_execution(
            approval_request_id,
            tool_name=tool_name,
            arguments_digest=actual_digest,
        )

        try:
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
PYTHON

python - <<'PYTHON'
from pathlib import Path

path = Path("app/services/approvals.py")
content = path.read_text(encoding="utf-8")

old = '''    def consume_approved_request(
        self,
        request_id: int,
        *,
        tool_name: str,
        arguments_digest: str,
    ) -> ApprovalRequest:
'''

new = '''    def consume_approved_request(
        self,
        request_id: int,
        *,
        tool_name: str,
        arguments_digest: str,
    ) -> ApprovalRequest:
        """
        Przestarzały mechanizm jednofazowego zużycia zgody.

        Nie używać dla nowych wywołań. Zatwierdzone narzędzia muszą być
        wykonywane przez ApprovedToolExecutionService.
        """
'''

if old not in content:
    raise SystemExit(
        "Nie znaleziono oczekiwanej definicji consume_approved_request. "
        "Przywrócono możliwość ręcznej weryfikacji; plik nie został zmieniony."
    )

path.write_text(content.replace(old, new, 1), encoding="utf-8")
PYTHON

python -m compileall -q app

echo
echo "Migracja kodu produkcyjnego zakończona."
echo
echo "Pozostałe użycia starego API:"
grep -RIn \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude='*.pyc' \
  'consume_approved_request' \
  app tests || true

echo
echo "Uruchom teraz testy:"
echo "  pytest -q"
