# Zespoły działów i delegowanie zleceń

## Aktualizacja 2026-09-13 — specjalizacje i rzeczywiste stany pracy

W `/os/work?teams=1` (wyszukiwarka: **Agenci działów**) dostępne są profile
wszystkich 12 działów i sześciu ról w każdym. Nie utworzono drugiego rejestru
agentów ani nowych procesów działających stale. To rozszerzenie już istniejących
tożsamości i czterostopniowego procesu realizacji.

- Analityk, wykonawca, tester i koordynator korzystają z istniejącego lokalnego
  Qwena na żądanie. Specjalizacja jest dołączana do wersjonowanego pakietu:
  misja, dane wejściowe, oczekiwany rezultat, instrukcja roli i granice działu.
- Kierownik i kontroler mają opisane profile koordynacji. Nie dodano dla nich
  autonomicznego planowania ani samodzielnego zatwierdzania pracy. Kontroler
  w rejestrze nie jest dowodem przeprowadzenia niezależnej oceny przez drugi model.
  Końcowy odbiór nadal wykonuje właściciel.
- Profile: strategia/prioritety; platforma/kontrakty i migracje; AI/ewaluacja;
  aplikacje/scenariusze; strony/dostępność; Linux/izolowane badania;
  obsługa klientów/zakres; jakość/dowody; operacje/odtwarzanie;
  marketing/dane oferty; finanse/założenia i braki; wiedza/dokumentacja.
- Marketing nie ma tu internetu i nie może deklarować bieżących badań rynku;
  finanse nie mają podstaw do zgadywania stawek/podatków. Tester tekstowy
  nie wykonuje testów programu: korzysta z dostarczonych raportów lub oznacza
  brak kontroli. Rzeczywisty runner kodu pozostaje osobną funkcją fabryki.
- Profile mają wersję `department-specialization.v2` i są objęte checksumą
  instrukcji. Zmieniony profil unieważnia stare instrukcje do przyszłego
  wykonania. Otwórz gotowe zadanie i przygotuj nowy pakiet; nie nadpisuj
  historii. Wcześniejsze wyniki i odebrane zadania pozostają zachowane.
- Działy niestandardowe bez profilu zachowują wcześniejsze instrukcje ogólne.
  Nie nadpisujemy opisów, indywidualnych kierowników ani wyłączeń agentów.

### Odczyt pracy

Każda karta roli pokazuje liczbę przypisanych zadań (także historycznych)
oraz grupy stanów ostatniej inferencji każdego zadania. Nie liczymy ponowień
tego samego zadania jako wielu pracujących agentów. Stan `awaiting_review`
po odbiorze właściciela jest przedstawiany w agregacie jako accepted/rejected,
nie jako kolejny oczekujący odbiór. Brak wykonań to `not_started`, brak aktywnego
wpisu po zakończeniu to `idle`. To dane rejestru, nie niezależny heartbeat
procesów ani dowód kompetencji. Wpis running po przerwie wymaga sprawdzenia
w historii Qwen, nie natychmiastowego uruchomienia następnego procesu.

„Pokaż zadania tego działu” korzysta z owner-only
`GET /api/agent-teams/{department_id}/work?before=ID`: maksymalnie 20 zadań
na stronę, zakres ograniczony do istniejących delegacji działu. Widać
wykonawcę, kontrolera, blokady, ostatni przebieg i link do projektu.
Otwieranie/stronicowanie nie zmienia danych ani nie uruchamia modelu.
Odczyt jest na żądanie — użyj przycisku odświeżenia po pracy.

„Zleć pracę temu działowi” tylko wybiera odpowiednią gałąź w formularzu.
Podaj cel i kryteria, zapisz zlecenie, przydziel zespół, a przy gotowym
etapie przygotuj instrukcję i uruchom Qwen. Wynik i postęp są nadal
kontrolowane przez istniejący odbiór. Nie tworzymy pustych zadań, aby
podnosić procenty działów.

