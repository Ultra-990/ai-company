# Stan projektu AI Company

## Aktualny etap

Fundament aplikacji, konfiguracja oraz bramka bezpieczeństwa są gotowe.
Następnym etapem jest trwały dziennik audytowy SQLite.

## Zrealizowane elementy

- lokalne środowisko wirtualne Python,
- repozytorium Git na gałęzi `main`,
- aplikacja FastAPI,
- konfiguracja YAML z walidacją,
- Konstytucja Systemu v1.0,
- podstawowa bramka bezpieczeństwa,
- endpoint statusu systemu,
- endpoint kontroli operacji,
- bezpieczne ustawienia domyślne,
- automatyczne testy API i bezpieczeństwa,
- punkt kontrolny Git.
- model AuditEvent,
- repozytorium zapisu i odczytu audytu,
- rejestrowanie decyzji bramki bezpieczeństwa,
- endpoint /api/audit/events,
- izolowane testy audytu;
- Ostatni potwierdzony wynik — 50 passed, 1 warning;
- Najbliższy etap — wybierz kolejny rzeczywisty element roadmapy, np. system zatwierdzeń Właściciela;
- usuń dziennik audytowy z listy elementów jeszcze niezaimplementowanych.


## Aktualne zasady bezpieczeństwa

- agenci są domyślnie wyłączeni,
- finanse działają w trybie symulacji,
- działania zewnętrzne są zablokowane,
- działania finansowe są zablokowane,
- publikowanie jest zablokowane,
- zmiany systemowe wymagają zatwierdzenia,
- trwałe zmiany pamięci wymagają zatwierdzenia,
- operacje tylko do odczytu są dozwolone,
- znaczące operacje docelowo muszą być rejestrowane.

## Testy

Polecenie uruchamiające testy:

    pytest -q

Ostatni potwierdzony wynik:

    9 passed, 1 warning

Ostrzeżenie dotyczy wycofywanej integracji `httpx` z
`starlette.testclient`. Nie wpływa obecnie na poprawność testów.
Nie należy instalować `httpx2` bez wcześniejszej kontroli zgodności
wersji FastAPI, Starlette i HTTPX.

## Git

Potwierdzony commit testów:

    773f8da Dodanie testów API i bramki bezpieczeństwa

Punkt kontrolny:

    v0.1-safety-baseline

Tag `v0.1-safety-baseline` wskazuje commit `773f8da`.

## Najbliższy etap

Implementacja trwałego dziennika audytowego SQLite:

1. konfiguracja połączenia z bazą,
2. model wpisu audytowego,
3. inicjalizacja tabel,
4. warstwa zapisu i odczytu zdarzeń,
5. rejestrowanie decyzji bramki bezpieczeństwa,
6. endpoint odczytu dziennika,
7. testy wykorzystujące izolowaną bazę,
8. aktualizacja dokumentacji i commit.

## Elementy jeszcze niezaimplementowane

- trwały dziennik audytowy,
- system zatwierdzeń Właściciela,
- trwały stan Emergency Stop,
- modele agentów,
- Mózg, Kierownicy i Mrówki,
- kolejka zadań,
- pamięć agentów,
- obsługa projektów,
- finanse symulacyjne,
- panel internetowy,
- integracje z modelami AI,
- działania zewnętrzne.

## Zasady dalszej pracy

- nie pomijać testów bezpieczeństwa,
- nie umieszczać sekretów ani plików `.env` w Git,
- nie włączać działań zewnętrznych ani finansowych,
- każdy zamknięty etap kończyć testami i commitem,
- przed większą zmianą sprawdzić aktualną strukturę kodu,
- aktualizować ten dokument po każdym kamieniu milowym.
