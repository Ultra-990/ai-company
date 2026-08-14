# Przekazanie projektu AI Company

## Cel projektu

Budowany jest lokalny system AI przypominający strukturę firmy:

Właściciel -> Mózg -> Kierownicy -> Mrówki

System ma docelowo realizować projekty i generować przychody, ale rozwijany
jest etapami z pierwszeństwem bezpieczeństwa, kontroli Właściciela, audytu
oraz testów.

## Instrukcja dla kolejnego asystenta

Przed zaproponowaniem zmian:

1. Przeczytaj:
   - `docs/CONSTITUTION.md`
   - `docs/PROJECT_STATE.md`
   - `docs/HANDOFF.md`
2. Sprawdź rzeczywistą strukturę repozytorium.
3. Przeczytaj aktualny kod, szczególnie:
   - `app/main.py`
   - `app/api/system.py`
   - moduły w `app/core/`
   - `config/settings.yaml`
   - testy w `tests/`
4. Uruchom istniejące testy.
5. Nie zakładaj istnienia plików lub funkcji bez ich sprawdzenia.
6. Dopasuj implementację do faktycznego kodu.
7. Nie osłabiaj bezpiecznych ustawień domyślnych.
8. Nie uruchamiaj płatnych API, publikowania, płatności ani innych działań
   zewnętrznych bez jawnej zgody Właściciela.
9. Każdy etap zakończ:
   - kompilacją lub kontrolą składni,
   - testami,
   - `git diff --check`,
   - przeglądem plików dodawanych do Git,
   - commitem,
   - aktualizacją `docs/PROJECT_STATE.md`.

## Aktualny stan

Działają:

- FastAPI,
- konfiguracja YAML,
- walidacja ustawień,
- status systemu,
- bramka bezpieczeństwa,
- trwały dziennik audytowy SQLite,
- model `AuditEvent`,
- repozytorium zapisu i odczytu zdarzeń audytowych,
- rejestrowanie decyzji bramki bezpieczeństwa:
  - `allowed`,
  - `blocked`,
  - `approval_required`,
  - odrzucenie nieznanej operacji,
- ograniczony endpoint odczytu dziennika pod adresem
  `/api/audit/events`,
- testy endpointów, decyzji bezpieczeństwa i dziennika audytowego.

Dziennik audytowy nie zapisuje sekretów ani pełnych danych wrażliwych.
Testy audytu korzystają z izolowanej bazy testowej i nie zanieczyszczają
produkcyjnej ani lokalnej bazy użytkownika.

Ostatni potwierdzony wynik testów:

    50 passed, 1 warning

Ostrzeżenie pochodzi z zależności FastAPI/Starlette TestClient i nie powoduje
niepowodzenia testów.

Punkt kontrolny:

    v0.1-safety-baseline

## Następne zadanie

Zaimplementować system zatwierdzania operacji przez Właściciela.

Plan:

1. Najpierw zbadać aktualny model zadań, bramkę bezpieczeństwa i dziennik
   audytowy.
2. Zdefiniować jawny model żądania zatwierdzenia operacji.
3. Określić stany zatwierdzenia, co najmniej:
   - `pending`,
   - `approved`,
   - `rejected`,
   - `expired`.
4. Zapisywać w dzienniku audytowym utworzenie, zatwierdzenie, odrzucenie
   i wygaśnięcie żądania.
5. Nie wykonywać operacji wymagających zatwierdzenia przed uzyskaniem
   jednoznacznej decyzji Właściciela.
6. Nie zapisywać sekretów ani pełnych danych wrażliwych w żądaniach,
   odpowiedziach ani dzienniku.
7. Udostępnić ograniczone endpointy do przeglądania i rozstrzygania
   oczekujących żądań.
8. Zapewnić jednoznaczną autoryzację decyzji Właściciela.
9. Dodać testy dla wszystkich stanów i przejść zatwierdzenia.
10. Testy muszą korzystać z izolowanych zasobów i nie mogą zanieczyszczać
    produkcyjnej ani lokalnej bazy użytkownika.
11. Zachować zgodność ze wszystkimi istniejącymi testami i nie osłabiać
    obecnych reguł bramki bezpieczeństwa.

## Polecenia diagnostyczne

Asystent powinien poprosić użytkownika o wykonanie albo przeanalizować wyniki:

    pwd
    git status --short
    git log --oneline --decorate -10
    find app config tests docs -maxdepth 4 -type f
    pytest -q

Przed przygotowaniem kodu audytu należy przeczytać odpowiednie pliki za pomocą
`sed`, `cat` albo podobnych bezpiecznych poleceń.

## Ważne ograniczenia

- Agenci pozostają wyłączeni.
- Finanse pozostają w trybie symulacji.
- Działania finansowe, publikowanie i działania zewnętrzne pozostają
  zablokowane.
- Zmiany systemowe i trwałej pamięci wymagają zatwierdzenia.
- Emergency Stop musi mieć nadrzędny priorytet, gdy zostanie wdrożony.
- Sekrety nie mogą trafić do repozytorium.
- Nie wolno pomijać istniejącej bramki bezpieczeństwa.

## Oczekiwany styl współpracy

Podawaj kompletne, możliwe do skopiowania polecenia. Po każdym większym kroku
wymagaj jednego zbiorczego wyniku kontroli zamiast wielu drobnych odpowiedzi.
Nie przyspieszaj przez pomijanie testów; przyspieszaj przez realizowanie
większych, zamkniętych etapów.
