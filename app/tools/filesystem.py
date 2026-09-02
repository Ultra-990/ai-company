from __future__ import annotations

from pathlib import Path

from app.tools import permissions
from app.tools.permissions import ToolSecurityError


MAX_READ_SIZE = 1024 * 1024
MAX_WRITE_SIZE = 1024 * 1024
MAX_LIST_ITEMS = 500

# Pliki, których narzędzie nigdy nie może odczytywać ani modyfikować.
SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "authorized_keys",
    "credentials.txt",
}

# Zapis do kodu źródłowego i konfiguracji wymaga osobnego procesu/deploymentu.
PROTECTED_SUFFIXES = {
    ".py",
    ".pyi",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".ini",
    ".cfg",
    ".conf",
}


def _validate_project_file(
    relative_path: str,
    *,
    must_exist: bool = False,
    for_write: bool = False,
) -> Path:
    if not relative_path or not relative_path.strip():
        raise ToolSecurityError("Ścieżka pliku nie może być pusta.")

    candidate = Path(relative_path)

    if candidate.is_absolute():
        raise ToolSecurityError("Ścieżki absolutne są niedozwolone.")

    resolved = permissions.safe_project_path(relative_path)

    # Sprawdzenie po normalizacji blokuje np. `.env`, `foo/.env`
    # oraz ścieżki z przejściem przez katalog wrażliwy.
    if any(part in SENSITIVE_NAMES for part in resolved.parts):
        raise ToolSecurityError(
            "Dostęp do plików wrażliwych jest niedozwolony."
        )

    if resolved.name in SENSITIVE_NAMES:
        raise ToolSecurityError(
            "Dostęp do plików wrażliwych jest niedozwolony."
        )

    if permissions.is_ignored(resolved):
        raise ToolSecurityError(
            "Dostęp do ignorowanych katalogów lub plików jest niedozwolony."
        )

    if must_exist and not resolved.exists():
        raise ToolSecurityError("Plik nie istnieje.")

    if resolved.exists() and resolved.is_dir():
        raise ToolSecurityError("Wskazana ścieżka jest katalogiem.")

    if for_write and resolved.suffix.lower() in PROTECTED_SUFFIXES:
        raise ToolSecurityError(
            "Zapis do plików kodu i konfiguracji jest niedozwolony."
        )

    return resolved


def list_project_files(
    path: str = ".",
    *,
    recursive: bool = False,
    max_items: int = MAX_LIST_ITEMS,
) -> list[str]:
    """Bezpiecznie listuje pliki projektu bez ujawniania symlinków."""
    if (
        not isinstance(max_items, int)
        or isinstance(max_items, bool)
        or max_items <= 0
        or max_items > MAX_LIST_ITEMS
    ):
        raise ToolSecurityError(
            f"Limit max_items musi mieścić się w zakresie 1-{MAX_LIST_ITEMS}."
        )

    root = permissions.project_root()
    requested_path = root / Path(path)

    # Wykrycie symlinku przed resolve(), które może ukryć jego naturę.
    if requested_path.is_symlink():
        raise ToolSecurityError(
            "Nie można listować katalogu będącego dowiązaniem symbolicznym."
        )

    base_dir = permissions.safe_project_path(path)

    if not base_dir.is_dir():
        raise ToolSecurityError("Wskazana ścieżka nie jest katalogiem.")

    resolved_root = root.resolve()
    iterator = base_dir.rglob("*") if recursive else base_dir.iterdir()
    items: list[str] = []

    for entry in iterator:
        # Symlink może wskazywać wewnątrz albo poza projektem:
        # w obu przypadkach nie ujawniamy go na liście.
        if entry.is_symlink():
            continue

        if not entry.is_file():
            continue

        if permissions.is_ignored(entry):
            continue

        if any(part in SENSITIVE_NAMES for part in entry.parts):
            continue

        try:
            entry.resolve().relative_to(resolved_root)
        except ValueError:
            continue

        if len(items) >= max_items:
            raise ToolSecurityError(
                f"Lista plików przekracza limit {max_items} pozycji."
            )

        items.append(
            str(entry.relative_to(resolved_root)) if recursive else entry.name
        )

    return sorted(items)



def read_project_file(
    path: str,
    *,
    max_bytes: int | None = None,
) -> str:
    resolved = _validate_project_file(path, must_exist=True)

    limit = MAX_READ_SIZE if max_bytes is None else max_bytes

    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ToolSecurityError("Limit max_bytes musi być dodatnią liczbą całkowitą.")

    if resolved.stat().st_size > limit:
        raise ToolSecurityError(
            f"Plik przekracza limit {limit} bajtów."
        )

    try:
        with resolved.open("r", encoding="utf-8") as file:
            return file.read()
    except UnicodeDecodeError as exc:
        raise ToolSecurityError("Plik nie jest poprawnym tekstem UTF-8.") from exc


def write_project_file(path: str, content: str) -> dict[str, object]:
    if not isinstance(content, str):
        raise ToolSecurityError("Treść pliku musi być tekstem.")

    encoded_size = len(content.encode("utf-8"))

    if encoded_size > MAX_WRITE_SIZE:
        raise ToolSecurityError(
            f"Treść przekracza limit {MAX_WRITE_SIZE} bajtów."
        )

    resolved = _validate_project_file(path, for_write=True)

    # Nie tworzymy brakujących katalogów automatycznie. Zapobiega to
    # swobodnemu tworzeniu całych struktur katalogów przez narzędzie.
    if not resolved.parent.is_dir():
        raise ToolSecurityError(
            "Katalog docelowy nie istnieje."
        )


    resolved.write_text(content, encoding="utf-8")

    return {
        "path": str(resolved.relative_to(permissions.project_root())),
        "bytes_written": encoded_size,
    }
