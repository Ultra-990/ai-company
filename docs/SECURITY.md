# Bezpieczeństwo — AI Company

## Zasady

1. Wszystkie pliki wrażliwe (.env, klucze, credentials) są zablokowane w SENSITIVE_NAMES.
2. Zapis do plików kodu/konfiguracji (.py, .yaml, .json) wymaga osobnego procesu.
3. Symlinki wskazujące poza projekt są zablokowane (resolve + relative_to).
4. Tool calling ma allowlist: tylko read_project_file i list_project_files.
5. write_project_file wymaga approved=True (mechanizm approval).
6. Audit log maskuje sekrety (redact_value).
7. Limit rozmiaru: 1 MB na odczyt/zapis.
8. Nie tworzymy katalogów automatycznie przy zapisie.

## Warstwy ochrony

| Warstwa | Plik | Co blokuje |
|---------|------|------------|
| 1 | permissions.py | absolute paths, traversal, ignored dirs |
| 2 | filesystem.py | sensitive names, protected suffixes, size |
| 3 | registry.py | approval required for write |
| 4 | tool_calling.py | allowlist (write_project_file NIE jest w liście) |
| 5 | audit.py | redaction secrets in logs |

## Testy

- tests/test_symlink_security.py — symlink outside/inside
- tests/test_tools_hardening.py — traversal, sensitive, size, approval
- tests/test_tool_calling.py — allowlist, limits, parse
- tests/test_audit_log_hardening.py — redaction
