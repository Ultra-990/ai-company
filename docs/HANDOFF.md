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
- testy endpointów i decyzji bezpieczeństwa.

Ostatni potwierdzony wynik testów:

    9 passed, 1 warning

Ostrzeżenie pochodzi z zależności FastAPI/Starlette TestClient i nie powoduje
niepowodzenia testów.

Punkt kontrolny:

    v0.1-safety-baseline

## Następne zadanie

Zaimplementować trwały dziennik audytowy SQLite.

Plan:

1. Najpierw zbadać aktualny kod i konfigurację.
2. Wykorzystać istniejący SQLAlchemy, jeśli jest poprawnie zainstalowany.
3. Wydzielić konfigurację bazy, model i warstwę repozytorium.
4. Zapisywać decyzje bramki:
   - `allowed`,
   - `blocked`,
   - `approval_required`,
   - odrzucenie nieznanej operacji.
5. Nie zapisywać sekretów ani pełnych danych wrażliwych.
6. Dodać ograniczony endpoint odczytu dziennika.
7. Testy nie mogą zanieczyszczać produkcyjnej/lokalnej bazy użytkownika.
   Powinny korzystać z izolowanej bazy testowej lub jawnego nadpisania
   zależności.
8. Zachować zgodność ze wszystkimi istniejącymi testami.

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
