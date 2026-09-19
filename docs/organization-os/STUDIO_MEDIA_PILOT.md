# FORMA: Qwen → ComfyUI → interaktywna strona

## Co działa (19.09.2026)

Rzeczywisty lokalny pilot, nie makieta: Qwen przygotował trzy opisy grafik,
istniejący Z-Image Turbo w ComfyUI wygenerował PNG, a nadzorowana warstwa
galerii osadziła je w stronie FORMA. Właściciel może otworzyć lokalny podgląd,
zmienić motyw, oglądać obrazy i korzystać z dotychczasowego kalkulatora.

Podział odpowiedzialności jest jawny:

- Qwen: opisy scen, tytuły, początkowe opisy alternatywne; wynik ograniczony
  schematem JSON, bez kodu, grafów nodes, poleceń lub pobierania.
- ComfyUI: istniejący natywny graph `comfyui_provider.graph`, 768×512,
  8 kroków, CFG 1, trzy stałe seedy 20260919–20260921; bez nowych nodes/API.
- Główny agent: przegląd promptów i trzech obrazów, kod integracji/galerii,
  kontrola testów. Nie przypisujemy napisania galerii modelowi Qwen.

Wagi odczytano z wcześniej istniejącego katalogu Windows, wyłącznie `ro`:
`z_image_turbo_bf16.safetensors`, `qwen_3_4b.safetensors`, `ae.safetensors`.
Nie pobrano modeli ani nie rozpoczęto treningu. Własny proces ComfyUI na
8189 miał osobny katalog danych/wyjścia na Linuksie i został zakończony
po generacji. Nie uruchamiano ani nie zatrzymywano cudzej instancji 8188.

## Interakcje

### Studio funkcji, sprężyste tory i skalowanie (20.09.2026)

Nagłówek **Studio ＋** otwiera rozwijane menu z grupami funkcji. Jest również
stałe drzewo na stronie w sekcji Studio: przestrzeń/ruch, projekt/moduły,
materiały/dostępność. Wszystkie pozycje prowadzą do istniejących narzędzi.
Menu ma modalny fokus, Escape, zamknięcie po kliknięciu w zewnętrzne tło,
przywracanie fokusu i nawigację do wybranego narzędzia. Wąski ekran dostaje
menu dopasowane do viewportu z wewnętrznym przewijaniem dłuższej treści.

Sterowanie sceną oferuje cztery tory: **helisa, orbita, fala, galeria**.
Helisa/orbita/fala zmieniają X/Y/Z i orientację płaszczyzn obrazów; obraz na
pierwszym planie przy pełnym wyborze jest zwrócony prosto do użytkownika.
Pojawia się rzut przestrzennej krzywej na tło. Ruch kursora delikatnie zmienia
punkt obserwacji; nie przesuwa systemowego kursora. To nadal płaszczyzny
zdjęć w CSS 3D, a nie rekonstrukcja przedmiotów ani generowanie wideo.

Regulacja sprężystości 0–100%, głębi 40–140%, pauza i reset są rzeczywiste.
Sprężyny z tłumieniem integrują ruch w małych podkrokach. Po ustaniu wejścia
zatrzymują się; limit 1.8s kończy dojście również przy niskim FPS. Ukrycie
karty wstrzymuje pętlę. Pauza nie blokuje przewijania dokumentu. Animacja
nie przechwytuje kółka na stronie. Kółko w otwartym widoku zdjęcia przybliża
i oddala (100–240%); Ctrl+kółko i systemowy pinch pozostają dla przeglądarki.
Kliknięcie pustego tła sceny cofa poprzedni wybór studium (historia do 16);
równoważny przycisk „Wróć” działa klawiaturą. Przy braku historii wraca do
poprzedniego studium. Puste tło podglądu zdjęcia zamyka podgląd. Kliknięcia
narzędzi nie są globalnym poleceniem cofania.