Aktualne testy: `tests/test_department_agents.py` sprawdza 72 profile,
instrukcje w każdym z czterech etapów wszystkich działów, historię pakietów,
stany inferencji i odbioru, RBAC oraz stronicowanie. Pilotaż realnego Qwena
`scripts/check_department_agents.py` używa wyłącznie syntetycznego zadania
i osobnej bazy w `ai-company-workspaces`. Nie zmienia prawdziwych zleceń.

Próby z 2026-09-13 wykazały ograniczenie jakości: Qwen potrafił przekroczyć
limit długości i zadeklarować jego spełnienie. Doprecyzowano format profili
oraz testy. Ostatnia próbka spełniła limit 120 słów i nie wymyślała kwot,
ale podała 12 zamiast maksymalnie sześciu pytań. Nie uznano jej za w pełni
zgodną; test pilota sprawdza teraz również liczbę pytań. Bramka odbioru
pozostała zamknięta. Te kontrole pilota nie są uniwersalnym automatycznym
walidatorem dowolnego briefu produkcyjnego — tam nadal potrzebny jest odbiór.
Zdolności całych działów nie zostały potwierdzone jednym zadaniem tekstowym.

## Wcześniejszy stan rejestru (2026-09-12)

Stan: 2026-09-12. Wdrożono trwały rejestr zespołów i przydział istniejących
zadań z centrum realizacji. **Nie jest to jeszcze uruchomiona sieć modeli AI.**
Rejestracja nie dowodzi kompetencji, dostępnego modelu, testów ani zdolności
do samodzielnego wykonania płatnego kontraktu.

## Hierarchia

```text
Właściciel — strategia, zasoby i końcowy odbiór
└── Brain — istniejąca tożsamość brain-core
    ├── Kierownik działu
    │   ├── Analityk wymagań
    │   ├── Wykonawca
    │   ├── Inżynier testów
    │   └── Koordynator przekazania
    └── Niezależny kontroler tego działu
```

Kontroler nie podlega kierownikowi realizującemu pracę. Każdy z 12 aktywnych
głównych działów ma sześć stabilnych tożsamości (72 nowe role + istniejący
właściciel i Brain). Aktualne `active=true` oznacza dostępność przypisania,
**nie pracującą sesję modelu**. UI jawnie pokazuje „model nieuruchomiony”.

Wykorzystano istniejącą tabelę `agents`; `metadata_json` zawiera wersję
profilu, dział, rolę, przełożonego i ograniczenia. Klucze `team.{id_działu}.{rola}`
nie zmieniają się po zmianie nazwy działu. Konfiguracja jest idempotentna,
nie nadpisuje opisów, wyłączeń ani istniejących indywidualnych kierowników.

## Obsługa

1. Otwórz `/os/work` → token właściciela → **Połącz**.
2. W sekcji **Kierownicy i zespoły agentów** wybierz **Pokaż zespoły**.
   Zespoły na bieżącej bazie zostały przygotowane podczas wdrożenia.
   W nowej instalacji **Przygotuj zespoły działów** tworzy brakujące role.
3. Utwórz zlecenie z rzeczywistym zakresem albo wybierz istniejące z listy.
4. **Przydziel kierownika i agentów** przypisuje cztery istniejące zadania:
   specyfikacja → analityk, implementacja → wykonawca, testy → tester,
   odbiór/przekazanie → koordynator. Każde dostaje kierownika i osobnego kontrolera.
5. Karta zadania pokazuje osoby/role, poprzedni etap, instrukcję,
   kryterium ukończenia, blokady planu oraz osobną blokadę wykonania.

Token pozostaje w dotychczasowej pamięci strony. Wylogowanie usuwa też dane
zespołów i delegacji. Wszystkie nazwy i briefy renderowane są jako tekst.

## Zasady delegacji

- Nowa tabela `task_delegations`: FK do istniejącego zadania, działu i trzech
  agentów; poprzednik, kopia briefu, kryterium etapu, polityka i czas.
  Jeden rekord na zadanie, brak duplikowania zadań lub projektów.
- Przydział dotyczy tylko nierozpoczętych, niekolejkowanych zadań bez prób.
  Błąd choćby ostatniego etapu cofa całą transakcję.
