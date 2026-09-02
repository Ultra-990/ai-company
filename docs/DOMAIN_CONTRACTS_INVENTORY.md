# Inwentaryzacja kontraktów domenowych

## Obecne lokalizacje

| Kontrakt | Aktualna lokalizacja | Stan |
|---|---|---|
| Task | `app/models/task.py` | istnieje, powiązany z bazą danych |
| Task kontekstowy | `app/brain/context_manager.py` | istnieje, wymaga decyzji o konsolidacji |
| Agent | `app/brain/context_manager.py` | istnieje jako `AgentProfile` |
| Tool | `app/tools/base.py` | istnieje |
| ApprovalRequest | `app/brain/context_manager.py` | istnieje |
| Decision | `app/brain/context_manager.py` | istnieje |
| AuditEvent | `app/models/audit.py` | istnieje jako model trwały |
| MemoryRecord | brak formalnego modelu | do zaprojektowania |
| Department | brak formalnego modelu | do zaprojektowania |

## Zasada

Nie tworzyć duplikatów modeli. Najpierw ustalić źródło prawdy dla każdego kontraktu, a dopiero potem przenosić lub wystawiać modele przez `app.domain`.

## Priorytet

1. Ustalić relację między `app.models.task.Task` i `app.brain.context_manager.Task`.
2. Ustalić, czy `AgentProfile` pozostaje nazwą publiczną, czy zostanie zastąpiony przez `Agent`.
3. Dodać `Department`.
4. Dodać `MemoryRecord`.
5. Przygotować stabilne eksporty z `app.domain.contracts`.
