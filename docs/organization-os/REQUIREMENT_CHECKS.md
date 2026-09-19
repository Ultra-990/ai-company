# Weryfikacja wymagań konkretnej wersji

## Cel i granice

Wymagania zlecenia (`WorkOrder.brief.acceptance_criteria`) są teraz powiązane
z wersjonowaną paczką źródeł i obserwacjami właściciela. Widok nie uznaje
zaliczonego profilu testów za dowód spełnienia wszystkich wymagań.

Ten etap jest rejestrem **ręcznej weryfikacji**, nie nowym automatycznym testerem.
Opcjonalne wskazanie raportu oznacza powiązanie dowodu, nie sprawdzenie, czy
test faktycznie pokrywa dane kryterium. Osobno dodano [deklaratywne przykłady
HTTP](AUTOMATIC_ACCEPTANCE.md), których wykonanie pozostaje wyłączone na czas
wynajmu i do rzeczywistego pilota. Nie zmienia się postęp zadania/projektu,
odbiór klienta, status publikacji ani obecna bramka wydania. Pełne potwierdzenie
ręczne nie zastępuje kontroli wydania ani niezależnego testu.

## Obsługa

1. W `/os/build` wybierz ID zadania i paczki, kliknij „Sprawdź wersję”. To tylko
   odczyt, bez uruchamiania aplikacji. Można też użyć przycisku przy wyniku
   istniejącego testu w historii.
2. Kliknij **Sprawdź wymagania klienta dla tej wersji**.
3. Rozwiń wymaganie. Wybierz „Nie sprawdzono”, „Potwierdzone ręcznie” albo
   „Nie spełnia wymagania”. Opisz czynność, wejście, wynik oczekiwany i rzeczywisty.
   Przy cofnięciu oceny opisz dlaczego; nie wpisuj sekretów ani danych klientów.
4. Opcjonalnie wskaż raport testów tej samej paczki. Lista nie zawiera raportów
   innych wersji ani raportów o naruszonej integralności.
5. Potwierdź zapis swojej obserwacji. Nowy zapis zachowuje wcześniejszy artefakt.
6. „Historia ocen tego wymagania” pokazuje wcześniejsze deklaracje, po 20 wpisów.
   Bieżąca lista wymagań, nie archiwalna deklaracja, określa aktualną zgodność dowodów.

Jeżeli inna karta zapisała ocenę, otrzymasz konflikt: odśwież kryteria i porównaj
wynik, zamiast nadpisywać go w ciemno. Przy utracie odpowiedzi formularz zachowuje
dokładną treść niepewnego żądania do ponowienia. Aby zmienić treść po takim błędzie,
najpierw odśwież listę. Odświeżenie usuwa niezapisane formularze.

W czasie aktywnego wynajmu Vast.ai NIE uruchamiaj aplikacji, podglądu w kontenerze
ani nowych testów w celu sprawdzenia wymagania. Można odczytywać dane i zapisywać
obserwacje z już wykonanej kontroli. Nie deklaruj kontroli, której nie wykonano.

## Spójność i historia

- Kryterium ma stabilny identyfikator SHA-256 z indeksu i tekstu.
- Każda ocena jest związana z ID paczki, sumą źródeł i sumą całego zakresu briefu.
- Nowa paczka zaczyna bez ocen, nawet jeżeli ma podobny kod.
- Zmiana briefu unieważnia stare oceny; zmienione kryterium jest nową pozycją.
- Uszkodzona ocena lub zmieniony raport oznacza stan „niespójny”, nie zaliczenie.
- Zapis jest addytywnym artefaktem `REPORT` z `previous_id` i zdarzeniem audytu.
  Nie ma migracji, kasowania ani nadpisywania istniejących rekordów. Widok pokazuje
  ostatnią ocenę oraz historię pod danym kryterium. Po zmianie tekstu kryterium
  stare artefakty pozostają zachowane, ale nie są ocenami nowego wymagania.
- Raport musi wskazywać tę samą paczkę i zadanie, mieć zgodne SHA-256 oraz powiązane
  wykonanie testów. Ogólny wynik raportu może być niezaliczony, mimo zaliczenia
  pojedynczego wymagania — inne wymagania mogą nie działać.

## API

GET/POST `/api/tasks/{task_id}/workspace-packages/{package_id}/requirements`.
Wyłącznie właściciel (istniejąca sesja z CSRF lub Bearer), `Cache-Control: no-store`.
POST wymaga `criterion_id`, `source_checksum`, `scope_checksum`, `previous_id`
(null dla pierwszej oceny), `state`, `observed_result`, opcjonalnego `test_report_id`
oraz boolowskiego `confirm_observation: true`. Dodatkowe pola są odrzucane.
Powtórzenie ostatniego identycznego żądania zwraca ten sam artefakt; stary zapis
po nowszej zmianie daje konflikt. `BEGIN IMMEDIATE` chroni sprawdzenie i zapis.

GET `.../requirements/{criterion_id}/history?before=ID` zwraca po 20 historycznych
ocen, od najnowszej. `next_cursor: null` oznacza koniec. Historyczne oceny nie
przeprowadzają ponownej kontroli dowodów; aktualny stan jest w głównym GET.

Wynik GET rozróżnia not_checked / passed / failed / stale / invalid, zwraca
liczniki i `automatic_coverage_verified: false`. Brak zlecenia z kryteriami
lub zmienione przypisanie zadania daje konflikt. Nie dopisujemy fikcyjnego zakresu.

Testy: `tests/test_requirement_checks.py`, `tests/test_requirement_checks.cjs`.
Izolowana SQLite, atrapa runnera, symulowany DOM. Bez modeli, kontenerów i GPU.
Nie przeprowadzono rzeczywistej kontroli wizualnej przeglądarki w trakcie wynajmu.
