# Stan projektu AI Company

## Aktualizacja 21.09.2026 — modelowa naprawa bez regresji

[Lekcja precyzyjnych zmian SVG](organization-os/VECTOR_SCHOOL.md): lokalny
Qwen sam wskazał dwa atrybuty do zmiany. System zastosował jego dosłowne
operacje; tylko2bajty SVG zmienione,8/8pól tekstowych w tolerancji,
6chronionych bez zmian. Niezależnie odebrano tę lekcję i zapisano dokładne
doświadczenie rozwojowe. 96testów zaliczonych. To poprawa sposobu pracy
z narzędziem, **bez treningu wag**, porównania na nowych rodzinach lub
deklaracji gotowości całej usługi. Potrzebna szersza partia danych z podziałem
rodzin przed ćwiczeniami. Poprzednie nieudane wersje pozostają zachowane.

## Aktualizacja 21.09.2026 — odtwarzanie ulotki przez model

[Szkoła wektorowa](organization-os/VECTOR_SCHOOL.md): Qwen stworzył wzorzec
i cztery odtworzenia z PNG, bez ręcznej naprawy SVG przez asystenta.
Teksty8/8 poprawne, lecz **0/4 realizacji odebranych**: różnice typografii,
zasłanianie podtytułu i regresje przy kolejnych poprawkach. Edytowalny SVG
i eksport A5 PDF działają; ostatni PDF ma osadzone fonty i brak rastrów.
66 testów zaliczonych. To ćwiczenie przez feedback, bez treningu wag,
eksportu SFT lub gotowości do druku. Dalsza nauka wymaga precyzyjnych zmian
bez psucia poprawnych elementów. Oryginalna ulotka klienta nadal niedostarczona.

## Aktualizacja 21.09.2026 — wynik sprawdzianu wizyjnego

Na trzech nowych obrazach miejsca do czytania porównano bazę i adapter
po trzech krokach treningu, w tym samym środowisku HF. Ocena bez etykiet
faz: **10/15 → 9/15, pełne wymagania 0/3 → 0/3**. Jeden błąd struktury
po stronie adaptera. [Szczegóły](organization-os/VISION_TRAINING_INPUTS.md).
Brak wykazanej poprawy; adapter nie został wdrożony. Materiały zarezerwowane
do oceny, z blokadą eksportu do treningu. 57 testów infrastruktury zaliczone.
Potrzebne szersze sprawdzone dane; gotowość pięciu usług nadal niepotwierdzona.

## Aktualizacja 21.09.2026 — rzeczywisty trening obraz–tekst

Wykonano trzy aktualizacje osobnego adaptera na jednym odebranym wyniku
lokalnego modelu wraz z rzeczywistym PNG. Obraz przetworzony w każdym kroku,
269 tokenów odpowiedzi nadzorowanych, zmiana LoRA_B i plik wag potwierdzone.
[Przebieg i naprawa ładowania](organization-os/VISION_TRAINING_INPUTS.md).
Pierwsza próba przerwana przed aktualizacją przez błąd ładowania kwantyzacji;
druga ukończona po ograniczonej poprawce procesu. 52 testy zaliczone.
To potwierdzenie mechanizmu treningowego, **nie poprawy jakości usługi**.
Nie wdrożono adaptera; nadal potrzebne szersze dane i niezależne porównanie.

## Aktualizacja 21.09.2026 — pierwszy odebrany przykład wizyjny

Dalsze dziewięć obserwacji lokalnego Qwena: jawny schemat, krótka lekcja
i poprawka wykonana przez model. Jedna pełna obserwacja odebrana do nauki,
dwie z ostatniej próby nadal z uwagami. [Wyniki](organization-os/INTERIOR_SCHOOL.md).
Zapisano dokładny prompt, odpowiedź i rzeczywisty obraz w osobnym formacie
multimodalnym; 41 testów infrastruktury zaliczonych. **Nie wykonano jeszcze
treningu wag na tej partii**, potrzebne dalsze dane i audyt wejść trenera.
Nie jest to dowód gotowości usługi lub przeniesienia poprawy na nowe obrazy.

## Aktualizacja 21.09.2026 — obrazy wnętrz i nauka opisów

