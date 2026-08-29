# Faza 1 — Kontrakty domenowe

## Cel

Zdefiniowanie typowanych i stabilnych obiektów domenowych dla systemu AI Company.

## Zasady

1. Kontrakty nie wykonują operacji plikowych ani sieciowych.
2. Kontrakty nie zależą od FastAPI ani konkretnego dostawcy LLM.
3. Dane wejściowe są walidowane.
4. Każdy model posiada testy jednostkowe.
5. Zmiany kontraktów wymagają aktualizacji dokumentacji i testów.
6. Operacje wysokiego ryzyka są reprezentowane przez jawny model zgody.

## Zakres pierwszej iteracji

- Task
- Agent
- Department
- Tool
- ApprovalRequest
- AuditEvent
- Decision
- MemoryRecord

## Kryterium ukończenia

- wszystkie modele mają jawne pola i typy,
- walidacja odrzuca niepoprawne dane,
- modele można serializować,
- istnieją testy jednostkowe,
- istnieją testy kompatybilności z executorami.
