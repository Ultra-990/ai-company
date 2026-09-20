# Trzy strony testowe — 20.09.2026

Właściciel podał trzy nowe briefy: sprzedaż kolekcji znaczków, portfolio
zespołu trance z muzyką i filmem przewijanym kółkiem oraz trzy gry kasynowe
na wirtualne żetony. Powstały trzy kompletne lokalne prototypy i osobne ZIP-y.
To próba realizacji pod nadzorem; nie zakończenie treningu ani pomiar pełnej
samodzielności modelu.

## Co działa

| Projekt | Funkcje |
| --- | --- |
| Atlas, znaczki | 18 ilustracyjnych pozycji, 6 krajów, 4 kategorie wybrane przez model, wyszukiwanie, sortowanie, galeria poprzedni/następny, torba, pojedyncze egzemplarze, usuwanie i testowe podsumowanie zamówienia |
| Portfolio trance | Własny znak zespołu z dysku, 3 lokalne nagrania, odtwarzanie/pauza, wybór utworu, suwak pozycji i głośności, przykładowe wydarzenia z filtrem miasta, szczegóły i eksport ICS, szkic kontaktu, płynne sekcje |
| Nocturne | Ruletka europejska, automat, blackjack, wspólne 1000 żetonów, stawka 10–500 co 10, jednokrotne pobranie stawki, blokada równoległych rund, historia i nowa sesja |

Film jest oryginalną proceduralną animacją świetlną wyrenderowaną przez
narzędzie asystenta do MP4 H.264: 1280×720, 24 fps, 240 klatek / 10 s.
Nie jest wynikiem sieciowego modelu generowania wideo. Każda klatka jest
kluczowa, aby seek był szybki. Naturalny scroll przesuwa currentTime w obie
strony; bez preventDefault na wheel i bez sterowania fokusem. Reduced motion
pozostawia statyczny kadr. Muzyka startuje po kliknięciu; ukrycie zatrzymuje
odtwarzanie bez samoczynnego wznowienia.

Ilustracje znaczków są autorskimi SVG, nie zdjęciami autentycznych egzemplarzy.
Katalog i ceny są oznaczone jako demonstracyjne. Brak pobierania płatności,
zapisu zamówień na serwerze i rzeczywistej sprzedaży biletów. Żetony nie mają
wartości pieniężnej. Stan torby i gier dotyczy bieżącej karty.

## Wkład modelu i nadzór

`scripts/web_trials/generate.py` wywołuje przypiętego lokalnego Qwena
sekwencyjnie. Oryginalne propozycje, prompt, digest i odpowiedzi zachowano
w prywatnych raportach. Kod modelu nie jest importowany ani wykonywany na
hoście; sprawdzenie JS odbywa się w osobnym headless Chrome z izolowaną ramką.

- Znaczki: koncepcja, dane i kategorie oraz filterProducts/cartTotal;
  12.503 s, 1582 tokeny.
- Muzyka: koncepcja oraz scrollTime/formatTime/filterEvents;
  10.523 s, 1127 tokenów.
- Gry: koncepcja i blackjackValue/roulettePayout/slotPayout;
  9.501 s, 1117 tokenów.

Moduły logiki przeszły niezależne przypadki bez poprawiania ich kodu.
Asystent wykonał HTML/CSS, interakcje i zarządzanie stanem, SVG, film,
kopiowanie mediów, integrację, testy i poprawki responsywności. W katalogu
ujednolicono określenie stanu „Świeży” na „Czysty — przykład”; oryginalna
odpowiedź modelu pozostała bez zmian. Koncepcja znaczków została zwrócona
po angielsku mimo prośby o polski — nie jest to dowód bezbłędnej zgodności.
Danych tych projektów nie dopisano do treningu ani odłożonego benchmarku.

## Podgląd i pliki

Lokalny katalog: `/home/marcin/ai-company-workspaces/three-sites-ufpa30po`.
Podkatalogi stamps/music/casino zawierają komplet stron; downloads zawiera
samodzielne ZIP-y. Evidence zawiera raporty i zrzuty, niedostępne przez HTTP.
Logo, okładka i MP3 zostały skopiowane z Windows, zamontowanego read-only;
oryginały nie są modyfikowane. Pochodzenie i sumy zapisano lokalnie.
Media właściciela, gotowe paczki i surowe raporty nie trafiają do publicznego Git.

