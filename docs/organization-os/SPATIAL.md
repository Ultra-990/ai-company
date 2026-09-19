# Spatial lab — prototyp przestrzeni firmy

## Zakres i uruchomienie

Adres: `http://127.0.0.1:8000/os/spatial` na istniejącym serwerze FastAPI.
Dotychczasowy `/os` nie został zastąpiony; ma odnośnik do prototypu.
Wersja atlasu z 2026-09-12 pokazuje wszystkie działy korzenia `ai-company` (obecnie 12),
nie nowy rejestr ani niezależny panel administracyjny agentów. Rozbudowane
operacje wykonawcze nadal są w `/os`; nowa scena jest nawigacją i odczytem danych.
Nie wymaga nowego procesu Node, portu ani zmian konfiguracji hosta.

Kierunek wskazany przez właściciela: cipher.tv, otsuka-air.jp, sharplink.com;
przejścia mają eksponować wybraną treść i zachowywać pełną funkcjonalność. Nie kopiujemy ich kodu,
zasobów, znaków ani nie deklarujemy, że używają identycznej technologii.
Automatyczny odczyt Cipher udostępnił tylko ekran ładowania, nie ocenę animacji.
Własna kompozycja: duża typografia, stonowane tło, metaliczne obiekty, warstwy,
kolorowe operacje okien i aktywny dział przybliżany kamerą.

## Technologia

- Three.js **0.186.0**, przypięte w `frontend/spatial/package.json` i lockfile.
- WebGL: rzeczywiste sfery, oświetlenie, materiały i wytłaczane
  ramy okien. Bez ciężkiego postprocessingu i modeli pobieranych z sieci.
- CSS3DRenderer: zawartość okien to HTML transformowany tą samą kamerą,
  zachowujący zaznaczanie tekstu, przyciski i fokus. Karty są podsumowaniami;
  pełna treść i przewijanie znajdują się w większym modalu.
- To hybryda: nie pełny compositor 3D. HTML jest nad canvasem i nie uczestniczy
  w buforze głębokości WebGL. Dialogi używają natywnej górnej warstwy przeglądarki.
- Wygładzanie wykładnicze kamery do wybranego punktu. Kliknięcie wskazuje
  dział, kółko zmienia odległość do niego bez zmiany selekcji. Przejście do
  odległego działu nie przebiega przez wszystkie pośrednie działy.
  Usunięto sztuczną długość dokumentu zależną od liczby działów.
  W teście 1440×1100 szerokość pierwszego okna wzrosła około 3.11 razy.
- Wszystkie osie obrotu okien i kamery pozostają zerowe: brak pochylenia,
  skręcania i przekrzywionego tekstu. Różnicę wielkości daje prawdziwa odległość.
- Kule AI i Brain podążają przestrzennie za kamerą, zmieniają wielkość ekranową,
  a pojedyncza orbita SVG przesłania księżyc sylwetką kuli na tylnej półorbicie.
  Menu rozwija się od położenia klikniętej kuli/przycisku i wraca do niego
  przy zamykaniu (Web Animations API, 320/200 ms). `prefers-reduced-motion`
  pomija te animacje. Przy ukrytej kuli dostępne są stałe skróty nagłówka.
- Renderowanie na żądanie; brak nieskończonej pętli w spoczynku. Ograniczenie
  gęstości pikseli do 1.5, bez cieni renderowanych wieloma dodatkowymi przebiegami.
- Brak WebGL lub utrata kontekstu: CSS3D + linie SVG i kule CSS. Wymuszenie:
  `/os/spatial?graphics=lite`. Błąd importu nie pozostawia nieskończonego loadera.
- Wspólny jasny/ciemny motyw i palety neutralna/zielona/niebieska:
  [ustawienia wyglądu i nawigacji](APPEARANCE.md). Ograniczony ruch systemowy
  wyłącza wygładzanie oraz krążenie księżyców pojawiających się przy kulach.

Biblioteka jest serwowana lokalnie, bez CDN i telemetrii. Reprodukcja:

```bash
cd frontend/spatial
npm ci --ignore-scripts --no-audit --no-fund
npm run build
```

Build kopiuje moduły dostawcy i licencję MIT do `app/static/spatial/vendor`.
Nie edytujemy ręcznie plików Three.js. Moduły r186 nie mają wariantów `.min.js`;
w tym prototypie są nieminizowane (łącznie około 2 MB). Bundling/tree shaking
i pomiar kosztu startu pozostają przed ewentualnym zastąpieniem głównego pulpitu.

## Obsługa

