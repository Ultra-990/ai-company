# Instrukcja → wynik → odbiór

Stan: 2026-09-12. Działający **ręczny obieg**, bez uruchamiania modeli,
kodów, kontenerów ani usług zewnętrznych. Nie jest to jeszcze autonomiczna
praca agentów. Korzysta z istniejących delegacji, zadań, prób i artefaktów.

2026-09-13: dostępna jest również [kolejka próbna lokalnego modelu](LOCAL_MODEL_QUEUE.md).
Instrukcję można sprawdzić ze stałą atrapą odpowiedzi, bez inferencji.
Wynik tej próby nie trafia do odbioru prawdziwego zadania.

## Obsługa właściciela

1. W `/os/work` połącz się tokenem właściciela, wybierz zlecenie i przydziel
   kierownika oraz agentów. Jeśli zespołów nie ma, wcześniej je przygotuj.
2. Przy pierwszym gotowym etapie kliknij **Przygotuj instrukcję**. Otworzy się
   zadanie z rolą, kierownikiem, kontrolerem, zakresem, kryterium i ograniczeniami.
   Możesz zaznaczyć tekst lub pobrać JSON. To nie wysyła instrukcji do modelu.
3. Wykonaj pracę samodzielnie lub przez uprawnionego wykonawcę poza systemem.
   Nie wysyłaj danych klienta ani sekretów do niezatwierdzonych usług.
   Przycisk **Pokaż prompt dla Qwen / lokalnego modelu** zamienia instrukcję
   w tekst gotowy do skopiowania. Zawiera rolę, zakres, kryterium odbioru,
   odebrany poprzedni etap i uwagi do odrzuconej wersji. Nie wywołuje modelu.
   Wywołanie modelu na tym hoście wymaga uzgodnionego budżetu zasobów Vast.ai.
4. Wklej rzeczywisty rezultat (do 32000 znaków) oraz jego pochodzenie (1000).
   **Zapisz wynik do odbioru** zapisuje próbę jako `owner-import`, a nie jako
   udowodnione wykonanie przypisanego agenta. Tożsamość źródła jest deklaracją.
5. Kliknij **Odbierz wynik**. Sprawdź konkretną wersję, podaj uzasadnienie
   i dowody albo konkretne braki. Akceptacja wykorzystuje dotychczasowy odbiór
   właściciela i kończy zadanie. Sam import nie podnosi jego procentu.
6. Akceptacja odblokowuje przygotowanie instrukcji kolejnego etapu, z treścią
   odebranego poprzednika. Nie uruchamia go ani nie zamyka całego projektu.
7. Odrzucenie blokuje zadanie. Nowa instrukcja zawiera uwagi i poprzedni
   rezultat do poprawy. Kolejny import tworzy nową próbę; historia pozostaje.

Zamknięcie okna czyści niezapisany formularz; instrukcja pozostaje w artefaktach.
Wylogowanie usuwa token i teksty z pamięci widoku. Nie przechowujemy ich
w localStorage. Odświeżanie listy nie nadpisuje otwartego formularza odbioru.

## API i integralność

- `POST /api/tasks/{id}/agent-packet` — przygotuj/reużyj instrukcję.
- `GET /api/tasks/{id}/agent-packets/{packet_id}` — odczytaj wersję.
- `GET /api/tasks/{id}/agent-packets/{packet_id}/prompt` — aktualna instrukcja
  jako `messages` (system/user) i `text`, związana z ID i sumą paczki.
  Odczyt owner-only, no-store, bez zapisu, sieci, inferencji i treningu.
  Nieaktualny zakres lub stan zadania daje 409. Wersja promptu
  `local-handoff-prompt.v1`, maksymalny wynik 32000 znaków; brak cichego cięcia.
- `POST /api/tasks/{id}/agent-results` — przyjmij wynik wraz z
  `packet_id`, `packet_checksum`, `result_content`, `source_note`.
- Istniejące `GET/POST /api/tasks/{id}/review` — odbiór konkretnej próby i sumy.

Wszystkie wymagają Owner; worker/klient nie otrzymują dostępu. Instrukcja jest
artefaktem PLAN z SHA-256 i profilem `delivery-instructions.v1`; kontekst max
256 KiB, bez cichego obcinania. Odrzucona i poprzedzająca wersja są kontrolowane.

Import przed zapisem ponownie sprawdza delegację, dział, aktorów, zakres,
poprzednika, stan zadania oraz sumę całego aktualnego kontekstu. Zapisy próby,
potwierdzenia i audytu są transakcyjne. Jedna wersja instrukcji przyjmuje jeden
wynik: identyczne ponowienie zwraca tę samą próbę, inny wynik/źródło daje 409.
Po niepewnym zapisie odśwież szczegóły; nie twórz fikcyjnego odbioru dla retry.

Kolejka automatyczna nadal wyklucza delegowane zadania. Import nie zmienia
zgody ani `queued_at`. Tekst wyniku jest wyświetlany w textarea, nie jako HTML.
Wynik nie jest paczką plików — te nadal mają osobny kontrolowany mechanizm.

## Granice

Instrukcja jest materiałem dla wykonawcy, nie zabezpieczeniem obcego modelu.
Nie uruchomiono przypisanego kontrolera ani testów; końcowa decyzja to jawny
odbiór właściciela. Podłączenie inferencji i runnera wymaga osobnej polityki
zasobów uwzględniającej Vast.ai. Produkcyjne zlecenia klientów nie są testowane
poprzez zmianę ich prawdziwych statusów.

## Lokalny model — stan 2026-09-13

Odczyt listy lokalnej Ollamy potwierdził tag `qwen3.8:27b` (17 GB).
To nazwa instalacji, nie niezależna weryfikacja pochodzenia lub jakości modelu.
Nie uruchomiono generowania i nie zmieniono wag. W projekcie istnieją
LLMTaskOperation i klient zgodnego HTTP API, ale automatyczny wykonawca
delegowanych zadań z kontrolą budżetu i izolowanym runnerem pozostaje do
połączenia oraz przetestowania. Eksport promptu nie jest tą integracją.