**Kreator briefu:** pięć typów projektu, cel do 600 znaków, osiem opcjonalnych
modułów, jawne kryteria odbioru i etapy. Działa według lokalnych reguł,
nie wywołuje modelu. Przycisk zaznacza wynik do ręcznego skopiowania — nie
twierdzi, że zapisał schowek. Brak przechowywania po refresh i wysyłania danych.
Wybór AI, mediów, kont czy płatności jest zakresem planu, nie wdrożeniem tych
usług ani przyjęciem zamówienia. Kalkulator pozostał pobocznym testem backendu.

Układ i narzędzia dopasowują się do ekranu. Przy <=800px lub wysokości <620px
oraz reduced motion scena przechodzi w układ redakcyjny; drzewo, konfiguracja,
brief, menu i powiększanie zdjęć nadal są dostępne. Testowane viewporty:
320×568, 390×844, 768×1024, 1024×768, 1440×900 i 2560×1440, również otwarte
menu oraz tekst 200%. CDP sprawdza rzeczywiste zdarzenia dotyku, kółka i Escape.
To emulacja Chrome, nie certyfikacja Safari/iPhone ani pomiar wydajności GPU.

Końcowy audit: `studio-design-o1sem2gt/studio-browser-y443q1s6/report.json`,
SHA-256 `e68618bd3ba2efc978e1cbc9f3e783c15994beaa33874453b8960cc7f8401192`,
**1 passed/21.95s**. Obejmuje tło/powrót, otwarte menu na sześciu viewportach,
dotyk, Escape/fokus, brief, wszystkie tory, pauzę, suwaki, zoom i dozwolone
`pinch-zoom`. Obejrzano końcowy zrzut rozwiniętego menu przy 320px.
Właściciel pozytywnie ocenił działanie; nie zmienia to stanu wydania backendu.

### Scena sterowana przewijaniem (20.09.2026)

Po uwadze właściciela, że samo animowanie dialogu nie daje oczekiwanego
efektu, główną interakcją jest teraz **przewijanie sceny na stronie**.
Link „Wejdź w scenę” z hero prowadzi do sekcji. Na ekranach powyżej 800px
szerokości i od 620px wysokości jest ona sticky, z trzema prostymi płaszczyznami
zdjęć w perspektywie CSS. Naturalny scroll zmienia przesunięcie i głębokość:
następny obraz rośnie i wysuwa się na pierwszy plan, poprzedni się oddala.
Bez pochylania tekstu, przejmowania kółka, WebGL i pętli renderującej w spoczynku.

420svh to długość sekcji, nie dodatkowa pusta strona: w trakcie jej przewijania
scena pozostaje w kadrze. Przyciski 01–03 pozwalają ominąć przewijanie do
wybranego studium, „Pomiń scenę” przechodzi do usług. Fokus klawiatury na zdjęciu
ustawia je na pierwszym planie. Kółko działa w obie strony. Modal z zoomem
pozostaje opcjonalnym widokiem detali, nie głównym sposobem oglądania.

Telefon, niski ekran i reduced motion dostają zwykły układ redakcyjny bez
długiej sticky sekcji. Brak JS również zostawia widoczne obrazy i podpisy.
Scena jest progresywną nakładką `studio-scene.css/js`; bazowa aplikacja i jej
obliczenia pozostają nietknięte. To perspektywa płaskich PNG, nie modele 3D
ani animacja wnętrza fotografii. Rozdzielczość mediów nadal 768×512.

Końcowy rzeczywisty audit Chrome: `studio-design-o1sem2gt/studio-browser-hnfxdrs9/report.json`,
SHA-256 `3366cba6ab73d0badd01e5774f4f29ce332b2aa4106511253b126263208a2f21`,
**1 passed/9.93s**. Faktyczne zdarzenia kółka potwierdzają zmianę rozmiaru
obrazu, odwrócenie ruchu, nawigację rozdziałów i pominięcie sceny. Sprawdzono
też wcześniejsze interakcje, kalkulator, układy mobilne i reduced motion.
Przejrzano zrzuty początku, przejścia i wybranego studium. Regresja:
74 passed/1 skipped; Node sprawdza geometrię. Nie jest to pomiar FPS ani
deklaracja jakości konkursowej. Nowy podgląd trzeba uruchomić ponownie
poniższym poleceniem, ponieważ serwer przechowuje zasoby z chwili startu.

