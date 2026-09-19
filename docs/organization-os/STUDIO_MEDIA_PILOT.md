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
