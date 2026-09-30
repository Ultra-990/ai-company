# Atomowy przydział gotowych zadań

`TaskWorker.claim_next()` i wywołujący go orkiestrator pobierają najstarsze
zatwierdzone zadanie przez `TaskRepository.claim_next()`. Wybór i przejęcie
odbywają się w jednej krótkiej transakcji SQLite `BEGIN IMMEDIATE`.

Poprzednio dwóch wykonawców mogło odczytać to samo pierwsze zadanie.
Przegrany zwracał pusty wynik, nawet kiedy dalsze zadania były gotowe.
Teraz drugi wykonawca po zwolnieniu blokady odczytuje aktualną kolejkę
i przejmuje następne dostępne zadanie. Porządek pozostaje bez zmian:
`queued_at`, a przy równym czasie — identyfikator zadania.

Warunki przejęcia:

- status `pending`, zgoda `approved` i niepuste `queued_at`;
- brak delegacji zespołowej, która wymaga osobnego środowiska wykonania;
- pojedyncza zmiana stanu na `in_progress`, wpis próby i zdarzenie audytu
  zatwierdzone razem w tej samej transakcji.

Wyjątek podczas zapisu cofa całą transakcję i zwalnia blokadę. Błąd bazy
nie oznacza pustej kolejki: jest przekazywany wywołującemu bez automatycznego
ponawiania. Jawne `claim(task_id)` korzysta z tej samej kontroli i zapisu.
Blokada kończy się przed aktualizacją dokumentacji i wykonaniem zadania;
nie jest utrzymywana przez czas odpowiedzi modelu ani pracy runnera.

Zmiana dotyczy przydziału w istniejącej kolejce. Nie uruchamia nowych
wykonawców, nie zwiększa limitu jednoczesnych inferencji, nie nadaje zgód
na zasoby i nie zmienia osobnej kolejki symulacyjnej modeli. Przejęcie nie
jest odbiorem wyniku. Awaria procesu po udanym przejęciu nadal wymaga
rozpoznania istniejącej próby; nie wolno automatycznie uruchamiać jej ponownie.

Testy korzystają wyłącznie z tymczasowych baz i osobnych połączeń. Obejmują
trzech równoczesnych wykonawców, kolejkę jednego i trzech zadań, kontrolowany
wyścig dwóch transakcji, kolejność FIFO, pomijanie nieuprawnionych zadań,
pojedynczy audyt/próbę i wycofanie wszystkich zapisów po wymuszonym błędzie.
Nie wykonują modeli, kodu produktu ani kontenerów.

## Diagnostyka niezakończonych prób

Właścicielski `GET /api/tasks/{task_id}/execution-diagnostics` pokazuje
metadane ostatniej próby, liczbę otwartych prób i wyników oczekujących
na odbiór oraz wiek najstarszej otwartej próby. Domyślny próg uwagi wynosi
900 sekund; parametr `attention_after_seconds` przyjmuje 1–604800 sekund.
Odpowiedź ma `Cache-Control: no-store` i nie zawiera treści wyników ani
komunikatów błędów wykonawcy.

To zwykła kolejka zadań, bez heartbeat. `worker_liveness: unknown` oraz
`failure_confirmed: false` są jawne także po przekroczeniu progu. Sam wiek
próby nie rozstrzyga, czy wykonawca pracuje, zawiesił się, zakończył się bez
zapisu lub utracił połączenie. `Task.updated_at` nie jest używany jako dowód
aktywności procesu. Próg jest wskazówką do sprawdzenia, a nie czasem
ważności uprawniającym do ponownego wykonania.

Diagnostyka rozróżnia oczekiwanie na potwierdzenie pracy, wynik oczekujący
na odbiór, brak otwartej próby oraz niespójne rekordy. Sygnalizuje m.in.
kilka otwartych prób, starszą próbę pozostawioną otwartą po nowej, konflikt
statusu zadania i próby oraz błędne czasy. Przyszły start nie jest zamieniany
na wiek zero. Czasy SQLite pozbawione strefy są interpretowane jako UTC,
zgodnie z ich zapisem. Uszkodzony zapis czasu uniemożliwiający odczyt daje
503 zamiast pozornie poprawnej diagnozy.

Wszystkie zapytania korzystają z jednego jawnego snapshotu SQLite. Test
z drugim połączeniem kończącym próbę między odczytami potwierdza, że odpowiedź
nie miesza różnych chwil. Endpoint niczego nie zapisuje, nie bada PID,
nie zmienia stanu zadania i nie ponawia wykonania. Również status ostatniej
próby `completed` nie oznacza automatycznej oceny jej jakości; zwracany jest
osobno zapisany `verification_status`.
