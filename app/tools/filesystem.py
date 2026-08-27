from __future__ import annotations

from pathlib import Path

from .audit import audit_tool_call
from .permissions import (
    ToolSecurityError,
    is_ignored,
    project_root,
    safe_project_path,
)


MAX_FILE_SIZE = 1_048_576  # 1 MiB


def read_project_file(path: str, max_bytes: int = MAX_FILE_SIZE) -> str:
    arguments = {"path": path, "max_bytes": max_bytes}

    try:
        if max_bytes <= 0 or max_bytes > MAX_FILE_SIZE:
            raise ToolSecurityError(
                f"Limit musi mieścić się w zakresie 1-{MAX_FILE_SIZE} bajtów."
            )

        file_path = safe_project_path(path, must_be_file=True)

        if is_ignored(file_path.relative_to(project_root())):
            raise ToolSecurityError("Odczyt tej ścieżki jest niedozwolony.")

        size = file_path.stat().st_size
        if size > max_bytes:
            raise ToolSecurityError(
                f"Plik jest za duży: {size} bajtów, limit: {max_bytes}."
            )

        content = file_path.read_text(encoding="utf-8")
        audit_tool_call(
            "read_project_file",
            status="success",
            arguments=arguments,
        )
        return content

    except Exception as exc:
        audit_tool_call(
            "read_project_file",
            status="denied",
            arguments=arguments,
            error=str(exc),
        )
        raise


def list_project_files(
    path: str = ".",
    recursive: bool = False,
) -> list[str]:
    arguments = {"path": path, "recursive": recursive}

    try:
        directory = safe_project_path(path)

        if not directory.is_dir():
            raise ToolSecurityError("Wskazana ścieżka nie jest katalogiem.")

        iterator = directory.rglob("*") if recursive else directory.glob("*")
        root = project_root()

        result = sorted(
            str(item.relative_to(root))
            for item in iterator
            if item.is_file()
            and not is_ignored(item.relative_to(root))
        )

        audit_tool_call(
            "list_project_files",
            status="success",
            arguments=arguments,
        )
        return result

    except Exception as exc:
        audit_tool_call(
            "list_project_files",
            status="denied",
            arguments=arguments,
            error=str(exc),
        )
        raise
