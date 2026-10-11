# Fabryka aplikacji — pierwszy działający profil

Aktualizacja 11.10.2026: sześcioplikowa generacja, pełna rewizja oraz zawężona
poprawka ROWEROWNI przeszły opisane niżej kontrole. Jest to dowód jednego
syntetycznego przebiegu, nie kwalifikacja modelu do samodzielnej realizacji
dowolnej strony.

Aktualizacja 19.09.2026: [syntetyczne zlecenie strony usługowej](UPWORK_WEB_PILOT.md)
sprawdza Qwen → ograniczone poprawki → niezależne testy HTTP/przeglądarki →
ZIP kandydata. To test istniejącego procesu, nie automatyczne przyjmowanie
zleceń ani potwierdzenie jakości premium. Podgląd zachowuje teraz motyw,
język i dozwolone atrybuty układu dokumentu aplikacji.

Weryfikacja zakresu: [wymagania konkretnej wersji i dowody](REQUIREMENT_CHECKS.md).
Osobny rejestr obserwacji właściciela; zaliczone testy nie potwierdzają automatycznie
wszystkich kryteriów klienta.

Nowość: [przekazanie klientowi](DELIVERY_HANDOFF.md) — zatwierdzony ZIP
z instrukcjami PL/EN oraz osobny szkic wiadomości EN w panelu. Bez inferencji,
uruchamiania kodu, automatycznej wysyłki lub zmiany statusów.

Stan: 2026-09-13. Profil **python-web-v1** tworzy małe aplikacje webowe Python
3.10 z biblioteką standardową i HTML/CSS/JS. Nie jest jeszcze ogólnym wykonawcą
projektów React, zależności npm/pip, baz danych, usług chmurowych ani wszystkich
zleceń Upwork. Nie ma automatycznej komunikacji z klientem czy wdrożenia produkcji.

## Przepływ w panelu

Obsługa kolejnych wersji: [zgłoszenie poprawki → Qwen → testy → odbiór](APPLICATION_REVISIONS.md).
Wykrywanie i poprawianie błędów bez ręcznego opisywania każdej poprawki:
[automatyczny cykl testy → Qwen → ponowne testy](AUTOMATIC_QUALITY.md).

### Działający podgląd bez otwierania plików z dysku

W `/os/build`, po połączeniu tokenem właściciela, przy zaliczonym wykonaniu
kliknij **Otwórz aplikację w izolacji**. Kalkulator zadania 45 / paczki 5
można obsługiwać bez wypakowywania ZIP i uruchamiania Pythona na hoście.
Jeżeli masz wcześniej otwartą kartę, odśwież ją (Ctrl+Shift+R) i otwórz podgląd
ponownie. Odpowiedź startowa przekazuje treści `assets` (app.js, style.css).
Zwykły GET paczki zawiera tylko metadane; brak assetów jest komunikowany jako
błąd, zamiast wyświetlać formularz bez skryptu.
Przeglądarka wyświetla formularz, a przycisk Oblicz zwraca wynik z rzeczywistego
serwera aplikacji uruchamianego w kontenerze. Kliknięcie 8 × 322 zweryfikowano
w Chrome: widoczny wynik `Łączny koszt: 2576 zł` (2026-09-13).

**Nie otwieraj `sources/index.html` bezpośrednio z dysku.** Dotychczasowa paczka
jest aplikacją serwerową: `/app.js` i `/api/estimate` wymagają serwera.
Stare źródła i ZIP zachowano bez nadpisania. Nowo pobierane ZIP zawierają
wyraźne ostrzeżenie w READ-ME-FIRST.md; kontrakt kolejnych generacji Qwen
wymaga też wyjaśnienia trybu file:// w samej aplikacji.

Podgląd to obecnie ograniczony **bezstanowy GET**, nie pełny hosting:

- Każde żądanie tworzy własny kontener z identyczną paczką i po odpowiedzi
  usuwa go. Brak portów opublikowanych na hoście, sieci, GPU, sekretów i
  importowania wygenerowanego Pythona na hoście. Ten sam globalny slot i
  mechanizm uzgadniania niepewnego sprzątania co runner testowy.
- Obsługiwane GET `/` i `/api/nazwa?parametry`. Bez POST, WebSocket, logowania,
  bazy, sesji i zachowania zmian między żądaniami. Maksymalnie 12 KB odpowiedzi,
  30 żądań na otwarcie widoku i 120 na wersję paczki; limit kontenera 45 s,
  wewnętrzny limit serwera podglądu 15 s.
- Ramka ma osobny, nieprzezroczysty origin (`sandbox allow-scripts allow-forms`),
  brak same-origin, magazynu przeglądarki i dostępu do rodzica/tokena. CSP blokuje
  sieć, zewnętrzne skrypty i wysyłanie formularzy. `allow-forms` umożliwia
  zdarzenie submit obsługiwane przez JavaScript, `form-action 'none'` nadal
  blokuje rzeczywistą nawigację formularza. Rodzic pośredniczy wyłącznie w
  ograniczonych żądaniach wersji wybranej przez właściciela.
