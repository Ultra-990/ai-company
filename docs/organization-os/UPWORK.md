# Upwork — przyjęcie zakresu i realizacja

## Pierwsze zlecenia proste; docelowe możliwości szerokie

Uściślenie właściciela 14.09.2026: najpierw konto Upwork i kilka łatwiejszych
zleceń przyjmowanych osobiście. Nie ogranicza to rozbudowy systemu do prostych
zadań. Rozwijamy także integracje, pracę z istniejącymi projektami i kolejne
profile wykonawcze. Badanie rynku pomaga ustalać kolejność, ale nie jest
dowodem gotowości wykonawcy ani gwarancją obsługi każdego ogłoszenia.

W `/os/upwork`, po zalogowaniu i wczytaniu panelu, sekcja „Na początek”
ma trzy syntetyczne briefy: godziny × stawka, metry/centymetry oraz licznik
słów. Kliknięcie wypełnia opis i mierzalne kryteria, ale nie zapisuje projektu,
nie analizuje i nie uruchamia wykonawcy. Wpisane dane lub niepewny wcześniejszy
zapis wymagają potwierdzenia przed zastąpieniem formularza. Zapisane projekty
pozostają nienaruszone. Link źródła przykładu jest pusty, tytuł oznacza ćwiczenie.

To nie gotowe aplikacje ani dowód zaliczonych testów: każdy wynik nadal musi
przejść istniejący proces generacji, testów, poprawek i odbioru. Nie dopasowujemy
prawdziwego zlecenia poprzez usuwanie wymagań klienta. Obecnie aktywny wynajem
Vast.ai pozwala na przygotowanie briefu, nie uruchamianie Qwena i runnerów.
Diagnostyka próbki API pozostała dostępna w zwiniętej sekcji dodatkowej.

Testy formularza: `node --test tests/test_upwork_starters.cjs` (bez przeglądarki,
modeli, sieci i bazy produkcyjnej). Nie są testami działania wygenerowanych aplikacji.

## Wcześniejsze materiały

Aktualizacja 14.09.2026: [przegląd ośmiu publicznych ogłoszeń i braki wykonawcy](UPWORK_MARKET_2026-09-14.md).
Pierwszy wynik implementacji: [diagnostyka próbki odpowiedzi API](API_CONTRACT_PROBE.md)
w tym samym panelu — bez sieci, inferencji i zmiany gotowości zleceń.

Dodano [instrukcję klienta PL/EN i szkic wiadomości do przekazania](DELIVERY_HANDOFF.md).
Materiały są w Budowie i testach przy konkretnym zatwierdzonym wydaniu.
Odczyt nie uruchamia modelu, nie publikuje i nie zmienia odbioru klienta.

Stan: 2026-09-13. Priorytet: pierwsze małe zlecenia możliwe do wykonania
obecnym profilem. Osobne konta klientów prywatnych i płatności odłożono.
Zwykłe logowanie właściciela hasłem nadal wymaga implementacji; ten panel
korzysta z już istniejącej [wspólnej sesji](OWNER_SESSION.md), nie dodaje nowego tokena.

## Obsługa

1. Wejdź na `/os/upwork` przez link „Zlecenia Upwork” na pulpicie, w Spatial
   lub przez wyszukiwarkę. Zalogowana sesja wczyta listę; samo wejście nie
   uruchamia Qwena. Bez sesji użyj przycisku logowania w górnym pasku.
2. Wklej tytuł, opis i mierzalne kryteria odbioru, opcjonalnie źródłowy URL
   oraz uwagi. URL jest wyłącznie zapisywany — nie jest pobierany. Nie wpisuj
   sekretów ani danych dostępowych. Formularz ma limit kontekstu, nie obcina danych.
3. „Zapisz zlecenie” tworzy projekt, plan i cztery istniejące zadania:
   zakres, wykonanie, testy, przekazanie. Zapis nie oznacza przyjęcia kontraktu.
4. „Analizuj zakres lokalnym Qwenem” przygotowuje kierownika, wykonawców,
   niezależnego kontrolera oraz instrukcję analityka. Korzysta ze wspólnej
   kolejki lokalnego modelu i uruchamia tylko analizę, nie kod aplikacji.
5. Odczytaj ocenę: wstępne dopasowanie, wymagane wyjaśnienia albo brak
   możliwości w obecnym profilu. Wynik jest opinią, nie gwarancją wykonania.
   Nie można usuwać obowiązkowych wymagań klienta tylko po to, by „pasowały”.
6. „Odbierz zakres i przejdź do wykonawcy” otwiera właściwy projekt
   w `/os/work?project=ID`. Odbierz specyfikację dopiero po sprawdzeniu
   zakresu i wyjaśnieniu pytań. Dalej używaj istniejącej fabryki aplikacji:
   pliki Qwen → testy w izolacji → automatyczne poprawki → odbiór → wydanie.
7. Gotowe materiały przekazujesz na platformie sam. Nie ma automatycznych
   ofert, negocjacji, publikacji, płatności, scrapingu ani połączenia z kontem Upwork.

## Zakres wykonawcy