- Mapa (00): kółko przewija dokument normalnie. Kliknięcie treści karty lub
  jej numeru wybiera dział i przybliża kamerę. Następnie kółko **nad sceną**
  zmienia zoom 65–125% tego zbliżenia. Poza sceną dokument przewija się normalnie.
  Przyciski +/− są alternatywą na telefonie i dla klawiatury.
- Małe karty nie mają scrolla. Opis i podpunkty otwierają się przyciskiem
  „Otwórz szczegóły działu” w większym panelu; tam przewijanie jest lokalne.
  Zoom nie zmienia `window.scrollY`; strona nie przechwytuje globalnie kółka.
- Ctrl/Command + kółko pozostaje funkcją przeglądarki, nie kamerą.
- Nawigacja 00–12 (generowana z danych), strzałki/PageUp/PageDown/Home przy fokusie sceny, poziomy gest
  nad tłem na dotyku. Przyciski pozostają alternatywą dla kółka.
- Escape/Home wraca do mapy (jeśli otwarty modal, Escape najpierw zamyka modal).
  +/− zmienia zoom przy fokusie sceny. Wspólny przełącznik Pulpit / Spatial
  pozostaje w przyklejonym pasku u góry obu widoków, także na telefonie.
- Okna można przesuwać za nagłówek w ograniczonym zakresie; linie podążają za nimi.
- Dzwonek: odczyt powiadomień działu i jego poddrzewa. Minus: zwinięcie.
  Maksymalizacja: czytelny modal szczegółów. Krzyżyk: ukrycie, nie usunięcie danych.
- Nawigacja działu przywraca jego ukryte okno. „Przywróć scenę” resetuje wszystkie.
- Kula AI otwiera Centrum Właściciela. Brain pokazuje rekomendację i wyjaśnia
  znaczenie połączeń. Dostępny stale przycisk właściciela w nagłówku.
- Odbiór, publikacje i inne rozbudowane operacje nadal w `/os` — wyraźne linki.
- Katalog pod sceną pokazuje wszystkie działy, postęp, status, wagę i przypisaną
  rolę. Wyszukiwanie po nazwie/roli, przybliżenie wybranego działu i nawigacja
  po zagnieżdżonych podpunktach przez modal z powrotem do rodzica.
- W zbliżeniu pokazywane są połączenia wybranego działu oraz właściciel–Brain,
  aby pozostałe relacje nie zasłaniały pracy. Całość w widoku 00.

## Dane i granice

Tylko GET: `/api/organization-os/tree`, `/overview`, `/next-move`, `/alerts`.
Odświeżanie co 30 s na widocznej karcie, timeout 10 s, brak nakładających się
cykli. Zachowanie tożsamości okien przy odświeżaniu. Awaria źródła zachowuje
ostatnie dane i wyświetla ostrzeżenie. Brak powiadomień nie zastępuje błędu API.
Lista powiadomień jest ograniczona do 100 otwartych wpisów przez obecny endpoint.

Wagi, postęp i przypisania pochodzą z API. Nie dodajemy fikcyjnych wykresów,
wyników finansowych, procentów ani sesji agentów. Nadzór Brain nad działem
jest rysowany wyłącznie przy zgodnych `brain_agent_id`; zależności między
działami pochodzą z danych i są deduplikowane. Układ okien jest lokalny dla
otwartej strony i nie zmienia preferencji w bazie. Przypisanie roli nie
oznacza, że agent właśnie pracuje.

## Kontrole

```bash
node tests/test_spatial_motion.mjs
.venv/bin/pytest -q tests/test_spatial_page.py tests/test_organization_os_api.py
.venv/bin/python scripts/check_spatial_browser.py --output /tmp/ai-spatial-check
```

Chrome działa w osobnym profilu z wyłączonym GPU i oprogramowaniem SwiftShader
(tylko dla tego testowego procesu). Test nie zmienia ustawień systemowej
przeglądarki. Odczytuje istniejący serwer, nie uruchamia modeli, kontenerów,
wykonawców ani nie zapisuje danych aplikacji. Zamyka tylko własny proces.
Sprawdza także 12 okien, brak sztucznie długiej strony, zmianę skali ponad 2.5×, zerowe
obroty macierzy HTML, ruch kul, animację otwarcia/zamknięcia, poddrzewo,
wyszukiwanie i wyjście poza scenę; tryb lekki, utratę WebGL, przeciąganie,
motywy, urządzenie 390px, brak scrolla kart, powrót w panelu, księżyce przy
kulach, API failure i tożsamość DOM. To test zachowania,
nie benchmark FPS ani gwarancja płynności na każdym urządzeniu.
