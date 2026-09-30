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
