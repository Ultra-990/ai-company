# Projekty Python z wieloma modułami

Stan 19.09.2026: wdrożona **kontrola struktury i składni w panelu**, przygotowany
adapter wykonawczy i tester kontenerowy. Pięć rzeczywistych scenariuszy pilota
kontenerowego przeszło po potwierdzeniu zakończenia wynajmu. Nowy profil **jest
dostępny do testowania przez API/panel**, z trwałymi raportami, bezstanowym
podglądem w przeglądarce, odbiorem konkretnej paczki i zatwierdzonym ZIP-em
z instrukcjami dla klienta. Pozostaje integracja automatycznych napraw.
Istniejący płaski `python-web-v1` pozostaje
bez zmian kontraktu. [Zapis wyników pilota](evidence/multifile-pilot-20260919.json).

## Co można zrobić teraz

W `/os/work`, przy odebranym zakresie i gotowym etapie wykonawcy, przygotuj
instrukcję i wybierz **Qwen: zbuduj aplikację z osobnymi modułami**. Nowy
`output_profile: python-web-multifile-v1` korzysta z istniejącej kolejki
LocalInference, przypiętego modelu i kontroli uprawnień. Generuje 7–16 plików,
w tym `modules/logic.py` i `tests/test_logic.py`. Ścieżki, składnia Pythona,
duplikaty JSON i rozmiar są sprawdzane przed atomowym zapisem paczki/próby.
Wygenerowany kod nie jest wykonywany na hoście. Opcja testów po generowaniu
uruchamia istniejący izolowany runner; sam zapis nie zmienia postępu zadania.
Pełna regeneracja jako poprawka jest zablokowana, aby nie zastępować testów
nowymi napisanymi pod wadliwe rozwiązanie. Korekty ręczne tworzą nową wersję;
automatyczne naprawy modułowe wymagają dalszej integracji.

To profil małych bezstanowych aplikacji Python/HTML, nie generator dowolnego
stosu, płatności, kont użytkowników czy modeli muzyki/wideo. Zachowuje
ograniczenia stdlib, lokalnych zasobów oraz GET opisane niżej.

Sprawdzenie 19.09: rzeczywisty Qwen utworzył siedmioplikowy kalkulator
wyceny; 11 metod testowych i 7 kontroli HTTP przeszło w kontenerach.
Chrome sprawdził pięć interakcji formularza oraz izolację ramki.
[Dowody i ograniczenia](evidence/qwen-multifile-20260919.json).
`scripts/check_qwen_multifile.py` domyślnie tylko wyświetla plan. `--run`
uruchamia model i kontenery; wymaga wolnych zasobów i kontroli wynajmu.
Każdy wynik, także błąd, zostaje w prywatnym katalogu pilota na Linuksie.
Nie tworzy ani nie odbiera rzeczywistego zlecenia, nie eksportuje danych
do treningu. Testy API są osobno wykonywane na bazie tymczasowej.

W `/os/build` wczytaj paczkę niezgodną z dotychczasowym runnerem i wybierz
**Sprawdź strukturę i składnię — bez uruchamiania**. Otrzymasz konkretne ścieżki
i numery wierszy wymagające poprawy. Edycja tworzy nową paczkę; kontroluj nową
wersję ponownie. Wylogowanie i zmiana paczki usuwają poprzedni widok.

Kontrola odczytuje wyłącznie zweryfikowany manifest. Nie importuje źródeł,
nie uruchamia testów, modelu ani kontenera, nie zapisuje artefaktu i nie zmienia
procentów lub statusów. Odpowiedź ma identyfikatory zadania/paczki i SHA-256,
`compatible`, `issues`, `test_files`, `executed: false`, `tests_passed: null`,
`can_execute: false`, `runtime_status: tests_available`. Pierwsze pole oznacza,
że kontrola struktury nie jest zgodą na wykonanie. Dostępne operacje podaje
osobno `capabilities` metadanych paczki i wykonania.