- Dział wyznaczany jest przez przejście od liścia projektu do głównego działu;
  cykl, brak lub nieaktywny przodek blokuje nowy przydział.
- Powtórzenie jest bezpieczne: nie zmienia istniejących delegacji.
  Edycja/przenoszenie już przydzielonej pracy wymaga przyszłego procesu rewizji;
  nie ma tu automatycznego nadpisywania odpowiedzialności.
- Gotowość planu sprawdza dostępność aktorów, niezależność kontroli, zgodność
  przypisania/briefu i odebranie poprzedniego etapu. Sam `completed` nie wystarcza:
  ostatnia próba musi mieć ukończony stan, akceptację, datę weryfikacji i zgodną
  sumę wyniku. Jest to odczyt istniejącego odbioru właściciela, nie nowy test jakości.
- Gotowość planu nie jest zgodą na uruchomienie. Polityka wykonania jest stale
  wyłączona: brak narzędzi, koszt 0, brak publikacji i działań zewnętrznych.
- `list_ready` i atomowe `claim` starej kolejki wykluczają delegowane zadania.
  Nawet ręczne zakolejkowanie i wcześniejsza zgoda nie obchodzą tej blokady.
  Pozostałe, wcześniejsze zadania zachowują dotychczasową obsługę kolejki.

## API, integralność, audyt

Wszystko wymaga obecnego Bearer Owner, `Cache-Control: no-store`:

- `GET /api/agent-teams` — działy, role i przełożeni.
- `POST /api/agent-teams/initialize` — idempotentne utworzenie brakujących ról.
- `POST /api/work-orders/{project_id}/delegate` — atomowy przydział.
- `GET /api/work-orders/{project_id}` — istniejący kontrakt rozszerzony
  o `tasks[].delegation` (null przed przydziałem).

Zapisy są serializowane transakcją SQLite BEGIN IMMEDIATE; zdarzenia audytu
`agent_team` i `task_delegation` są częścią tej samej transakcji co zmiana.
Przy błędzie/timeout odśwież stan i ewentualnie powtórz tę samą operację.
Nie ma przekazywania tokenów, uprawnień hosta ani prywatnych narzędzi agentom.

Nowa tabela jest rejestrowana w istniejącym `Base.metadata` i tworzona przez
obecny startup; nie usuwa ani nie przekształca dawnych danych. Backup przed
inicjalizacją bieżącej bazy zapisano lokalnie, ścieżka w `docs/WORK_LOG.md`.

## Kolejne etapy potrzebne do rzeczywistej realizacji

1. Wersjonowane instrukcje i sprawdzalne kwalifikacje wykonawców dla jednej
   pierwszej usługi (np. strony i małe aplikacje), nie wszystkie branże naraz.
2. Adapter sesji modelu przypisanej do konkretnej tożsamości; ograniczony czas,
   koszt i kontekst. Uzgodnione zasoby poza aktywnym wynajmem Vast.ai.
3. Izolowany runner konkretnej paczki i zapis rzeczywistych wyników testów;
   niezależny odbiór i poprawki. Nie uruchamiać obcego kodu na hoście wynajmu.
4. Dopiero po pilotażu: zatwierdzane przekazanie klientowi, wycena i rozliczenie.

Nie uruchomiono inferencji, runnera, automatycznych ofert Upwork ani publikacji.
Te funkcje nie wynikają z samego istnienia tożsamości agentów.

## Testy

`tests/test_agent_teams.py`: hierarchia, 72 role, powtórzenia i zachowanie zmian,
RBAC, atomowe wycofanie, cztery przydziały, brak wykonania, blokady, kontrola
poprzednika i integralności oraz brak obejścia przez starą kolejkę.
`scripts/check_work_browser.py`: konfigurowanie zespołu, przydział, widoczny
kontroler/blokady, bezpieczny tekst i wcześniejsze funkcje centrum realizacji.
Testy używają izolowanych baz lub symulowanego API, bez modeli/GPU.
