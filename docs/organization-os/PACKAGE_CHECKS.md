# Kontrola plików paczki — profil statyczny v1

Stan: 2026-09-12. Działający analizator zapisanych plików, **nie runner kodu**.
Nie uruchamia modeli, przeglądarki projektu, shell, kontenerów, instalatorów
ani kodu dostarczonego w paczce. Nie otwiera plików hosta i nie pobiera URL.

## Obsługa w centrum realizacji

1. Otwórz `/os/work`, połącz się tokenem Owner i wybierz zlecenie.
2. Przy istniejącej paczce źródeł kliknij **Sprawdź pliki**.
3. Poniżej zobaczysz wynik, ID paczki, SHA-256 źródła, problemy z nazwami
   plików/wierszami oraz listę rzeczy, których nie sprawdzono.
4. Wśród artefaktów powstaje **test_result**. **Otwórz raport kontroli**
   odczytuje zapisany wynik, ponownie weryfikując integralność paczki.

Zmodyfikowaną stronę zapisz jako **nową paczkę** istniejącym panelem źródeł
i sprawdź tę wersję. Dawny raport nie jest automatycznie dowodem dla nowych
plików. Powtórne kliknięcie kontroli tworzy nowy raport, nie nadpisuje starego.
Po niepewnej odpowiedzi zapisu odśwież listę artefaktów przed ponowieniem.

## Co sprawdza ten profil

- Integralność manifestu, rozmiary UTF-8 i SHA-256 wszystkich plików.
- Dla `.html` / `.htm`: deklaracja HTML5, niepusty język i tytuł dokumentu,
  viewport, jeden h1 i jeden obszar main, powtórzone identyfikatory,
  obecność atrybutu alt obrazów.
- Wykrywa lokalne `href` i `src`, sprawdza istnienie ścieżki w paczce,
  a dla rozpoznanego dokumentu HTML — również docelowego ID fragmentu.
  Rozwiązuje ścieżki względem katalogu HTML, dopuszcza odnośniki od korzenia
  paczki i nazwę `index.html` dla ścieżki zakończonej `/`.
- Dla `.json`: składnia standardowego JSON (bez NaN/Infinity), z limitem
  zagnieżdżenia 128. Nie sprawdza schematów danych biznesowych.
- Aktywne elementy i adresy zewnętrzne zaznacza jako wymagające oddzielnej
  kontroli. Schematy `javascript`, `vbscript`, `file`, `data` zgłasza jako
  problem tego profilu. W raporcie nie zapisuje surowych adresów z query string.

To reguły **ograniczonego profilu jakości**, nie pełny walidator standardu HTML,
audyt dostępności ani bezpieczeństwa. Przykładowo obecność alt nie potwierdza
poprawności jego treści, a zaliczenie viewport nie potwierdza układu na telefonie.
Poprawność składni CSS/JS, srcset, adresy w CSS, routing frameworków, DOM
tworzony przez JS oraz działanie formularzy pozostają poza zakresem.
Element `base` powoduje pominięcie odnośników danego dokumentu i niepełny wynik.

## Znaczenie wyników

- `checks_passed`: wykonane kontrole profilu nie wykazały błędów; mogą nadal
  występować ostrzeżenia. Nie oznacza działającej ani bezpiecznej aplikacji.
- `issues_found`: wykryto przynajmniej jeden problem profilu.
- `incomplete`: brak obsługiwanych dokumentów lub analiza została ograniczona.

Limit: do 400 wpisów wyniku oraz do 10000 znaczników na dokument HTML.
Limit paczki pozostaje bez zmian: 100 plików, 256 KiB na plik, 1 MiB łącznie.
Po osiągnięciu limitu raport nie może udawać pełnej kontroli. Wynik wskazuje
`analysis_incomplete`; przy wcześniej znalezionych problemach zachowuje
`issues_found`. Limity nie zmieniają konfiguracji procesu Python ani hosta.

Każdy raport ma `code_executed: false` i `product_accepted: false`.
Nie zatwierdza zadania, nie tworzy próby wykonawcy, nie zmienia postępu,
nie odbiera projektu i nie publikuje niczego klientowi.

## API i trwałość

Wymagany Bearer Owner; Worker otrzymuje 403. Wszystkie odpowiedzi sukcesu
zawierają `Cache-Control: no-store`.

- `POST /api/tasks/{task_id}/workspace-packages/{package_id}/static-check`
  tworzy raport (201), bez ciała żądania i bez możliwości przekazania polecenia.
- `GET /api/tasks/{task_id}/static-checks/{report_id}` odczytuje raport (200).
- 404: brak paczki/raportu dla wskazanego zadania; 409: naruszona integralność;
  503: błąd repozytorium, wymagane sprawdzenie zapisu przed ponowieniem.

Raport to istniejący model `Artifact`, typ `TEST_RESULT`, nazwa
`organization-os.static-check.v1`, bez nowej tabeli/migracji. Treść zawiera
ID zadania, ID paczki, sumę źródła, wersję kontrolera, kontrole i ograniczenia.
Sam raport ma własną sumę SHA-256. Artefakt i zdarzenie audytu
`package_static_check` są zapisywane w jednej transakcji.

Odczyt sprawdza sumę raportu, zgodność zadania/odnośnika i integralność źródła.
Sumy nie są podpisem chroniącym przed administratorem, który może zmienić
jednocześnie dane i hashe w bazie. Brak testu wykonania pozostaje jawny również
po pobraniu lub ponownym odczycie raportu.

## Testy

`pytest -q tests/test_package_checks.py`: poprawny szkielet, brakujące elementy
i pliki, odnośniki, zewnętrzne URL, limity, JSON, zapis/odczyt i integralność,
RBAC, powiązanie z zadaniem, brak zmiany postępu i wykonania dołączonego Python.

`python scripts/check_work_browser.py`: izolowany Chrome z wyłączonym GPU,
całe API symulowane; kontrola przycisku, raportu, bezpiecznego tekstu,
ponownego odczytu, mobile i czyszczenia danych. To test UI, nie przeglądarkowy
test wygenerowanej aplikacji.