API właściciela:
`GET /api/tasks/{task_id}/workspace-packages/{package_id}/multifile-inspection`.
Istniejące uwierzytelnienie, brak dostępu workera/klienta, `no-store` i
kontrola integralności. Nie jest to upoważnienie do wykonania.

## Uruchomienie, raport i kandydat

1. Wczytaj paczkę o zgodnym układzie. Panel pokazuje profil wielomodułowy;
   metadane zawierają `execution_profile: python-web-multifile-v1`.
2. Zaznacz zgodę i wybierz **Uruchom aplikację i testy w izolacji**. Korzysta
   z istniejącego `POST /api/package-runs`: task_id, package_id, SHA-256,
   request_id i confirm_execution. Profil dobiera serwer; klient nie może
   podać polecenia, obrazu, sieci lub profilu do obejścia walidacji.
3. Historia pokazuje zapisany raport z profilem, sumą testera, paczką i jej
   sumą. Powtórzenie tego samego UUID zwraca ten sam wynik, bez kolejnego
   kontenera. Zmienione dane dają konflikt. Limit trzech prób tej wersji,
   wspólny slot i uzgadnianie niepewnego stanu pozostają zachowane.
4. Po zaliczeniu pobierz **ZIP kandydata do odbioru**. Zawiera katalogi źródeł,
   raport, manifest i polecenie testów `python -m unittest discover -s tests
   -t . -p "test_*.py" -v`. Nie jest zatwierdzonym wydaniem dla klienta.
5. Przy błędzie otwórz pliki, popraw implementację w nowej paczce i testuj
   nową wersję. Nie dziedziczy ona wyników starej wersji ani jej odbioru.

Automatyczna naprawa Qwen nie jest jeszcze obsługiwana dla nowego profilu.
Panel nie pokazuje jej przycisków. Stary płaski profil zachowuje swoje
istniejące możliwości. Samo zaliczenie testu nie zmienia Task.progress.

### Odbiór wersji i wydanie dla klienta

W historii zaliczonego wykonania wybierz **Odbierz lub wycofaj odbiór tej paczki**.
Formularz pokazuje zakres zadania, SHA źródeł i raportu. Opisz sprawdzone
kryteria oraz dowody/ograniczenia, wybierz decyzję i zaznacz potwierdzenie.
Następnie **Sprawdź gotowość do przekazania** i **Przygotuj i pobierz
zatwierdzone wydanie**. ZIP zawiera źródła, raport, manifest, instrukcje PL/EN,
metrykę plików i dowodów. Wiadomość do klienta pozostaje szkicem do ręcznego
wysłania przez właściciela na Upwork. Prywatne notatki odbioru nie są kopiowane
do dokumentów klienta. Wydanie nie wdraża aplikacji ani nie zawiera logowania.

Odbiór paczki jest odrębny od odbioru TaskAttempt: nie zmienia statusu zadania,
postępu, aprobaty klienta ani delegacji. Pozwala odebrać także nową wersję
z edytora bez fałszywego przypisania jej do starej odpowiedzi modelu.
Wymaga najnowszego zaliczonego testu tej paczki w aktualnym profilu.
Wiąże źródła, raport, profil oraz tytuł/opis/projekt/plan/etapy zadania.
Zmiana tych danych wymaga ponownej kontroli; brak automatycznego dziedziczenia.
Zmiana testów/profile lub wycofanie odbioru blokuje dalsze pobieranie wydania.
Już pobranego pliku ZIP nie można zdalnie wycofać.

Każda decyzja to niezmienny Artifact i AuditEvent. Idempotentny UUID nie
przywraca starej akceptacji po nowszym odrzuceniu. Ponowny odbiór tworzy nowe
powiązanie wydania; wcześniejsze zapisy pozostają historyczne.

