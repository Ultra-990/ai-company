# Centrum pomocy

Pierwsza wersja: 2026-09-13. Instrukcje powstają równolegle z działającymi
funkcjami; nie czekamy na ukończenie całej firmy.

## Dostęp

- Właściciel: `/os/help` — 10 instrukcji, od zlecenia i tokena po Qwena,
  podgląd aplikacji, automatyczne naprawy, odbiór i publikacje.
- Klient: `/client/help` — 7 instrukcji: kod, workflow, materiały, uwagi,
  wymagania, kontakt i prywatność.
- Przycisk **Pomoc** w nawigacji pulpitu, Spatial, realizacji, budowy,
  odbioru, publikacji, historii klientów oraz panelu klienta.
- W Budowie i testach bezpośrednie odnośniki do automatycznych napraw
  (`/os/help#automatic`) oraz wstrzymanego wydania (`/os/help#release`).

Instrukcje nie wymagają tokena — wyjaśniają również pierwsze logowanie.
Nie zawierają danych projektów, kodów dostępu ani sekretów. Osobna aplikacja
`app.client_main` udostępnia wyłącznie pomoc klienta; `/os/help` zwraca tam 404.
Nie jest to automatyczne publiczne wdrożenie ani zastępstwo zabezpieczeń API.

## Obsługa

W panelach właściciela jest także osobne pole „Znajdź stronę lub funkcję”
(Ctrl+K), opisane w [wyszukiwaniu nawigacji](NAVIGATION_SEARCH.md).
Prowadzi np. do panelu klienta lub testów. Poniższe wyszukiwanie w centrum
pomocy filtruje natomiast treść instrukcji, nie strony aplikacji.

Wyszukiwanie filtruje lokalnie wszystkie słowa zapytania, ignorując wielkość
liter i polskie znaki. Zapytania nie są wysyłane na serwer ani zapisywane
w pamięci przeglądarki. Escape lub Wyczyść przywraca listę. Każdy temat ma
stały odnośnik, który otwiera instrukcję i ustawia fokus na jej nagłówku.

„Drukuj instrukcje / zapisz PDF” otwiera drukowanie przeglądarki. Na czas
wydruku rozwijane są wszystkie instrukcje bieżącej roli, także odfiltrowane;
potem wraca wcześniejszy stan. Zapis PDF zależy od możliwości przeglądarki.
Treść i rozwijane instrukcje są dostępne bez JavaScript; wyszukiwanie,
automatyczne rozwinięcie do druku i kontrolki motywu wymagają JavaScript.

Palety neutralna, zielona i niebieska oraz tryby jasny/ciemny są wspólne
z aplikacją. Układ zwęża się do jednej kolumny na telefonie. Pomoc nie jest
czatem, systemem zgłoszeń ani agentem podejmującym działania.

## Źródła i utrzymanie

- `app/help_content.py`: jedyne źródło redakcyjnej treści OWNER/CLIENT;
  identyfikatory tematów są stabilne, data UPDATED oznacza weryfikację treści.
- `app/api/help_center.py`: bezstanowy render HTML z escapowaniem tekstów,
  bez zapytań do bazy i wywołań modelu.
- `app/static/organization-os/help.js`, `help.css`: wyszukiwanie, druk,
  dostępność i wygląd; wspólne zasoby nie zawierają instrukcji właściciela.

Przy zmianie funkcji należy w tym samym zestawie zmian zweryfikować opis,
nazwy przycisków, ograniczenia, odnośniki i datę aktualizacji. Nie obiecujemy
automatycznej synchronizacji dokumentacji z kodem ani generowania pomocy
z niezweryfikowanych odpowiedzi modelu. Planowane konta e-mail, płatności,
hosting i automatyczny transfer aplikacji nie są opisane jako dostępne.

## Weryfikacja

`tests/test_help_center.py` sprawdza trasy, katalogi, odnośniki, escapowanie,
izolację aplikacji klienta, zasoby oraz obecność nawigacji. Wykorzystuje
izolowane fixture testowe, nie prawdziwe projekty.

`scripts/check_work_browser.py` sprawdza także wyszukiwanie z polskimi znakami,
pusty wynik, odnośniki/fokus, przywracanie stanu po drukowaniu, palety,
telefon i działanie treści bez JS. Operacyjne API są atrapami; test nie
wykonuje zmian projektów ani inferencji. Wyniki: `docs/WORK_LOG.md`.
