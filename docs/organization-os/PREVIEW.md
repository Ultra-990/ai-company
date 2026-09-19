# Statyczny podgląd paczki

Stan: 2026-09-12. Dostępny w `/os/work` przy paczkach źródeł jako
**Podgląd strony**. Otwiera modal z podglądem szerokim lub telefonicznym
(390 px, ograniczone dostępnym miejscem na mniejszym ekranie). Nie jest
emulatorem telefonu ani testem na fizycznym iPhonie. Escape / Zamknij usuwa
dokument z ramki. Wylogowanie i opuszczenie karty również czyszczą podgląd.
Podczas oglądania wstrzymane jest automatyczne odświeżanie listy zleceń.

## Co działa

- Odczyt konkretnego artefaktu po sprawdzeniu manifestu, SHA-256 i zadania.
- `index.html` z głównego katalogu oraz wskazane przez `link rel=stylesheet`
  pliki `.css` z tej samej paczki. Obsługiwane ścieżki dokładne i prefiks `./`;
  brak rozwiązywania zewnętrznych URL, query string i importowania plików hosta.
- Czytelny identyfikator paczki, zadania i suma źródła poza ramką.
- Zwykłe elementy struktury HTML, tekst, klasy CSS, wybrane atrybuty ARIA.

Limity: 5000 znaczników otwierających, 128 poziomów dopuszczonego HTML,
128 KiB wskazanych arkuszy CSS. Obowiązują też istniejące limity paczek.
Brak `index.html` lub przekroczenie limitu powoduje odmowę, nie pozornie
kompletny obraz. Podgląd jest przekształcony: nie dowodzi zgodności pełnego
produktu, dostępności, działania JavaScript, backendu lub formularzy.

## Izolacja i ograniczenia

API zwraca **JSON**, nigdy publiczną stronę HTML pod originem właściciela.
Dokument trafia wyłącznie do `iframe srcdoc` z pustym `sandbox` — bez
`allow-scripts`, `allow-same-origin`, formularzy, popupów, pobierania i nawigacji
głównej karty. Nie jest wstawiany do DOM panelu. Ramka ma odrębny opaque origin;
token Bearer pozostaje w pamięci strony właściciela, nie w dokumencie podglądu.

Warstwy ograniczenia:

1. Serwer odtwarza ograniczony zestaw znaczników i atrybutów. Nie jest to
   ogólny sanitizer dowolnej aplikacji. Usuwa wszystkie atrybuty URL/event/style;
   pomija skrypty, style inline, iframe, SVG, MathML, szablony i multimedia.
   Formularze nie są aktywne, przyciski są disabled, odnośniki nie nawigują.
2. CSP dokumentu: `default-src 'none'`, `script-src 'none'`,
   `style-src data:`, pozostałe źródła, formularze i base wyłączone.
   CSS jest kodowany jako arkusze `data:text/css;base64`, a nie składany
   z niezweryfikowanego tekstu wewnątrz `<style>`. Pobieranie sieciowe CSS,
   fontów, obrazów i ramek blokuje CSP.
3. Sandbox przeglądarki pozostaje włączony niezależnie od filtrowania HTML.
   Panel nie odbiera `postMessage` i nie nadaje ramce uprawnień.

Polityka `/os/work` dopuszcza `data:` **tylko dla arkuszy stylów**, aby ramka
mogła je odziedziczyć. Nie dodano `unsafe-inline` ani `unsafe-eval`. Pozostałe
strony, np. portal klienta, zachowują wcześniejszą politykę.

CSS nadal jest interpretowany przez przeglądarkę. Limity rozmiaru nie stanowią
twardego limitu CPU/RAM ani ochrony przed błędami samej przeglądarki. To lokalny,
właścicielski podgląd ograniczonych paczek, nie hosting wrogiego kodu. Pełne
aplikacje wymagają osobnego środowiska, zasobów i dalszych testów bezpieczeństwa.
Nie dodawać uprawnień sandbox w celu „naprawienia” brakujących funkcji.

Podstawy zachowania ramki i polityk:
[MDN: srcdoc i izolacja sandbox](https://developer.mozilla.org/en-US/docs/Web/API/HTMLIFrameElement/srcdoc),
[MDN: Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy).

## API i testy

`GET /api/tasks/{task_id}/workspace-packages/{package_id}/preview`

Wymaga Bearer Owner. Odpowiada JSON, `no-store`, `nosniff`. 404 brak paczki
dla zadania; 409 integralność; 422 poza profilem; 503 baza niedostępna.
Nie zapisuje artefaktu odbioru, nie zmienia statusów i nie wywołuje wykonawcy.

`pytest -q tests/test_package_previews.py` sprawdza filtrowanie, limity,
autoryzację, wiązanie wersji, realny CSS szablonu i brak zmian postępu.
`python scripts/check_work_browser.py` sprawdza CSS w ramce, blokadę skryptu
(również celowo dodanego za filtrem), brak dostępu do rodzica, blokadę sieci,
modal, Escape, szerokość, mobile i czyszczenie sesji. API i treść są testowe,
Chrome ma wyłączone GPU. Obsługiwany jest osobny proces ramki w Chromium.
Test sieci ma dodatkową blokadę przechwytywania żądań, gdyby zawiodło CSP.

Nie uruchomiono modeli, projektowych skryptów, serwera projektu ani kontenera.
Windows, konfiguracja Linuksa i procesy Vast.ai pozostają poza tą funkcją.