- Źródła JS są wykonywane tylko w ramce przeglądarki, Python tylko w kontenerze.
  To nie środowisko do celowo wrogiego kodu. Kontenery współdzielą jądro;
  przeglądarka nie narzuca limitu CPU pojedynczemu skryptowi aplikacji.
- Każdy request zostawia wersjonowany PackageRun i raport HTTP. `previewed`
  nie oznacza zaliczenia testów ani odbioru. Historia zachowuje ostatnie 30
  uruchomień testowych i 5 żądań podglądu. Zamknięcie/wylogowanie usuwa ramkę,
  nie deklaruje anulowania już rozpoczętego żądania.

Regresja: `scripts/check_application_browser.py` używa prawdziwej paczki 5,
prawdziwej przeglądarki i kontenerów. Tymczasowy serwer testowy udostępnia
wyłącznie zaufany panel, losowy token testowy i pośrednik do pełnych endpointów
FastAPI (prawdziwa serializacja i autoryzacja, bez mockowania źródeł). Zapisuje
raporty podglądu w bazie, nie zmienia statusu ani odbioru zadania. Sprawdza
kliknięcie 8 × 322, błąd dla ujemnej wartości, izolację origin/storage,
odmowę zewnętrznego fetch i POST oraz usunięcie ramki po wylogowaniu.

### Generowanie, testy i wydanie

1. `/os/work`: utwórz projekt i przydziel zespół. Zakres/specyfikacja muszą
   zostać przygotowane i odebrane, zanim odblokuje się etap wykonawcy.
2. Przy etapie wykonawcy kliknij **Przygotuj instrukcję**. Wybierz
   **Qwen: wygeneruj pliki aplikacji Python**. Opcjonalnie zaznacz wcześniej
   automatyczne wykonanie aplikacji i testów po wygenerowaniu plików.
   Ta zgoda obejmuje tylko opisany stały profil, nie dowolny terminal.
3. Model zwraca JSON z pełnymi źródłami. Serwer sprawdza strukturę, ścieżki,
   rozmiary i kompletność przed atomowym zapisem paczki oraz próby do odbioru.
   Nie importuje ani nie wykonuje plików na hoście. Błędny JSON nie tworzy
   częściowej paczki. W historii Qwen pojawia się link do testów tej wersji.
4. `/os/build`: jeżeli nie wybrano automatycznych testów, wczytaj ID zadania
   i paczki, sprawdź SHA-256 i potwierdź uruchomienie kontenera. Nie można podać
   własnego polecenia, obrazu, ścieżki, portu ani ustawień sieci przez API.
5. Odczytaj raport. `passed` znaczy zaliczenie ograniczonego profilu, nie
   spełnienie wszystkich wymagań klienta. Pobierz ZIP kandydata do przeglądu.
6. Sprawdź źródła, wygląd, kryteria funkcjonalne i ograniczenia. W `/os/review`
   lub przy zadaniu wybierz odbiór konkretnej próby z jej checksumą i dowodami.
7. W `/os/build` wybierz **Sprawdź gotowość do przekazania**. Panel wyjaśni,
   czy źródła i raport testów są spójne, czy odebrano tę konkretną próbę i czy
   wydanie już istnieje. Dopiero po zaliczeniu bramek pokaże przycisk
   **Przygotuj i pobierz zatwierdzone wydanie**. Wydanie zapisuje osobny
   artefakt oraz audyt. Odczyt gotowości nie akceptuje pracy i nic nie zapisuje.
8. Przekazanie pobranego wydania klientowi jest osobną czynnością. System
   nie wysyła ZIP na Upwork, nie publikuje aplikacji i nie deklaruje odbioru klienta.

Kontrola `GET /api/package-runs/{run_id}/delivery-readiness` wymaga tokenu
właściciela i zwraca `ready`, `checks`, `release_id` oraz identyfikatory wersji.
Brak gotowości jest poprawnym wynikiem 200 z wyjaśnieniem, nie błędem serwera.
Nie uruchamia modelu, kontenera, odbioru ani zapisu wydania. Kontrola korzysta
z tych samych walidacji co pobieranie ZIP: źródła/raport, najnowszy test
w aktualnym profilu oraz odbiór dokładnie tych źródeł Qwen. Niespójny istniejący
zapis wydania wstrzymuje przekazanie. To stan odczytany w danej chwili:
przygotowanie i pobranie ponownie weryfikują bramki, również po zmianach
w innej karcie. Pola dotyczące klienta nie zastępują historii jego publikacji.

Po przerwaniu połączenia najpierw odśwież historię. UUID chroni ponowienie tego
samego żądania przed drugim uruchomieniem. Nowy UUID oznacza nową świadomą próbę;
dozwolone są maksymalnie trzy uruchomienia jednej paczki. Poprawki tworzą nową
paczkę (nową wersję), nie zmieniają istniejących dowodów.

## Kontrakt źródeł Qwen

