from __future__ import annotations

from pathlib import Path


IGNORED_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
}

IGNORED_SUFFIXES = {".pyc", ".pyo"}


class ToolSecurityError(ValueError):
    """Raised when a tool request violates filesystem restrictions."""


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def safe_project_path(relative_path: str, *, must_be_file: bool = False) -> Path:
    if not relative_path:
        relative_path = "."

    candidate = Path(relative_path)

    if candidate.is_absolute():
        raise ToolSecurityError("Ścieżki absolutne są niedozwolone.")

    root = project_root()
    resolved = (root / candidate).resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ToolSecurityError(
            "Ścieżka wychodzi poza katalog projektu."
        ) from exc

    if must_be_file and not resolved.is_file():
        raise ToolSecurityError("Wskazana ścieżka nie jest zwykłym plikiem.")

    return resolved


def is_ignored(path: Path) -> bool:
    return (
        any(part in IGNORED_NAMES for part in path.parts)
        or path.suffix in IGNORED_SUFFIXES
    )
