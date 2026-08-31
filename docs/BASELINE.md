# Wersja bazowa projektu

## Stan bazowy

- Gałąź: `refactor/task-stage-contract`
- Commit bazowy: `96eab70`
- Zakres: audyt modeli domenowych, publicznego API `Brain` i kontraktów `Task`/`ApprovalRequest`
- Testy bazowe: 364 przechodzące
- Kompilacja: `app` i `scripts` przechodzą

## Znane ograniczenia

- Istnieją równoległe modele trwałe SQLAlchemy i modele kontekstu jako dataclasses.
- `BrainDecision` oraz `context_manager.Decision` mają różne odpowiedzialności.
- Brak kompletnego katalogu `app/schemas`.
- `docs/STATUS.md` może być automatycznie aktualizowany i nie powinien być traktowany jako ręcznie stabilny zapis statusu.
- Kontrakty domenowe nie obejmują jeszcze wszystkich wymaganych encji i przejść stanów.

## Bezpieczeństwo

Centralny system polityk, poziomy autonomii A0–A3, kolejka zgód i pełny audyt działań nie są jeszcze ukończone. Do czasu ich wdrożenia działania poza istniejącymi ograniczeniami muszą być traktowane jako wymagające ręcznej kontroli.

## Plan

Po tym punkcie rozpoczyna się Faza 1: ujednolicanie kontraktów domenowych.
