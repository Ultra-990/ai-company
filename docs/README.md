# Dokumentacja projektu

## Cel

AI Company jest rozwijanym systemem zarządzania firmą technologiczną,
jej produktami, zleceniami i agentami wykonawczymi.

Docelowy zakres produktów, sieć agentów, architektura Linux i zasady odbioru
są opisane w [architekturze docelowej](ARCHITECTURE.md). Dokument rozróżnia
planowane zdolności od stanu istniejącego kodu.

Przebieg implementacji i wyniki kontroli: [dziennik prac](WORK_LOG.md).
Testy projektu uruchamiaj z jego środowiska: `.venv/bin/pytest -q`.
Po `source .venv/bin/activate` równoważne jest `pytest -q`.
Domyślnie zbierane są testy z `tests/`; materiały ćwiczeń w `.pytest_cache`
nie stanowią samodzielnego zestawu testowego projektu.
Instrukcje dla właściciela i klienta: [Centrum pomocy](organization-os/HELP_CENTER.md).
Znajdowanie paneli i funkcji: [Wyszukiwarka nawigacji](organization-os/NAVIGATION_SEARCH.md).
Jedno logowanie do paneli: [Sesja właściciela](organization-os/OWNER_SESSION.md).
Priorytet realizacji: [Zlecenia Upwork i kontrolowana analiza Qwen](organization-os/UPWORK.md).
Przekazanie gotowej wersji: [Instrukcje klienta PL/EN i szkic wiadomości](organization-os/DELIVERY_HANDOFF.md).
Wymagania a testy: [Weryfikacja wymagań konkretnej paczki](organization-os/REQUIREMENT_CHECKS.md).
Automatyczne przykłady: [Niezmienny plan HTTP i pętla poprawek](organization-os/AUTOMATIC_ACCEPTANCE.md) — wykonanie wyłączone do pilota.
Zasady bezpiecznej pracy i paczki projektów:
[środowisko wykonawcze](organization-os/EXECUTION.md).

Aktualny pulpit i operacyjne funkcje działów: [Centrum dowodzenia](organization-os/COMMAND_CENTER.md).
Poprzedni pulpit, motywy i wydajność: [Studio](organization-os/STUDIO.md).
Scena z przewijaniem i rzeczywistą geometrią 3D: [Spatial lab](organization-os/SPATIAL.md).
Publikacja informacji dla klienta i granice wdrożenia: [Panel klienta](organization-os/CLIENT_PORTAL.md).
Przyjmowanie zleceń i przygotowanie pierwszych plików: [Centrum realizacji](organization-os/WORKBENCH.md).
Struktura wykonawcza i przydział zadań: [Kierownicy i zespoły agentów](organization-os/AGENT_TEAMS.md).

Kontrola lokalnego modelu i decyzje o strojeniu: [Jakość Qwena](organization-os/MODEL_QUALITY.md).
Plan osobnego adaptera, danych i testów: [Dostrojenie Qwena](organization-os/QWEN_TRAINING.md).
Rzeczywiste tekstowe wykonanie Qwen na lokalnym GPU: [Lokalna inferencja](organization-os/LOCAL_INFERENCE.md).
Generowanie źródeł, testy w kontenerze i wydania: [Fabryka aplikacji](organization-os/APPLICATION_FACTORY.md).
Próba strony usługowej z Qwenem, poprawkami i ZIP: [Upwork web pilot](organization-os/UPWORK_WEB_PILOT.md).
Kontrola źródeł i raporty związane z wersją: [Kontrola paczek](organization-os/PACKAGE_CHECKS.md).
Oglądanie statycznych stron bez ZIP: [Podgląd paczek](organization-os/PREVIEW.md).
Przygotowana partycja i katalogi poza danymi Dockera: [Przestrzeń robocza](organization-os/STORAGE.md).

## Główne elementy

- Task API
- Panel postępu
- Baza SQLite
- System etapów zadań
- Automatyczna dokumentacja statusu
- System agentów
- Audyt i bezpieczeństwo

## Dostępne widoki

[Wspólne palety, powrót do pulpitu i obsługa okien](organization-os/APPEARANCE.md).

- `/health` — kontrola działania aplikacji
- `/os` — Centrum dowodzenia: przegląd, działy, realizacja i decyzje
- `/os/legacy` — zachowany poprzedni pulpit
- `/os/spatial` — przestrzenna nawigacja przez 12 działów i katalog
- `/os/review` — odbiór konkretnego zadania i pliki
- `/os/build` — izolowane testy aplikacji Python, raporty i wydania ZIP
- `/os/publishing` — publikacje, workflow i kody dostępu klienta
- `/os/work` — formularz zlecenia, projekt, zadania i pobieranie szkieletu strony
- `/api/organization-os/tree` — struktura firmy i zależności
- `/progress` — panel postępu
- `/api/tasks` — API zadań
- `/api/progress` — dane postępu
