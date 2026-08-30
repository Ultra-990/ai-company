# Faza 2 — Trwała pamięć domenowa

## Zakres ukończony

- dodano interfejs `MemoryRepository`;
- dodano implementację `InMemoryMemoryRepository`;
- zintegrowano repozytorium z `DomainRegistry`;
- zaimplementowano operacje `save`, `get`, `list` i `delete`;
- dodano obsługę duplikatów identyfikatorów;
- dodano testy jednostkowe i integracyjne;
- zweryfikowano pełny zestaw testów projektu.

## Weryfikacja

```bash
pytest -q