Wymagane: `app.py`, `test_app.py`, `index.html`, `README.md`. Opcjonalnie:
`style.css`, `app.js`. Tylko płaskie, jawne nazwy plików, tekst UTF-8 bez NUL;
brak dowiązań, archiwów wejściowych, ukrytych plików i nadpisania testera.
JSON nie może mieć powtórzonych kluczy lub dodatkowych pól z poleceniami.
Generowanie używa jawnego schematu tych plików zamiast samego trybu JSON.
Instrukcja preferuje zwarty kod i cztery pliki, aby odpowiedź zmieściła się
w obecnym budżecie. Nie zwiększono limitu 4096 tokenów; ucięty wynik nadal
jest odrzucany, bez utworzenia częściowej paczki.

Program używa `HOST=127.0.0.1` i `PORT=8080`, `/health` odpowiada
`{"status":"ok"}`, `/` zwraca HTML. Nie wolno wystawiać plików źródłowych
ani dowolnych ścieżek systemowych. Zależności muszą mieścić się w stdlib.
Model nie może oznaczać testów jako wykonanych; ich wynik zapisuje runner.

`LocalInference.limits.output_profile` rozróżnia tekst i źródła bez zmiany
starej tabeli. Jedna instrukcja ma jeden profil wykonania. Wynik modelu,
pakiet, raport i odbiór zachowują oddzielne identyfikatory oraz SHA-256.

### Sześcioplikowy adapter generowania

`app/services/filewise_application_provider.py` zachowuje profil `python-web-v1`
(historyczny moduł w `scripts` jest zgodnym importem),
ale dla pierwszej wersji prosi lokalny model kolejno o dokładnie sześć plików:
`app.py`, `test_app.py`, `index.html`, `style.css`, `app.js` i `README.md`.
Każde wywołanie ma schemat `{"content":"..."}`, jawny typ pliku, miękki cel
znaków i limit `num_predict <= 3000`. Adapter przekazuje oryginalny pakiet oraz
dokładne, już wygenerowane źródła, aby model utrzymał zgodność plików. Przed
każdym wywołaniem sprawdza wolny slot modelu; cały przebieg ma najwyżej sześć
wywołań i deadline 600 s, a timeout pojedynczego wywołania nie przekracza
pozostałego czasu ani 180 s.

Żądanie i surowa odpowiedź każdego pliku są zapisywane przed parsowaniem wraz
z hashami, tożsamością modelu i autorstwem (`code=local_model`,
`orchestration=assistant`). Adapter nie minifikuje, nie poprawia i nie wykonuje
kodu. Pusty, ucięty, zbyt duży wynik, zmiana modelu/digestu lub przekroczenie
łącznego limitu 32 KB zatrzymują składanie; częściowe dowody pozostają, lecz nie
powstaje końcowa paczka. Profil `python-web-repair-v1` nie uruchamia sześciu
wywołań: przechodzi przez zwykły, pojedynczy dekoder poprawki i również zachowuje
surową odpowiedź.

Zwykła kolejka obsługuje serwerowy opt-in `application_generation_strategy:
filewise-v1` wyłącznie dla `python-web-v1`. Brak pola lub `single-call-v1`
zachowuje dotychczasowy przepływ. Strategia i stałe budżety trafiają do snapshotu
wykonania; zadanie ani caller API nie podają parametrów modelu. Profile tekstu,
modułów i zawężonej poprawki nadal używają jednego wywołania. Rezerwacja slotu
obejmuje cały batch, a ponowienie trwającego wpisu wymaga upływu 600+15 sekund.

Pakiet wejściowy jest kodowany bez dodatkowej warstwy JSON-string; wszystkie
wartości i wcześniejsze źródła pozostają kompletne. Enqueue sprawdza dokładny
pierwszy prompt, a każdy kolejny call ponownie mierzy pełne UTF-8 względem
`num_ctx - num_predict - 1024`. Przekroczenie kończy batch przed kolejnym
wywołaniem, bez częściowej próby zadania lub paczki. Przy początkowym kontekście
16384 duży katalog PLAN ZAJĘĆ przekracza tę konserwatywną bramkę już przy drugim
pliku; nie podniesiono limitów ani nie ogłoszono obsługi dowolnie dużego briefu.

Dowody są zapisywane w prywatnym katalogu, a ograniczony, sprawdzony zestaw
request/response/manifest trafia do artefaktu REPORT także po porażce lub zmianie
instrukcji. Import kontroluje typ i rozmiar plików, hashe, liczniki wywołań,
źródła i zgodność manifestu z rzeczywistym obiektem wykonania. Produkcyjny
manifest identyfikuje deterministyczną usługę w `execution_context`; zachowuje
historyczne autorstwo kodu modelu. Późna odpowiedź po 600 s zostaje dowodem,
ale nie tworzy paczki. Niepewny transport nadal zajmuje slot do uzgodnienia.

`scripts/filewise_production_canary.py` sprawdza tę ścieżkę na małym fikcyjnym
LICZNIKU LITER, w oddzielnej bazie i z zamrożonym harness'em. Domyślnie pominięty
test wymaga jawnego `--run` i nowego katalogu roboczego. Nie zmienia aktywnej
konfiguracji, nie odbiera produktu ani go nie publikuje.

