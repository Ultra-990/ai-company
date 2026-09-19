# Wyszukiwarka stron i funkcji

Stan: 2026-09-13. Pole „Znajdź stronę lub funkcję” znajduje się w górnej
nawigacji pulpitu, Spatial, realizacji, budowy, odbioru, publikacji, historii
klientów i pomocy właściciela. W siedmiu panelach operacyjnych dodano również
zwykły odnośnik **Panel klienta ↗**, dostępny bez JavaScript.

## Korzystanie

1. Kliknij pole lub naciśnij Ctrl+K (Command+K na macOS).
2. Wpisz np. „panel klienta”, „testy”, „agenci”, „historia” albo „podgląd”.
3. Kliknij wynik lub użyj strzałek i Enter. Enter w polu otwiera pierwszy
   wynik. Escape zamyka wyniki; Tab działa jak przy zwykłych odnośnikach.

Puste zapytanie pokazuje katalog. Wyszukiwanie ignoruje wielkość liter
i polskie znaki, uwzględnia wszystkie wpisane słowa oraz wybrane synonimy
i literówki (np. „klijenta”, „spartial”). Przy braku wyników pokazuje
podpowiedź zamiast uruchamiać dowolny adres.

## Trzy różne wejścia

- **Panel klienta** (`/client`): logowanie kodem do udostępnionego projektu.
- **Podgląd panelu klienta dla właściciela** (`/os/client-preview`): przykład
  i podgląd właściciela; nie loguje go jako klienta.
- **Publikacje i dostęp klienta** (`/os/publishing`): przygotowanie treści
  i kodów. Historia publikacji i aktywności znajduje się w `/os/clients`.

Wyszukiwarka tylko prowadzi do strony. Nie loguje, nie omija uprawnień,
nie zmienia statusów i nie uruchamia agentów. Nie przeszukuje rzeczywistych
projektów, plików ani klientów. Nie wymaga tokena ani wywołania Qwena.

## Technika i bezpieczeństwo

Katalog 13 stron jest w `navigation-search.js`. Zapytanie jest filtrowane
w pamięci strony, bez wysyłania ani zapisu. Wyniki powstają przez DOM
i textContent, a odnośniki pochodzą wyłącznie ze stałego katalogu.
Po opuszczeniu strony pole jest czyszczone. Nowe trasy należy dopisywać
do katalogu wraz z testami i aktualizacją pomocy.

Skrypt i CSS są dołączane tylko do wewnętrznych paneli. Osobna aplikacja
klienta nie udostępnia tych zasobów ani katalogu właściciela. Pomoc klienta
zachowuje własne wyszukiwanie instrukcji. Wspólna stylistyka respektuje
sześć kombinacji palety i motywu, a wyniki mieszczą się na telefonie.

Testy: `tests/test_navigation_search.py` oraz scenariusze Chrome w
`scripts/check_work_browser.py`. Rzeczywiste API wykonawcze są w scenariuszach
przeglądarkowych zastąpione atrapami. Wyniki kontroli w WORK_LOG.md.
