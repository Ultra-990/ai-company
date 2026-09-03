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