- Grafika w hero i trzy spójne studia: chrom, architektura, materiały.
- Subtelne skalowanie kart podczas zwykłego przewijania, bez blokady scrolla.
- Kliknięcie otwiera natywny dialog; kółko **nad obrazem w otwartym dialogu**
  przybliża/oddala w zakresie 100–240%. Ctrl+kółko pozostaje dla przeglądarki.
- Przyciski +/−/Reset działają również bez myszy. Strzałki/przyciski zmieniają
  obraz, Escape/zamknięcie przywraca fokus do otwierającego elementu.
- Jasny/ciemny motyw, mobilny układ i reduced motion. Brak zewnętrznych
  bibliotek, fontów, trackerów i sieci w ramce z wygenerowanym kodem.

### Animowane przejścia (20.09.2026)

Kliknięty obraz powiększa się z pozycji karty do widoku obejmującego ekran
(720 ms), a zamknięcie odwraca przejście (520 ms). Natywny dialog pozostaje
dla izolacji fokusu, lecz nie ma ramki zwykłego okna. Tło oraz sterowanie
pojawiają się stopniowo. Zmiana obrazu to animacja przesunięcia i skali,
nie natychmiastowa podmiana; zmiana resetuje zoom. Zamknięcie po przełączeniu
wraca do karty aktualnego obrazu, a fokus do pierwotnego przycisku.

Implementacja używa Web Animations API, jednolitej skali i animowanego kadru,
bez rozciągania proporcji zdjęcia. Dla karty poza ekranem używa zanikania,
bez wymuszonego przewijania strony. Kółko poza otwartą galerią nadal normalnie
przewija stronę. Przy `prefers-reduced-motion` animacje są pomijane. Nie dodano
ciężkiego silnika 3D ani nowych zależności. Resize kończy bieżącą animację;
zamknięcie podczas otwierania jest kolejkowane, a tymczasowy obraz usuwany.

Test rzeczywistej przeglądarki: `studio-design-o1sem2gt/studio-browser-qffj4d4d/report.json`
(w tym samym lokalnym katalogu dowodów co poniżej), SHA-256
`7970b8e36014679248a1ccb8ec58306c8d6ca03a1eefbe017d1eb1642c7c0c40`:
**1 passed, 7.93s**. Sprawdza działające animacje otwarcia/przełączania/powrotu,
zoom kółkiem, Escape/fokus, mobile 390px, reduced motion, szybkie zamknięcie,
motywy i kalkulator. Obejrzano zrzuty fazy przejściowej i telefonu.
Regresja: **74 passed, 1 skipped**, dodatkowo testy geometrii Node i składnia JS.
Nie jest to test FPS ani próba na fizycznym iPhonie.

Po zmianie nakładki trzeba uruchomić nowy podgląd poleceniem poniżej:
serwer zachowuje wersję zasobów z chwili startu. Sam refresh starego serwera
nie wczytuje nowego kodu. Media nie wymagają ponownego generowania.

To zoom wyświetlania PNG, nie generowanie nowych szczegółów ani super-resolution.
768×512 jest rozdzielczością prototypu, nie docelową grafiką dla ekranów 4K.

## Uruchamianie i dowody

```bash
# Sam opis operacji, bez uruchamiania modelu:
.venv/bin/python scripts/build_studio_media.py --plan
# Jedna odpowiedź Qwen; sprawdzić zapisane prompty przed renderem:
.venv/bin/python scripts/build_studio_media.py --plan --run
# Jawny etap renderowania zaakceptowanego do próby lokalnego planu:
.venv/bin/python scripts/build_studio_media.py --render /sciezka/do/planu/report.json --run
```