[Szkoła wnętrz](organization-os/INTERIOR_SCHOOL.md) wykonała lokalnie plan,
trzy obrazy, sześć obserwacji wizualnych i dwie wersje paczki redakcyjnej.
Autorstwo modeli zachowane. Obrazy nadają się na kandydaty ćwiczeniowe;
opisy **0/3 odebranych przed i po uwagach**: nieuzasadnione twierdzenia,
pozorne wady i urwane zdania. Zachowano błędy i ocenę, bez ręcznej naprawy.
34 testy infrastruktury zaliczone. Ta partia nie zasiliła treningu wag.
Brak podstaw do deklaracji gotowości usługi; panel i produkcyjne zlecenia
bez zmian. Dalsza nauka obejmuje ugruntowanie opisów w obrazie i zwięzłość.

## Aktualizacja 20.09.2026 — drugi trening i porównanie recenzji

Ukończono kolejny rzeczywisty trening:17 zatwierdzonych przykładów,
18 kroków QLoRA, kontekst4096, osobny adapter i potwierdzona zmiana wag.
Test ról11/12 przed i po. Trzy zarezerwowane artykuły: nauczycielska ocena
treści11/15 →9/15, pełny kontrakt0/3 →0/3. **Brak spójnej poprawy; adapter
nie został wdrożony**. [Wyniki i ograniczenia](organization-os/TRAINING_OBJECTIVE.md).
Nie ma podstaw do deklaracji gotowości wszystkich pięciu usług. Dalsza nauka
wymaga szerszych danych i odrębnej walidacji, bez uczenia na tych odpowiedziach
egzaminacyjnych. Interfejs, routing i zlecenia produkcyjne bez zmian.

## Aktualizacja 20.09.2026 — dane do specjalizacji recenzenta

Sześć syntetycznych ćwiczeń i 17 odpowiedzi lokalnego Qwena, z zachowanymi
wersjami oraz niezależnymi uwagami. Odebrano do nauki trzy dokładne recenzje:
koszty, pamięć QLoRA i ograniczenia dowodów w porównaniu platform. Pozostałe
wersje odrzucone. [Przebieg szkoły](organization-os/TECHNICAL_REVIEW_PILOT.md).
Trzy rekordy przeszły tokenizację i maskowanie odpowiedzi; na tym etapie
**nie wykonano na nich jeszcze treningu wag** (kolejny etap opisano wyżej).
Ulepszenia tych recenzji wynikają z informacji zwrotnej,
nie z użycia pierwszego adaptera. Nadal brak potwierdzonej gotowości pięciu usług.

## Aktualizacja 20.09.2026 — rzeczywisty trening adaptera

Cel właściciela: trenować lokalne modele do jakości porównywalnej z asystentem
na wskazanych usługach. [Protokół i wyniki](organization-os/TRAINING_OBJECTIVE.md).
Ukończono 14 kroków QLoRA na 14 odebranych przykładach, zweryfikowano maski,
zmianę parametrów i zapis adaptera. Ocena 11/12 przed i 11/12 po: **brak
wykazanej poprawy**. Eksperyment nie zastępuje szerszego zbioru, holdoutu
ani odbioru usług. Oryginalny model i routing pozostają bez zmian.

## Aktualizacja 20.09.2026 — ćwiczenia funkcjonalne i pięć celów Upwork

Właściciel odłożył zmiany wyglądu panelu i polecił rozwijać funkcje oraz naukę.
[Szkoła funkcji](organization-os/FUNCTION_SCHOOL.md) działa: lokalny model
napisał trzy rozwiązania (koszyk, rezerwacje, wirtualny portfel), 23/23 testy
w izolacji. Trzy dokładne kandydaty SFT pending, tokenizacja 3/3; brak treningu wag.

Zapisano pięć typów zleceń w `config/upwork-learning-targets.json`.
[Recenzent techniczny](organization-os/TECHNICAL_REVIEW_PILOT.md) wykonał
syntetyczną próbę i dwie poprawki. Ostatnia jest merytorycznie lepsza,
ale nadal `needs_more_learning`; pierwsza poprawka powtórzyła cały wynik.
Pozostałe cztery kierunki wymagają prób i wejściowych materiałów klienta.
Nie ma jeszcze podstaw do deklaracji samodzielnej realizacji wszystkich
pięciu zleceń. Menu, układ panelu i produkcyjne zadania nie zostały zmienione.