API właściciela: GET/POST `/api/package-runs/{run_id}/package-review`.
GET zwraca `binding`, `context_checksum` i stan decyzji. POST: `request_id`,
`context_checksum`, `accepted`, `criteria`, `evidence`, `confirm_review: true`.
Zmieniony zakres od czasu GET skutkuje konfliktem zamiast cichego odbioru.
Endpointy release/released.zip/handoff pozostają wspólne z poprzednim profilem.
Jeżeli zadanie ma wybrany plan HTTP starego cyklu quality, odbiór paczki jest
blokowany: nowa ścieżka nie może ominąć obowiązujących kryteriów. Wykonanie
takiego planu dla nowego profilu pozostaje kolejnym etapem.

### Podgląd działającej aplikacji

Po zaliczonym wykonaniu wybierz **Otwórz aplikację w izolacji**. Istniejąca
ramka ma nieprzezroczysty origin (bez allow-same-origin), brak tokenów,
brak sieci i brak dostępu do dokumentu właściciela. API zwraca wyłącznie
publiczne CSS i klasyczny JS z głównego katalogu oraz `static/`, nie Python,
testy lub README. Odwołania w HTML muszą być dokładnymi lokalnymi ścieżkami.
Zewnętrzne adresy, `..`, importy modułów JS i ładowanie zależności nie są
obsługiwane. CSS wymagający dodatkowych zasobów sieciowych może się różnić.

Każde GET `/` albo `/api/nazwa` startuje nowy kontener; podgląd nie zachowuje
sesji ani danych pomiędzy żądaniami. Nie ma POST, płatności, logowania,
trwałych zapisów, WebSocketów ani dostępu do portów hosta. Obowiązują limity
30 żądań w otwartym podglądzie, 120 zapisanych żądań na wersję i 12 KB
odpowiedzi HTTP. Odczyt podglądu to osobny `previewed`, nigdy `passed`.
Nowy tester ma pełną kontrolę izolacji, własny schemat i przypięty SHA pilota.

19.09 sprawdzono rzeczywisty HTTP i przeglądarkę Chrome (GPU wyłączone,
prywatny profil, syntetyczna tymczasowa baza). Test potwierdza style z
static/site.css, działanie static/app.js, wynik 8 × 322 = 2576 oraz odmowę
dostępu ramki do parent.document. Nie stanowi odbioru wizualnego produktu.

## Kontrakt `python-web-multifile-v1`

```text
app.py                   punkt startowy HTTP
index.html               interfejs
README.md                obsługa, uruchomienie i ograniczenia
modules/
  __init__.py
  logic.py               własne moduły, także podpakiety
tests/
  __init__.py
  test_logic.py          unittest; dozwolone podpakiety z __init__.py
static/                  opcjonalne lokalne HTML/CSS/JS/JSON/TXT
```

- Opcjonalne główne `style.css` i `app.js`. Inne pliki główne, instalatory,
  manifesty zależności i nadpisanie testera są odrzucane przez profil.
- Python 3.10 stdlib. Brak pip, shellowych poleceń klienta, instalacji,
  pobierania zasobów i zewnętrznych API. Każdy pakiet Python ma `__init__.py`;
  tylko ten plik może być pusty. Nazwy modułów muszą być identyfikatorami.
- Dotychczasowe limity: 100 plików, 256 KiB/plik, 1 MiB/paczka; maksymalnie
  sześć segmentów ścieżki. Pliki UTF-8, bez ścieżek bezwzględnych, `..`,
  ukrytych segmentów, kolizji plik/katalog lub samej wielkości liter.
- Parser AST sprawdza składnię, nie importuje kodu. Nie rozstrzyga dostępności
  wszystkich importów (zwłaszcza dynamicznych), bezpieczeństwa ani poprawności.
  Nazwa test_*.py nie dowodzi obecności lub jakości asercji.
- Aplikacja ma korzystać z HOST/PORT, udostępniać GET `/health` (JSON status ok)
  i `/` (HTML5), bez udostępniania kodu, katalogów i danych hosta.

## Wykonawca i granice zaufania

