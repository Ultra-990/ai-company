# Paczki aplikacji ze zdjęciami

Stan 20.09.2026: źródła Python i PNG można zapisać jako jedną niezmienną
wersję zadania, uruchomić w izolacji, obejrzeć, odebrać i pobrać jako wydanie.
Nie trzeba oddzielnie dołączać zdjęć do końcowego ZIP-a. Sam import ani
zaliczenie testów nie zamyka zadania i nie oznacza odbioru klienta.

## Obsługa

1. W `/os/build` połącz się jako właściciel. Rozwiń „Importuj paczkę ze
   zdjęciami”, podaj ID istniejącego zadania i wybierz kompletny plik JSON.
2. „Zapisz i otwórz paczkę” pokazuje inventory i sumę wersji. Uruchom testy
   dopiero po sprawdzeniu wybranej wersji.
3. W historii sprawdź raport, podgląd i wymagania. Zaliczone testy pozwalają
   pobrać ZIP kandydata. Odbiór konkretnej paczki oraz pozytywna gotowość
   pozwalają przygotować zatwierdzone wydanie z instrukcjami PL/EN.
4. Poprawki wymagają ponownego importu całej paczki. Źródła i PNG są zawsze
   razem. Edytor tekstowy i automatyczna naprawa nie obsługują tego profilu.
   Identyczna treść, cel i zadanie otwierają istniejący zapis; zmiana obrazu
   daje nową sumę i nowy artefakt, który nie dziedziczy odbioru.

Plik importu zawiera `purpose` oraz dwie mapy: `files` (ścieżka → UTF-8)
i `images` (ścieżka → kanoniczne base64 PNG, bez prefiksu data URI).
Endpoint właściciela: `POST /api/tasks/{task_id}/workspace-media-packages`.
Odczyt/lista/download korzystają z dotychczasowych workspace-packages.
Powtórny import jest atomowy i nie duplikuje artefaktu. Wylogowanie podczas
czytania pliku w przeglądarce blokuje jego późniejsze wysłanie.

Przygotowanie syntetycznego FORMA z istniejącego, zweryfikowanego ZIP-a:

```bash
.venv/bin/python scripts/check_media_package.py \
  --bundle /home/marcin/ai-company-workspaces/qwen-training/studio-bundle-9spiyivv/forma-candidate.zip
```

Skrypt wypisuje ścieżkę `package-request.json` w nowym prywatnym katalogu
na Linuksie. Dodaje niezmienione niezależne asercje kalkulatora. Nie zapisuje
do aktywnej bazy. Opcja `--run` osobno wykonuje pilot kontenera i osiem prób
HTTP. To narzędzie demonstracji FORMA; API nie przyjmuje dowolnych ZIP-ów.

## Kontrakt i limity

- Osobny manifest `organization-os.workspace-media.v1` i profil
  `python-web-media-v1`; bez zmiany limitów dawnych paczek tekstowych.
  Tekst nazwany `.png` w starym schemacie nie aktywuje nowego wykonawcy.
- Układ Python wielomodułowy: app.py, index.html, README.md, modules/,
  tests/ z unittest, lokalne static/. 8–100 plików. Tekst: 256 KiB na plik,
  1 MiB łącznie. Bez instalowania zależności.
- 1–12 PNG pod static/, 4 MB na obraz, 12 MB łącznie, do 4096×4096,
  pojedyncza klatka. Kontrola formatu, CRC, base64, ścieżek, kolizji i hashy
  przed zapisaniem. Żądanie JSON do 24 MiB. SHA pliku liczone z bytes PNG;
  suma całego manifestu wiąże treść, inventory, cel i zadanie.
- Publiczne trasy muszą oddawać dokładne pliki i właściwy MIME: index.html
  jako `/`, style.css, app.js i static/. `/health` zwraca `status=ok`.
  Podgląd bezstanowego GET: `/` do 18 000 bytes, API do 12 000 bytes,
  cały raport do 30 000 bytes. Bez POST, kont, trwałego zapisu i hostingu.
- Ramka zachowuje opaque origin i istniejące CSP. Obrazy `<img src>`
  wskazujące pliki PNG z paczki otrzymują zweryfikowane data URI.
  Osadzanie przez CSS url(), srcset i dynamiczne pobieranie obrazów nie
  zostało dodane. Brak obrazu wymienionego w inventory blokuje otwarcie.
- Pobierane archiwa zawierają binarne PNG. Podgląd źródła obrazu odmawia
  zwrócenia tekstu; porównanie pokazuje hash/rozmiar i zmianę zamiast diffu
  base64. Eksport na dysk Linux także zapisuje binarne PNG, weryfikuje ich
  hash i zachowuje obce zmiany. Nie ma ekstrakcji ZIP ani wykonania aplikacji
  na hoście.

## Testy i odbiór

Przypięty tester `media_package_harness.py` korzysta z przypiętego wsparcia
profilu wielomodułowego. Zachowane Docker nonroot, readonly, network none,
1 CPU/512 MiB/64 PID/45 s, brak GPU, slot globalny i sprzątanie wyłącznie
własnego kontenera. Najpierw sprawdza izolację, potem testy paczki, bytes/MIME
wszystkich publicznych zasobów i odmowę dostępu do prywatnych źródeł.
Brak assetów nie może dać passed, niepewne sprzątanie pozostawia uncertain.

Zwykłe testy paczki nie są niezależnym dowodem wszystkich wymagań biznesowych.
Odbiór właściciela wiąże źródła i PNG z najnowszym testem tej paczki,
aktualnym testerem i zakresem zadania. Zmiana dowodów, profilu, zakresu,
nowszy test lub wycofanie odbioru blokują wcześniejsze wydanie. Stary
wybrany plan HTTP pozostaje bramką; import PNG nie pozwala go ominąć.
Odbiór w testach odbywa się tylko na syntetycznych zadaniach w tymczasowej DB.

Dowody lokalne, niepublikowane do Git:

- `media-package-pilot-rv0rwxdu/report.json`: passed, 9 wykonań (testy +
  osiem prób), dokładny FORMA ZIP SHA-256
  `957bd21a6c3e61ed5ec77638d4d19c506a2b7d3aa2c488db2b34214bc6890c05`.
- API → kontener → odbiór → ZIP/PNG → podgląd → wynik 2125:
  **1 passed / 1.75 s**. Rzeczywisty test błędnego MIME oraz sześć wariantów
  unieważnienia odbioru: **7 passed / 1.18 s**.
- Headless Chrome przez API: **1 passed / 3.19 s**; trzy obrazy z dokładnych
  data URI mają rzeczywiste wymiary, scena inicjalizuje się w desktopowym
  widoku, kalkulator ma trzy poprawne wyniki i jedną walidację wejścia.
- Regresja Python: **162 passed / 5 skipped / 8.39 s**. Eksport Linux i
  media po domknięciu integracji: **38 passed / 3 skipped / 1.89 s**. Nowe/zmienione
  kontrole Node: **19 passed** (import, wylogowanie, inventory, ramka,
  brak PNG, stare odpowiedzi, obsługa profili w panelu).

Pełny wcześniejszy audit 112 interakcji FORMA i naprawa pierwszego przewijania
są opisane w [STUDIO_BUNDLE.md](STUDIO_BUNDLE.md). Integracja mediów nie jest
ponownym odbiorem wizualnym właściciela ani testem fizycznego Safari/iPhone.