Każde uruchomienie ma nowy katalog `studio-media-*`, bez nadpisywania wag
i wcześniejszych wyników. Skrypt wymaga zgodnego read-only mount, przypiętego
ComfyUI i dostępnych zasobów. Brak modeli kończy etap komunikatem, nie downloadem.
W aktualnym skrypcie kontrola obcej kolejki/kontenerów/Ollama również podczas
renderu co 5s; konflikt kończy wyłącznie własny proces, nie cudze usługi.

Dowody pod `/home/marcin/ai-company-workspaces/qwen-training/`:

- Plan Qwen `studio-media-9qu0ny99/report.json`:
  `7dd938365a9c0d4fbc75b5449e90ae8d3c9f1b43bad047ff58576c457815d21c`.
- Generacja `studio-media-8ab7jpvs/report.json`:
  `11d3dbedfb14acc0325a326b67839252046649a4d0301647ba766c1f6f7b8520`.
  Obrazy w jego `output/`: `sculpture_00001_.png`, `architecture_00001_.png`,
  `material_00001_.png`. Czasy: 53.268s, 48.651s, 48.747s, z ładowaniem wag.
- Browser `studio-design-o1sem2gt/studio-browser-4njgfhkm/report.json`:
  `331eaa0b34da1576f3e529a4793feba2456dc153e515c94de27be7fa3866aa20`.
  Wynik 1 passed/5.42s. Raport wiąże źródła, media oraz CSS/JS nakładki hashami.

Otworzenie aktualnej wersji (wypisze losowy lokalny adres, działa do 120 minut):

```bash
.venv/bin/python scripts/serve_studio_preview.py \
  /home/marcin/ai-company-workspaces/qwen-training/studio-design-o1sem2gt/report.json \
  --media-report /home/marcin/ai-company-workspaces/qwen-training/studio-media-8ab7jpvs/report.json \
  --minutes 120
```

Nie uruchamiać wygenerowanego `app.py` na hoście. Kalkulator korzysta z
dotychczasowego izolowanego runnera. Podgląd nie używa produkcyjnej bazy,
tokena właściciela ani prawdziwych danych klientów.

## Kontrola i ograniczenia

Loader wymaga trzech PNG z lokalnego katalogu raportu, zgodnych hashy,
rozmiarów, nagłówków i weryfikacji PNG. Tytuły/alt są escapowane, obrazy trafiają
do istniejącej opaque ramki jako data URI; CSP nie została rozluźniona.
Zamrożone źródła aplikacji i backend pozostają bez zmian. **Galeria/media są
na razie osobną nakładką podglądu**, a dotychczasowy ZIP kandydata zawiera
aplikację bazową bez nich. Raport jawnie zapisuje `includes_media_overlay=false`.
Następny etap przed dostawą klientowi: wersjonowany pakiet aplikacja+media,
testy jego odtwarzania i praw/licencji, integracja z produkcyjnym procesem zadań.

Nie jest to autonomiczny pełny workflow zlecenia ani dowód jakości Awwwards.
Nie publikowano strony, nie odebrano zlecenia, nie wysyłano nic na Upwork.
Prompty i obrazy to własne materiały demonstracyjne, nie prace klienta.

Zachowano niezaliczone audity: pierwszy test kółka wysyłał zdarzenie bez
ustawienia kursora, kolejny odczytywał fokus przed zdarzeniem close, trzeci
zakładał stałe 300ms na smooth scroll dłuższej strony. Poprawiono sterowanie
testu i ograniczone oczekiwanie na faktyczny stan, nie kryteria funkcjonalne.
Ostateczny audit sprawdza rzeczywiste zdarzenie kółka CDP oraz Escape,
załadowanie PNG, zoom/przełączanie, kalkulator, mobile, FAQ i motywy.
Regresja: 95 passed/1 skipped; osobno 9 testów walidacji mediów/ochrony
zasobów. Nie jest to pełny audyt dostępności, wydajności iOS ani bezpieczeństwa.
