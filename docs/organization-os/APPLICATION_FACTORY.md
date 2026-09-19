# Fabryka aplikacji — pierwszy działający profil

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

## Izolowany profil wykonania

- Lokalny obraz `python:3.10-slim` przypięty do ID
  `sha256:bef522938ef068e9fe7c1f078b1eb929cf32bbb2047b8e67723996c1e050e6e9`.
  Brak pull przy wykonaniu, brak instalowania zależności. To zastany obraz,
  nie deklaracja najnowszej poprawki bezpieczeństwa.
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