### Uwagi po odrzuceniu i dwa rodzaje poprawki

`append_rejection_review` może dopisać nowe, wersjonowane uzasadnienie i dowody
wyłącznie do najnowszej, integralnej, już odrzuconej próby. Wymaga zgodnej sumy
wyniku i nie tworzy nowej próby, nie zmienia odrzucenia w akceptację oraz nie
udaje ponownego testu.

Automatyczna poprawka pozostaje zawężona: `python-web-repair-v1` może zmienić
1–2 istniejące pliki, a `test_app.py` jest składany z wersji bazowej bajt w bajt.
Pełna rewizja jest osobną, jawną operacją `python-web-v1`: model ponownie pisze
wszystkie sześć plików, w tym własny helper w `test_app.py`, gdy błąd dotyczy
samej konstrukcji testu. Nie wolno osłabiać asercji; nowa wersja przechodzi
niezmieniony, niezależny harness. Dzięki temu naprawa wadliwego helpera testowego
nie obchodzi blokady testów automatycznego cyklu.

## Izolowany profil wykonania

- Lokalny obraz `python:3.10-slim` jest przypięty do ID
  `sha256:0f61d91517f6602b9d99096696845f54ddfe01a52029b4f55fdddb277ebe034a`.
  Obraz pobrano z repozytorium jako
  `python@sha256:6ff506466f8b1e981719b468cc0023b8ef000b983cdec0eafe119d01f379e31d`;
  wykonanie nadal używa `--pull=never` i nie instaluje zależności. Pin oznacza
  sprawdzony lokalny artefakt, nie deklarację najnowszej poprawki bezpieczeństwa.
  Raporty i certyfikaty utworzone z wcześniejszym image ID pozostają dowodami
  historycznych wykonań; nie są przepisywane ani automatycznie uznawane za test
  bieżącego profilu.
- Docker pod stałym lokalnym socketem, `runc`, seccomp builtin i AppArmor.
  Brak uprzywilejowania, capabilities, nowych uprawnień, GPU, sieci zewnętrznej,
  mapowania portów, sekretów, docker.sock i katalogów repozytorium w kontenerze.
- UID/GID 65534, read-only root i źródła, tymczasowy `/tmp` 32 MiB noexec,
  1 CPU, 512 MiB RAM (bez dodatkowego swap), 64 PID, limit otwartych plików,
  rozmiaru pliku 16 MiB i brak core dump. Logowanie demona dla kontenera wyłączone.
- Testy aplikacji: oddzielny proces, timeout 15 s, brak testów to porażka.
  Tester HTTP uruchamia aplikację i sprawdza health, HTML oraz odmowę dostępu
  do kilku źródłowych/systemowych ścieżek. Nie jest to pełny pentest.
- Tester PID 1 ma alarm 35 s, transport hosta deadline 45 s i max 32768 B
  wyjścia; log testów w raporcie ograniczony do 12000 znaków. Kod paczki nie
  jest importowany do procesu API. Odpowiedź z kontenera jest danymi.
- Kontrola przed `docker create` rozróżnia ograniczone przyczyny
  `preflight_security_unavailable`, `preflight_image_unavailable` i
  `preflight_harness_changed` oraz zapisuje `container_started=false`. Taki
  wynik kończy się jako `failed` tylko po osobnym odczytowym potwierdzeniu, że
  dokładna losowa nazwa kontenera nie istnieje. Jeżeli pod tą nazwą istnieje
  własny albo obcy kontener lub odczyt jest niejednoznaczny, stan pozostaje
  `uncertain`; preflight nie usuwa kontenera. Raport rozróżnia utworzenie
  kontenera i próbę startu. Niejednoznaczny timeout samego `docker create`
  pozostaje `uncertain`; ograniczony timeout po próbie startu zachowuje faktyczny
  wynik sprzątania, więc potwierdzone usunięcie nie jest fałszywie oznaczane jako
  niepewne. Awaria infrastruktury nie jest przekazywana modelowi jako błąd aplikacji.
- Jeden globalny slot bazy i blokada katalogu runnera. Stan `uncertain`
  zatrzymuje kolejne uruchomienia. Przy przerwaniu procesu API po 90 s dostępne
  jest jawne uzgodnienie i sprzątanie wyłącznie zapisanej losowej nazwy kontenera,
  po potwierdzeniu jego własnej etykiety. Brak globalnego kill/prune/restart.
- Robocze źródła są kopiowane do prywatnego, tymczasowego podkatalogu
  `/home/marcin/ai-company-workspaces/runner`, montowane tylko do odczytu,
  następnie usuwane. Oryginały pozostają w SQLite i ZIP. Nie używamy Windows.