## Aktualizacja 20.09.2026 — lokalny panel bez tokena

Na komputerze właściciela `http://127.0.0.1:8000/os` automatycznie otwiera
sesję i pokazuje „Właściciel · ten komputer”. Włączono LOCAL_OWNER_ACCESS
w prywatnym .env; token nie jest wpisywany ani przekazywany do przeglądarki.
42 testy uprawnień/sesji i osiem rzeczywistych paneli Chrome zaliczone.
Szczegóły: [sesja właściciela](organization-os/OWNER_SESSION.md).
To zmiana dostępu; integracja szkoły modeli z panelem pozostaje do wykonania.

## Aktualizacja 20.09.2026 — realizacje mają wykonywać modele

Właściciel skorygował kierunek: do ukończenia projektu asystent rozwija
system, uczy i ocenia; nie pisze za lokalne modele stron ani ich poprawek.
Zasada i stała zgoda na kontynuowanie prac są zapisane w AGENTS.md.

Dodano [szkołę lokalnego wykonawcy](organization-os/LOCAL_WEB_SCHOOL.md):
pełne pliki od Qwena, niezależny egzamin, raport do samodzielnej naprawy,
pamięć zweryfikowanych błędów i automatyczne odkładanie kandydatów SFT.
Pierwsze ćwiczenie przeszło 30 kontroli po poprawce modelu; źródła zachowane
bez zmian asystenta. To pilot jednej rodziny, nie gotowa specjalizacja.
Trening wag, holdout, estetyka i integracja z kolejką/panelem pozostają
do wykonania. Szczegóły i nieudane próby w WORK_LOG.md.

## Aktualizacja 20.09.2026 — trzy nowe prototypy

Ukończono [trzy testy stron](organization-os/THREE_WEB_TRIALS.md): kolekcja
znaczków, portfolio muzyczne z własnym logo/audio i filmem sterowanym scroll
oraz ruletka/automat/blackjack na wirtualne żetony. 48/48 kontroli Chrome,
224 przypadki obliczeń gier, 15 testów transportu. Osobne kompletne ZIP-y.
Qwen dostarczył katalog i moduły logiki; asystent interfejsy, integrację,
media proceduralne i niezależną kontrolę. To nie ukończony trening ani
dowód pełnej samodzielności modeli. Materiały właściciela pozostają lokalne.

## Aktualizacja 20.09.2026 — wznowienie i kompletna paczka FORMA

Właściciel po restarcie potwierdził poprawną pracę myszy i przełączania okien
oraz polecił kontynuować budowę. Przyczyna wcześniejszego problemu pozostaje
niepotwierdzona; zabezpieczenia fokusu i zakaz sterowania pulpitem obowiązują.

Gotowy jest [kompletny kandydat FORMA](organization-os/STUDIO_BUNDLE.md):
aplikacja, trzy grafiki, scena, galeria, menu, kreator briefu i nawigacja w jednym
ZIP-ie. Odtworzony w izolacji i sprawdzony w Chrome (112 kontroli). Osobny
podgląd działa też przez jawny adres LAN dla telefonu; nie udostępnia panelu.
Nie jest to odbiór klienta ani wdrożenie. [Paczki źródeł i PNG](organization-os/MEDIA_PACKAGES.md)
są już włączone do zadań, testów, podglądu, odbioru konkretnej wersji i wydań.
Panel `/os/build` importuje kompletny JSON; ZIP zawiera binarne obrazy.
Obieg sprawdzono w tymczasowej bazie i izolowanym kontenerze, także w Chrome.
Automatyczna naprawa paczek PNG pozostaje do dalszej integracji.
Szczegóły bieżących prac i ograniczeń: WORK_LOG.md i organization-os/.

Po zgłoszeniu gorszych przejść zdjęć naprawiono blokadę renderowania przed
pierwszym kliknięciem w ramkę. Przewijanie od razu porusza zdjęcia; nie wymusza
fokusu. Nowy test pierwszego wejścia oraz pełna regresja galerii zaliczone.
Aktualny kandydat to `studio-bundle-9spiyivv`, szczegóły w STUDIO_BUNDLE.md.

Poniższy opis fundamentów jest historycznym zapisem z początku projektu,
nie aktualną listą wszystkich zaimplementowanych funkcji.

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