`python-web-v1` tworzy małe aplikacje Python stdlib z HTML/CSS/JS. Podgląd
obsługuje bezstanowe HTTP GET. Nie obejmuje instalacji pip, zewnętrznych API,
kont, trwałej bazy danych, płatności ani hostingu produkcyjnego. Dla takich
ogłoszeń trzeba najpierw rozwinąć profil wykonawczy, nie obiecywać gotowości.
Niska temperatura i poprawny format JSON nie gwarantują prawdziwości oceny.
Testy produktu i odpowiedzialność za zakres pozostają niezależne od opinii Qwena.

## Kontrola modelu

- Używany jest lokalny, przypięty skrótem model; brak płatnego API i narzędzi hosta.
- Obecnie kontekst 16384, do 8 wątków CPU, temperatura 0,2, timeout 180 s,
  `think:false`. Dla analityka Upwork limit odpowiedzi wynosi najwyżej 1536 tokenów
  (niższy limit konfiguracji nadal obowiązuje). Generowanie kodu ma osobny budżet.
- Kontrakt `upwork-scope.v1` jest częścią sumy kontrolnej instrukcji. Wymaga
  JSON z polami `fit`, `reason`, `questions`, `scope`, `acceptance_cases`, `exclusions`.
  Od 2026-09-13 schemat Pydantic jest przekazywany także do dekodera Ollamy
  (`scope_decoder: json-schema.v1`), zamiast wyłącznie prośby o JSON.
  Wcześniej zakolejkowane analizy z innym dekoderem wymagają jawnego nowego
  przebiegu; stare wyniki pozostają zachowane. Nie zmieniono wag modelu.
  Długości, wartości, puste/powtórzone pozycje i powtórzone klucze są sprawdzane.
  SUPPORTED wymaga zakresu i przypadków odbioru bez otwartych pytań;
  UNSUPPORTED nie może proponować zakresu wykonania ani negocjować usunięcia wymagań.
- Całość do 3200 znaków. Niepoprawna odpowiedź daje `scope_contract_invalid`:
  nie powstaje TaskAttempt do odbioru ani paczka. To kontrola formatu i podstawowej
  spójności, nie automatyczny dowód braku halucynacji.
- Aktualność instrukcji, digest modelu, limity i Emergency Stop są sprawdzane
  przed i po wykonaniu. Zmieniona instrukcja nie otrzyma starej odpowiedzi.
- Poprawna analiza pozostaje do odbioru; brak automatycznej akceptacji,
  przyrostu procentu lub uruchomienia kolejnego etapu.

## Trwałość i błędy

Nie powstała nowa baza ani drugi rejestr zleceń. `WorkOrder.brief` zawiera
`channel=upwork` oraz oryginalne wejście, a prace są przypisane do istniejącego
liścia `web-platforms.business`. Link źródłowy nie steruje narzędziami.
POST zapisu jest transakcyjny i idempotentny według UUID; inny zakres z tym
samym UUID daje konflikt. Niepewny zapis ponawiaj tym samym formularzem;
po przeładowaniu strony najpierw sprawdź listę, bo klucz formularza nie jest
przechowywany w przeglądarce. Nowy formularz oznacza możliwość nowego projektu.

Przygotowanie analizy również jest idempotentne. Jeśli połączenie przerwie się
po utworzeniu kolejki, „Odczytaj aktualny stan” pokaże wpis. Tylko `queued`
można uruchomić. `running/uncertain` nie powodują drugiego wykonania;
kontrolowane odzyskanie/retry dostępne w Centrum realizacji, maks. trzy próby.
Samo zamknięcie karty nie dowodzi anulowania modelu.

API owner-only (wspólna sesja/CSRF albo istniejący Bearer dla skryptów):

- POST/GET `/api/upwork-orders`: zapis i stronicowana lista tylko kanału Upwork.
- GET `/api/upwork-orders/{project_id}`: zapisany zakres, cztery etapy i ostatnia analiza.
- POST `/api/upwork-orders/{project_id}/analysis`: przydział, instrukcja i kolejka, bez wywołania modelu.
- POST istniejącego `/api/local-inference/{id}/run`: jawne wykonanie.

## Testowanie

`tests/test_upwork_orders.py` sprawdza RBAC, walidację, transakcje, replay,
powiązania z dotychczasowym procesem, bramkę odbioru i odrzucanie złych odpowiedzi.
Domyślnie model jest atrapą, baza jest testowa. `scripts/check_work_browser.py`
sprawdza formularz, niepewny zapis, wynik, bezpieczne renderowanie i przejście
do właściwego projektu na 1440/390 px; API jest symulowane, GPU wyłączone.

`scripts/check_upwork_pilot.py` uruchamia opt-in jedną rzeczywistą inferencję
Qwena na syntetycznym ogłoszeniu poza profilem. Osobna baza i raport trafiają
do prywatnego katalogu tymczasowego w `ai-company-workspaces`. Nie akceptuje
specyfikacji, nie wykonuje kodu i nie dotyka rzeczywistych zleceń. Pozytywny test
nie zastępuje przeczytania odpowiedzi przez nadzorującego.
