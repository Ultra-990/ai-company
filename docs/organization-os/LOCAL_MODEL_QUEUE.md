# Kolejka lokalnego modelu — próba bez inferencji

Stan: 2026-09-13. Wynajem zakończony. Ta kolejka nadal jest wyłącznie próbna;
rzeczywiste generowanie ma osobny [obieg lokalnej inferencji](LOCAL_INFERENCE.md).

## Co można sprawdzić teraz

1. Otwórz `/os/work`, połącz się tokenem właściciela.
2. Wybierz projekt z przydzielonym zespołem i gotowe zadanie.
3. **Przygotuj instrukcję → Dodaj instrukcję do kolejki próbnej**.
4. Zamknij instrukcję. W sekcji **Kolejka lokalnego modelu** wybierz
   **Pokaż kolejkę próbną** lub **Symuluj jedną oczekującą pozycję**.
5. Obejrzyj wynik próby. Jest jednoznacznie oznaczony jako SYMULACJA,
   nie rezultat Qwen, nie wykonanie zadania i nie dowód testów produktu.

Nie wymaga to osobnego tokenu klienta ani uruchamiania Ollamy. Odczyt listy
i pojedyncza próba są ręczne; nie dodano procesu pracującego w tle.
Samo dodanie do kolejki niczego nie uruchamia. Lista ma paginację po 30 wpisów.

## Dane i zabezpieczenia

- Addytywna tabela `local_model_jobs` tworzona przez istniejący start aplikacji.
- Instrukcja powiązana z Task, artefaktem i SHA-256. Odczyt i ponowna
  walidacja przed rezerwacją oraz przed zapisaniem odpowiedzi.
- UUID żądania chroni retry. Jedna wersja instrukcji ma jedną próbę w tej
  kolejce; ponowne dodanie zwraca zapisany wynik/status, nie wykonuje retry.
- Do 50 pozycji oczekujących/trwających; FIFO, jeden slot globalny.
  Rezerwacja pod BEGIN IMMEDIATE. Brak blokady zapisu bazy podczas odpowiedzi.
- Wygenerowany błąd: stały kod, bez treści wyjątku, promptu lub sekretów.
  Obsługa zgłoszonego TimeoutError, pustego lub zbyt dużego wyniku, NUL/UTF-8.
  Maksymalnie 32000 znaków wyniku, bez cichego obcinania i auto-retry.
- `queued → running → simulation_complete / failed / stale`;
  anulowanie tylko `queued → cancelled`. Nie kasuje danych historii.
- Po awarii pozostawiającej `running` kolejka nie odzyskuje slotu automatycznie:
  potrzebna diagnostyka i potwierdzenie końca własnej próby. Sama data nie jest
  dowodem zakończenia procesu; nie wznawiamy go z drugiej sesji.
- Wyniki prób pozostają w kolejce, nie są importowane do TaskAttempt/Artifact.
  Nie zmieniamy Task.status/progress/approval/queued_at. Nie odblokowują następcy.
- Wszystkie endpointy Owner-only; brak ich w osobnym `app.client_main`.
  API nie przyjmuje modelu, adresu serwera, narzędzi ani przełącznika live.

## API

- `GET /api/local-model-queue?before=...` — stan i historia, `live_enabled:false`.
- `POST /api/local-model-queue` — `request_id`, `task_id`, `packet_id`, `packet_checksum`.
- `POST /api/local-model-queue/{id}/cancel` — anulowanie pozycji oczekującej.
- `POST /api/local-model-queue/simulate-next` — najwyżej jedna pozycja FIFO;
  stała atrapa `FixtureProvider`, bez HTTP, shell, kodu i modeli.

## Co pozostaje przed rzeczywistym wykonaniem

To przygotowanie cyklu kolejki i kontraktu adaptera, **nie ukończone połączenie
wykonawcze z Qwen**. Stałej atrapy nie wolno traktować jako modelu. Flaga
`simulation_only` jest wewnętrznym kontraktem kodu, nie sandboxem obcego pluginu.

Po potwierdzeniu zwolnienia zasobów: uzgodnienie CPU/RAM/GPU i limitu
czasu/kontekstu/tokenu, kontrolowany adapter do lokalnego serwera, rzeczywisty
deadline i bezpieczne przerwanie własnego wywołania, zapis pochodzenia oraz
wersjonowany wynik do odbioru. Obsługa wyjątku TimeoutError nie jest jeszcze
wymuszaniem deadline'u na dowolnym providerze. Osobno izolacja wykonywania kodu.
Prób symulacyjnych nie promujemy automatycznie do rzeczywistych zleceń.