`MultifilePilotRunner` wykorzystuje istniejący ContainerRunner: przypięty obraz,
globalną blokadę slotu, nieuprzywilejowanego użytkownika, seccomp/AppArmor,
brak sieci/GPU i zapisywalnych źródeł, 1 CPU, 512 MiB, 64 PID i 45 s.
Przyjmuje wyłącznie niezmienioną konfigurację obliczoną po stronie serwera.
API wybiera adapter z walidowanego układu źródeł, nie z nazwy podanej przez
klienta. Zmiana SHA testera względem zaliczonego pilota blokuje nowe wykonanie.
Zmiana źródeł lub konfiguracji w trakcie działania nie daje wyniku passed.

Staging waliduje całą paczkę przed zapisem; zapisuje tekst w nowym prywatnym
katalogu, bez ekstrakcji archiwum, symlinków, nadpisywania i bitów wykonania.
Pliki dostają 0444, katalogi 0755 dopiero po przygotowaniu. Nie jest to ochrona
przed innym złośliwym procesem tego samego użytkownika hosta. Katalog tymczasowy
i jego sprzątanie należą do istniejącego runnera.

Nowy tester zachowuje kontrolę izolacji przed kodem klienta. Uruchamia unittest
rekurencyjnie, odrzuca zero testów, błąd i timeout. Dopiero po zaliczeniu testów
uruchamia serwer. Dodaje wyłącznie `/workspace` do ścieżki modułów **wewnątrz
kontenera**, zachowując `-I -S -B`. Sprawdza HTTP oraz próbę udostępnienia każdego
niepublicznego pliku, nie tylko app.py. Limity czasu i logów nadal obowiązują.
Kontener współdzieli jądro hosta: nie traktować go jako wystarczającej granicy
dla celowo wrogiego kodu. Testy smoke nie zastępują kryteriów klienta.

## Dalsza kolejność prac i dowody

1. Zakończone: walidacja, podgląd problemów w API/UI, staging, adapter
   i tester, testy lekkie z atrapami.
2. Zakończone 19.09 po **jawnym potwierdzeniu końca wynajmu**: sekwencyjny pilot
   pięciu scenariuszy z `scripts/check_multifile_isolation.py`: success,
   no-tests, failed-test, timeout, source-leak. Każdy wynik zgodny z oczekiwaniem;
   każdy kontener posprzątany. To aplikacja syntetyczna, nie odbiór klienta.
   Kolejne zmiany testera wymagają nowej weryfikacji; zapis identyfikuje jego SHA.
3. Zakończone: podłączenie do trwałych PackageRun, odrębnego kontraktu raportu,
   panelu i eksportu kandydata. Rzeczywisty test API na syntetycznej bazie:
   wykonanie → raport → ZIP → idempotentne ponowienie, bez zmiany postępu.
   Podgląd HTTP i ramka z publicznymi CSS/JS również wdrożone i sprawdzone.
   Wdrożono także oddzielny odbiór paczki (w tym wersji z edytora), wydanie
   i dokumenty klienta. Sprawdzono rzeczywisty pilot API do gotowego ZIP-a.
   Stary raport nie zatwierdza nowego profilu ani nowych źródeł.
4. Następnie generowanie/naprawy wielomodułowe z Qwen, pomiar jakości i kosztu
   na tych samych kryteriach; bez automatycznego edytowania testów odbiorczych.
5. Osobny etap: zatwierdzane zależności, trwałe dane, integracje i import
   repozytoriów. Obecny profil nie udaje tych zdolności.

Bezpieczna kontrola samego planu (bez Dockera):

```bash
.venv/bin/python scripts/check_multifile_isolation.py
```

Skrypt domyślnie tylko analizuje dane. Realne wykonanie wymaga jednocześnie
`--run` i `--rental-ended`; tej drugiej opcji nie podawać przed potwierdzeniem
właściciela. Skrypt nie monitoruje wynajmu i nie zmienia jego usług.
Nie pobiera obrazu zastępczego. Nie zapisuje do produkcyjnej bazy ani nie
publikuje wyniku klientowi.
