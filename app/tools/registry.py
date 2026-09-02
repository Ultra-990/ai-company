from __future__ import annotations

from typing import Any

from app.services.approvals import (
    ApprovalRepository,
    canonical_arguments_digest,
)

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
    *,
    approval_repository: ApprovalRepository | None = None,
    approval_request_id: int | None = None,
    **arguments: Any,
) -> Any:
    """Wykonuje narzędzie, atomowo zużywając wymaganą zgodę."""
    tool = get_tool(name)

    if tool.requires_approval:
        if approval_repository is None:
            raise PermissionError(
                f"Narzędzie {name} wymaga repozytorium zatwierdzeń."
            )

        if (
            not isinstance(approval_request_id, int)
            or isinstance(approval_request_id, bool)
            or approval_request_id <= 0
        ):
            raise PermissionError(
                f"Narzędzie {name} wymaga poprawnego approval_request_id."
            )

        approval_repository.consume_approved_request(
            approval_request_id,
            tool_name=tool.name,
            arguments_digest=canonical_arguments_digest(arguments),
        )
    elif approval_request_id is not None:
        raise ValueError(
            "approval_request_id jest dozwolone wyłącznie dla narzędzi "
            "wymagających zatwierdzenia."
        )

    return tool.execute(**arguments)