```bash
.venv/bin/python scripts/web_trials/serve.py \
  /home/marcin/ai-company-workspaces/three-sites-ufpa30po \
  --bind 10.0.0.57 --port 33117 --minutes 240
```

Adres zależy od aktualnego LAN. Nie uruchamiać drugiego serwera na zajętym
porcie. `/stamps`, `/music`, `/casino` to trzy zakładki; górny pasek umożliwia
przełączanie i pobranie ZIP-a. Domyślny bind narzędzia to loopback.

Podgląd wczytuje tylko dozwolone pliki z poprawnymi hashami, do 40 MB na plik
i 100 MB łącznie. Host jest dokładnie sprawdzany. Źródła i media są serwowane
z pamięci, bez uruchamiania projektu na hoście. Ramka oraz nagłówek CSP
wymuszają sandbox bez same-origin, sieci aplikacji i nawigacji rodzica.
Obsługa Range/206/416 pozwala przewijać rzeczywiste audio i wideo. POST,
dowolne pliki hosta, raporty i API firmy są niedostępne. Archiwa mają stałe
czasy i kolejność plików, binarne media i manifest accepted/deployed=false.

Ten pilot jest osobnym, statycznym torem przeglądarkowym. Nie rozszerza
produkcyjnego profilu Python+PNG o MP3/MP4 i nie omija odbioru zadań.
Samodzielne pliki można odtworzyć przez lokalny serwer HTTP; niczego nie
wysłano klientowi i nie wdrożono na publicznym hostingu.

## Weryfikacja

- `evidence/browser-5oeqq9_y/report.json`: **48/48 kontroli**, brak wyjątków
  JS. W zestawie 224 deterministyczne przypadki obliczeń gier, następnie
  rzeczywiste kliknięcia, podwójne kliknięcie, debet, rozliczenia i walidacja.
- Galeria, przejście po kraju, torba i podsumowanie; prawdziwe dekodowanie
  logo/audio/wideo; naturalne wheel w obie strony; play/pause/seek/next;
  ukrycie karty, filtrowane wydarzenie; brak wywołań focus w opóźnionej pracy.
- Desktop 1440×1000, ekrany 390/768/320 px, brak poziomego overflow,
  sprawdzony reduced motion. To Chrome, nie fizyczny Safari/iPhone.
- `tests/test_web_trials.py`: **15 passed / 0.79 s**, w tym zakresy bajtów,
  HEAD, sandbox, odmowa obcego Host i prywatnych tras, zgodność MP3 jako
  bytes, niezmienne ZIP-y i wykrywanie zmiany pliku.
- `evidence/live-preview.json`: odczyt trzech podglądów LAN, zgodność hashy
  wszystkich pobranych ZIP-ów, Range filmu i odmowa prywatnych tras/Host.

Pierwsza próba browser-qrssf8au miała 7 niezaliczonych kontroli: brak logo,
2 problemy szerokości przy 320 px i 4 kontrole reduced motion, ponieważ
emulację zastosowano tylko do procesu rodzica. Poprawiono małe siatki i
transport odtwarzacza; media emulowane również na oddzielnym procesie ramki.
Po znalezieniu logo: browser-mgjo51hj **48/48**. Ostatni przebieg sprawdził
końcową wersję symboli UI i dodatkowy sandbox nagłówka HTTP. Nie osłabiono
asercji modelu. Wcześniejsze logi HTTP odnotowały reset połączenia po
zamknięciu testowej przeglądarki; finalny serwer zamyka odpowiedzi jawnie.

| ZIP | Bytes | SHA-256 |
| --- | ---: | --- |
| stamps.zip | 143211 | `83879bafcd23a2b14635838a4980a7d1b2f003d85f164bfdff969c4c4005ff09` |
| music.zip | 48008329 | `a7c4c0f1d137221f71900ad93e6ef33ddb78b117f2ad36afbd5cd00f38312abc` |
| casino.zip | 30406 | `4cf544010997441d3bc108b0a2db46673ad4a92d5e669f1c0dd1f7cde9ee42cd` |