Kontenery współdzielą jądro hosta. Nie są wystarczającą granicą dla celowo
wrogiego kodu, niezaufanych narzędzi klientów lub ataków na kernel. Przed takim
zakresem potrzebny jest osobny host/VM i dodatkowy audyt. Wygenerowane testy
mogą być błędne lub zbyt słabe; ich sukces nie zastępuje niezależnego odbioru.
Wynik logu nie jest kryptograficznym poświadczeniem uczciwości programu.
Parametry: [Docker run](https://docs.docker.com/engine/containers/run/) i
[seccomp](https://docs.docker.com/engine/security/seccomp/).

## API i wydania

Wszystkie trasy wymagają właściciela; oddzielny panel klienta ich nie posiada.

- `POST /api/local-inference`: `output_profile: "python-web-v1"` dla wykonawcy.
- `GET /api/package-runs`: ostatnie 30 wykonań, bez uruchamiania Dockera.
- `POST /api/package-runs`: UUID, task_id, package_id, package_checksum,
  `confirm_execution: true`. Uruchamia jedną wersję w stałym profilu.
- `POST /api/package-runs/{id}/reconcile`: po limicie, tylko własny kontener.
- `GET /api/package-runs/{id}/candidate.zip`: źródła i raport po zaliczeniu profilu.
- `POST /api/package-runs/{id}/release`: po istniejącym odbiorze właściciela.
- `GET /api/package-runs/{id}/released.zip`: odebrana wersja, bez publikacji.

ZIP zawiera `sources/`, `delivery.json`, `test-report.json`, `READ-ME-FIRST.md`.
Manifest rozróżnia zgodę właściciela, klienta i wdrożenie. Ponowne przygotowanie
wydania nie tworzy duplikatu. Odmienna/odrzucona ostatnia próba blokuje wydanie.
Wymagane jest najnowsze wykonanie paczki w aktualnym profilu testera; starszy
sukces nie przesłania późniejszej porażki ani zmiany konfiguracji izolacji.

## Rzeczywisty pilotaż

Projekt **#5 „Pilotaż fabryki aplikacji — kalkulator zakresu”**, zadanie **#45**,
generowanie **#2**, paczka **#5**, test kontenerowy **#1**, raport **#7**.
Nowy pilot ma pierwszy etap świadomie skonfigurowany jako wykonawczy na podstawie
pełnej specyfikacji wejściowej; nie fabrykowano zakończonego etapu analizy.

Qwen napisał aplikację i testy w 111.254 s, 2998 tokenów generowania. Kontener
wykonał 19 testów, health, HTML i kontrole ścieżek; profil zaliczony, sprzątanie
potwierdzone. Pliki i wynik czekają na odbiór. Nie utworzono rzeczywistego
zatwierdzonego wydania za właściciela. ZIP kandydata:

`/home/marcin/ai-company-workspaces/candidate-vmq0lxsm/application-candidate.zip`

Dodatkowe rzeczywiste próby znanego wzorca: 4 testy izolacji zaliczone,
zawieszony test przerwany i odrzucony, brak testów odrzucony. Wszystkie własne
kontenery usunięto. Qwen przygotował również szkic harnessu; niezależny przegląd
poprawił m.in. nieograniczone logi, importy i możliwość sukcesu przy zerze testów.

Nie wykonano pełnego odbioru wizualnego aplikacji, wdrożenia, płatności,
obsługi kont klienta, dowolnych bibliotek ani uruchamiania następnych zadań w pętli.
Te elementy nie są oznaczone jako gotowe.

## Syntetyczny pilot wieloplikowy i przeglądarka

`scripts/check_application_delivery.py` tworzy osobną testową bazę i pełne
zlecenie kalkulatora z rabatem. Uruchamia prawdziwego Qwena, dotychczasowy cykl
kontroli/poprawek i runner. `tests/application_pilot_checks.py` dodaje 14
niezależnych prób HTTP oraz wstępną kontrolę HTML: brak przypisania innerHTML
i obecność wskazówki file://. Te dwie kontrole tekstowe nie dowodzą wyglądu
ani działania ostrzeżenia, nie analizują też dowolnych zewnętrznych skryptów.
Obecność testu `discount=` rozróżnia pusty parametr od pominiętego parametru.
Nie są to uniwersalne testy wszystkich aplikacji: dotyczą tego jednego briefu.

`scripts/check_delivery_browser.py ŚCIEŻKA_DO_REPORT.JSON` sprawdza źródła
z udanej próby dostawy w osobnym profilu Chrome i istniejącej nieprzezroczystej
ramce. Wymaga raportu z `candidate_created=true`, `quality.state=passed`
i `final_sources` pod `/home/marcin/ai-company-workspaces`. Uruchamia wyłącznie
syntetyczny serwer pośredniczący na loopback oraz PreviewRunner; nie tworzy
PackageRun w prawdziwej bazie i nie odbiera zadania. Raport SHA-256 służy jako
lokalne powiązanie testowe, nie jako checksum produkcyjnej paczki.

Sprawdzane są kliknięcia formularza: 8×322 z rabatem10% →2318,40, pusty
opcjonalny rabat w formularzu →2576,00, odmowa ujemnych godzin, brak dostępu
do DOM rodzica/storage, odmowa zewnętrznego fetch oraz usunięcie ramki po
zamknięciu. Generowany Python działa tylko w kontenerze; JS tylko w ramce.
To nie pełny audyt bezpieczeństwa ani automatyczny odbiór biznesowy.
Wyniki, także nieudane, opisuje [dziennik](../WORK_LOG.md).

Próba 2026-09-13 `application-delivery-pilot-d1qoyzrn`: pierwsza generacja,
dwa nieudane zestawy testów, dwie poprawki samego app.py oraz zaliczenie
końcowych testów. 44.15s łącznie; poprawki 9.603s/892tokeny i9.724s/896tokenów.
Testy, HTML i README zachowane. Powstał ZIP kandydata, nie odebrane wydanie.
Źródła końcowe przejrzano; tej nowej wersji nie poddano jeszcze audytowi Chrome.
To pojedynczy sukces po wcześniejszych porażkach i doprecyzowaniu instrukcji,
nie oszacowanie skuteczności ani obietnica realizacji dowolnego zlecenia.

## ROWEROWNIA — pełna rewizja i poprawka krawędziowa

Syntetyczny przebieg `business-website-pilot-fkf_d3w0` zachował surowe odpowiedzi
sześcioplikowego generowania i wszystkie kolejne wersje. Pierwszy kandydat ujawnił
błędny helper we własnym `test_app.py`, brak ścisłej odmowy dodatkowego parametru,
brak widocznej informacji `file://` oraz braki prezentacyjne. Zamiast zmieniać
zamrożony tester lub ręcznie pisać produkt, system wykonał jawną pełną rewizję
sześciu plików przez lokalny model. Następnie dodatkowa kontrola znalazła pusty
dodatkowy parametr gubiony przez parser; zawężona poprawka modelu zmieniła tylko
`app.py`, zachowując `test_app.py` i pozostałe pliki bajt w bajt.

Końcowa wersja to paczka **#24** o sumie
`7e741d9607a1e157dd9f8ac9d08c6fe7477cb0cd2be378bf553873efb7dc9b16`.
Zaliczyła 8 testów modelu w izolowanym runnerze, 16 zamrożonych niezależnych
przypadków HTTP/HTML, 12 kontroli rzeczywistej przeglądarki oraz 3 dodatkowe
próby API. Trzecia próba dodatkowa dla powtórzonego parametru była diagnostyczna,
nie osobną bramką, ale również przeszła. Kontrole przeglądarki obejmowały oba
viewporty, menu i Escape/fokus, FAQ oraz trzy rzeczywiste wyceny przez izolowany
backend. Pierwotny raport zachowuje `accepted=false`, `visual_review=pending` i
`deployed=false`. Późniejszy osobny `technical-assessment.json` dokumentuje
przegląd pełnych screenshotów i ograniczony odbiór techniczny. Automatyczne
testy nie stanowią decyzji właściciela. Nie wykonano publikacji produktu,
pracy dla klienta ani treningu wag.

Ten przebieg pokazuje, że system potrafił zachować autorstwo modelu, rozdzielić
pełną rewizję od zablokowanej poprawki, przekazać obserwowany błąd z powrotem do
modelu i związać wynik z konkretnymi źródłami oraz testerem. Nie mierzy skuteczności
na nowych domenach, jakości premium, odporności na celowo wrogi kod ani zdolności
do pracy bez nadzoru. Jedna rodzina briefu i poprawki po ujawnionych błędach nie
jest testem generalizacji.

## Scenariusz transferowy SERWIS CREMA

`scripts/service_quote_transfer_case.py` definiuje nowy syntetyczny brief
sześcioplikowej strony serwisu ekspresów, odmienny endpoint `/api/quote`, ceny,
jednorazową opłatę dojazdową, kontrolki DOM i tryb `file://`. Dokładne 19 prób
egzaminatora zostało zamrożonych poza publicznym briefem i obejmuje poprawne
wyceny, brakujące, puste, dodatkowe i powtórzone parametry, 404, strukturę sześciu
plików, lokalne assety, dostępność i README. `scripts/check_service_quote_transfer.py`
uruchamia ten przypadek przez ten sam izolowany przepływ oraz filewise provider;
przeglądarka ma osobną konfigurację scenariusza.

Pierwszy przebieg `service-quote-transfer-q4ylytju` zakończył się stanem
`needs_attention`, bez kandydata. Sześcioplikowe generowanie trwało 60,378 s
i zwróciło 5540 tokenów. Niezależny runner wykazał cztery błędy testów modelu:
helper tworzył obiekt `H` bez metody `do_GET`. HTML duplikował CSS/JS inline,
zamiast łączyć wymagane lokalne `style.css` i `app.js`. Jedna automatyczna
poprawka trwała 16,17 s i zwróciła 1921 tokenów, ale została odrzucona jako
nieprawidłowa, ponieważ wskazany plik pozostał niezmieniony. System nie uznał
deklaracji modelu za naprawę i nie utworzył wersji kandydata.

Osobna pełna rewizja opisana niżej nie jest wynikiem pierwszego przebiegu. Po pokazaniu publicznego briefu i dodaniu
scenariusza do repozytorium CREMA nie jest ślepym holdoutem; służy jako
ograniczona próba transferu narzędzia do innej domeny. Dotychczasowy wynik jest
negatywnym dowodem konkretnej próby, nie przykładem przyjętym do treningu,
odbiorem właściciela, wdrożeniem ani podstawą deklaracji kwalifikacji modelu.


Późniejsza pełna rewizja CREMA naprawiła helper testów i podłączenie zasobów:
7 testów modelu i te same 19 zamrożonych prób HTTP przeszły. Odrębna poprawka
modelu zmieniła tylko HTML/CSS: położenie rozwijanego menu, fikcyjne dane
kontaktowe i polskie etykiety. Końcowa paczka #21 ma checksum
`6fa35f42330f932b72a67cff50b073bb122a5e81817adb7eb5457bb839da0d03`.
Egzaminator viewport.v3 zaliczył 15 kontroli, w tym rzeczywisty tryb file://,
trzy wyceny przez Docker, geometrię/hit-test otwartego menu i ukrycie po Escape.
Pełne screenshoty obu szerokości obejrzano; osobny technical-assessment zapisuje
ograniczony odbiór techniczny. Brak odbioru właściciela, wdrożenia i treningu wag.

Podczas audytu poprawiono też błędny predykat testera: pusty kontener nav może
mieć prostokąt o wysokości zero, choć wszystkie linki są ukryte. viewport.v3
bada widoczność i dostępność linków dla fokusu, zachowując kontrole geometrii.
Ta sama wersja egzaminatora odrzuca źródła sprzed naprawy za menu poza ekranem
i zalicza źródła poprawione. Stare raporty nie zostały nadpisane. To jawna
korekta egzaminatora, nie wsteczne zaliczenie pierwszego transferu.

`scripts/collect_web_code_experience.py` waliduje osobny kandydat doświadczenia
naprawy parsera: surową odpowiedź modelu, model/digest, dokładny diff app.py,
zachowane testy/frontend oraz powiązane surowe wyniki runnera, edge i browsera.
Eksport nie uruchamia treningu ani nie trafia do istniejącego korpusu wizyjnego.
Jeden przykład ROWEROWNIA otrzymał niezależną decyzję
`eligible_for_curated_training`; rodzina i jej bliskie duplikaty są tylko train,
poza ewaluacją. `ready_for_trainer=false`: nadal wymagany jest nowy spójny
zbiór i niezależna ocena transferu. Nie jest to dowód poprawy wag modelu.

### Kuracja doświadczenia do zbioru treningowego

`scripts/curate_web_code_experience.py` przyjmuje trzy lokalne artefakty:
kandydata, manifest dowodów oraz niezależną recenzję o decyzji
`eligible_for_curated_training`. Sprawdza zwykłe pliki w Linux workspace,
brak symlinków, wersje i dokładne pola, hashe oraz wszystkie osiem dowodów.
Ponownie wykonuje walidację collectora i wymaga odtworzenia identycznego
kandydata oraz manifestu; wykrycie zmiany wejść przerywa kurację.

Wyjściem jest nowy, prywatny katalog z `train-candidate.jsonl` w schemacie
`company-sft.v1` oraz `curation-receipt.json`. Rekord ma `split=train` i
recenzję zatwierdzającą kurację. Odpowiedź treningowa zachowuje format
`{"changes":{"app.py":"pełne źródło modelu"}}`. Ścieżki do dowodów są zastąpione
referencjami hash; wiadomości zawierają tylko brief, opis usterki, błędne źródło
i oryginalną poprawkę modelu. Ocena treści nadal wymaga niezależnej recenzji;
narzędzie nie jest ogólnym wykrywaczem danych prywatnych ani parafraz.

Receipt wiąże konkretną zapisaną zgodę na rozwój/trening i hashe wejść, ale nie
deklaruje odbioru produktu przez właściciela. Pełna bramka `validate_dataset`
działa przed zapisem. Pierwszy rzeczywisty rekord ma 1 train, 0 validation,
0 test: `export_ready=false`, `ready_for_trainer=false`, `training_started=false`.
Nie uruchomiono nowego treningu; wymogi zbioru i niewidzianego zadania oceny
pozostają niespełnione.

Przypięty `datasets/qwen/training-only-families-001.json` rezerwuje rodzinę
ROWEROWNIA wyłącznie do treningu. Import validation/test i bezpośrednie loadery
katalogu egzaminów odrzucają tę rodzinę nawet w osobnym pliku lub nowej,
poprawnie zahashowanej wersji egzaminu. Brak lub zmiana rejestru blokują odczyt.
Kurator przypisuje bliskie duplikaty do tej samej rodziny; sam rejestr sprawdza
identyfikatory i nie rozpoznaje automatycznie pokrewieństwa semantycznego.

### Wspólna poprawka HTML/CSS

`collect_web_ui_experience.py` i `curate_web_ui_experience.py` zachowują jedną
modelową interakcję poprawiającą dwa pliki CREMA. Próbka v2 zawiera pełny publiczny
kontekst, dokładny feedback, dwa błędne i cztery zachowane źródła; target to
oryginalne `changes` dla `index.html` i `style.css`. Nie dzieli zależnej naprawy
na dwa pozornie niezależne przykłady. Collector wiąże 7 testów, 19 prób, browser
before/after 14/15 i 15/15, raw model response, assembly i przegląd screenshotów.
Kurator wymaga odrębnej recenzji nauki oraz odtwarza identyczne wejścia przez
ponowną walidację collectora.

Rodzina `service-crema-responsive-nav-copy-development` jest zarezerwowana
wyłącznie do train razem z wcześniejszą rodziną ROWEROWNIA. Wspólna bramka obu
rzeczywistych przykładów daje 2 zatwierdzone train, 0 validation i 0 test.
`export_ready=false`, brak świeżego zastrzeżonego holdoutu, bez nowego treningu
wag. Pokrewne wersje ujawnionych zadań nie są niezależną oceną generalizacji.

## PLAN ZAJĘĆ — katalog z dwoma filtrami

Trzeci syntetyczny scenariusz `workshop_catalog_case.py` ma sześć warsztatów,
filtry dnia i poziomu łączone przez AND, pusty wynik oraz ścisłe API
`/api/sessions`. Pierwsza generacja zaliczyła 16 własnych testów i 17 zamrożonych
prób HTTP; przeglądarka wykazała niedziałające zasoby w trybie file://, a review
pusty katalog przed pierwszą interakcją. Modelowa poprawka HTML/JS dodała
początkowe pobranie sześciu rekordów, polskie etykiety i względne assety.

Osobna diagnostyka wykryła akceptowanie ścieżek ze średnikiem. Kolejne poprawki
modelu były sprawdzane tym samym zestawem czterech prób; dodano jawny piąty
przypadek pustego średnika. Pierwsza poprawka nie działała, kolejna pomijała
pusty parametr, a jedna odpowiedź była identyczna z bazą i została odrzucona.
Końcowa wersja używa parsera zachowującego pełną ścieżkę i zalicza wszystkie pięć
prób. Pozostałe pięć plików, w tym testy modelu, zachowano bajtowo.

Końcowa paczka #36 ma checksum
`e1eb01bd03d6be6e5797c68a84cf924a40eeb9cc7bbac650b97d5d33cd5fcd9b`:
16 testów modelu, 17 frozen probes, 16 kontroli przeglądarki i 5 dodatkowych
prób routingu passed. Pełne screenshoty 1440/390 px i trybu file:// obejrzano;
oddzielny assessment stwierdza ograniczony odbiór techniczny. Kandydat nadal
nie jest odebrany przez właściciela, wdrożony ani zatwierdzony do treningu.

Egzaminator `catalog.v4` dodaje kontrolę sześciu początkowych rekordów i wymaga
rzeczywistego tekstu instrukcji w file://. Ta sama wersja odrzuca pierwotny UI
(14/16) i zalicza naprawiony (16/16). Oryginalne raporty i zamrożony harness
pozostały niezmienione. Rozwijany przykład nie jest ślepym holdoutem.

## Wynik próby zwykłej kolejki filewise

LICZNIK LITER korzysta z normalnych `enqueue/execute` i `application_revisions`,
bez podmiany fabryki na adapter w samym pilocie. Pierwsza próba 16k została
zatrzymana przed piątym wywołaniem przez limit kontekstu; zachowała cztery
odpowiedzi i nie utworzyła częściowej paczki. Jawnie zwięźlejsza druga próba
złożyła sześć plików, ale runner odrzucił wadliwy konstruktor handlera w testach
napisanych przez model.

Pełna rewizja modelu, korzystająca z istniejącego kontekstu rewizji 32k,
naprawiła testy bez zmiany niezależnego harnessu. Sześć wywołań trwało 41,273 s,
2399 tokenów wyjściowych łącznie. Paczka #10
`f54fce4f08227b96b7e2e103f25080aa74224f2254c996145ef5e25f3a47c4b7`
zaliczyła 7 realnych testów HTTP modelu oraz 6 frozen probes/HTML. Pełne raw
evidence jest związane z REPORT artifact w osobnej bazie. To dowód generowania,
kontroli i pełnej rewizji małej aplikacji; nie sukces pierwszej próby, trening
wag, automatyczny odbiór ani włączenie strategii w aktywnej konfiguracji serwera.

Ten sam produkt przeszedł następnie 8 kontroli przeglądarki: formularz z polskimi
literami, zero dla tekstu bez liter, błąd pustego pola bez wywołania API, układ
mobilny i rzeczywisty widoczny komunikat file://. Trzy screenshoty obejrzano;
osobna ocena dotyczy tylko tego zakresu integracji. Nie jest to pełny audyt tras
ani wszystkich granic długości Unicode.

Pierwsze badanie przeglądarki przerwała walidacja podglądu: `encodeURIComponent`
pozostawia `!~*'()`, a query allowlist ich nie dopuszczała. API, broker właściciela
i izolowana ramka akceptują teraz te znaki w zapytaniu. Zachowano lokalne trasy
`/api/nazwa`, limit 800 znaków query i izolację; CR/LF są odrzucane również na
końcu ciągu JavaScript. Poprawka dotyczy systemu, źródła modelu są niezmienione.
Raport nieukończonej próby pozostał obok nowego wyniku 8/8.
