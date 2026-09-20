# FORMA: kompletna paczka demonstracyjna

## Stan — 20.09.2026

ZIP zawiera teraz aplikację, trzy PNG oraz wszystkie interakcje widoczne w
podglądzie: 20 plików i osobny manifest `bundle.json`. Podgląd z `--bundle`
odczytuje wyłącznie zawartość archiwum; nie dobiera nakładki z bieżącego repo.
To lokalny kandydat syntetyczny, nie zatwierdzone wydanie ani wdrożenie klienta.
Zamrożony raport bazowy i starsze ZIP-y pozostają bez zmian.

`scripts/build_studio_bundle.py` sprawdza bazowe źródła i media, składa HTML,
umieszcza interakcje i PNG pod `static/`, zachowuje logikę Qwen i zastępuje
wejściowy serwer nadzorowanym serwerem z dokładną listą publicznych tras.
Obrazy nie zależą od ComfyUI ani katalogów hosta podczas uruchamiania paczki.
Kod źródłowy, testy i README nie są publicznymi trasami HTTP.

```bash
.venv/bin/python scripts/build_studio_bundle.py \
  /home/marcin/ai-company-workspaces/qwen-training/studio-design-o1sem2gt/report.json \
  --media-report /home/marcin/ai-company-workspaces/qwen-training/studio-media-8ab7jpvs/report.json \
  --run
```

Bez `--run` powstaje tylko kandydat; nic nie wykonuje kodu aplikacji.
Każde uruchomienie tworzy nowy katalog na dysku Linux. Manifest zawiera
SHA-256 plików, pochodzenie i `accepted=false`, `deployed=false`. Raport kontroli
pozostaje osobno, związany sumą całego ZIP. Hash nie jest podpisem ani odbiorem.

## Izolacja i odtwarzanie

- ZIP jest czytany w pamięci, bez `extractall`. Wymagany dokładny zestaw nazw,
  zwykłe pliki, brak kompresji, szyfrowania, duplikatów i dowiązań. Limity:
  4 MB/PNG, 256 KiB/tekst, 14 MB zawartości. Sumy weryfikowane przed użyciem.
- Oddzielny pilot `BundleRunner` zapisuje bytes do nowego prywatnego stagingu.
  Nie rozszerza limitów pakietów produkcyjnych ani dostępnych profili API.
- Wykorzystuje istniejący przypięty Docker: nonroot, read-only, network none,
  1 CPU, 512 MiB, 64 PID, bez GPU, home hosta i docker.sock. Kontrola izolacji
  poprzedza uruchomienie. Zamyka wyłącznie własny kontener o losowej tożsamości.
- Tester uruchamia oryginalne oraz niezależne, niezmienione asercje logiki,
  porównuje bytes i MIME wszystkich publicznych tras z plikami paczki,
  sprawdza API oraz odmowę dostępu do źródeł i ścieżek traversal.
- Ramka podglądu ma opaque origin i wcześniejsze CSP. PNG z ZIP są zamieniane
  na data URI, CSS/JS pochodzą z ZIP. Wywołania kalkulatora wykonują dokładne
  źródła archiwum w kontenerze, nie bazowy backend z innego raportu.
- Test Chrome używa osobnego profilu headless, bez GPU, DISPLAY, Wayland,
  XAUTHORITY i sesyjnego D-Bus. Nie steruje pulpitem właściciela.

## Podgląd komputera i telefonu

```bash
.venv/bin/python scripts/serve_studio_preview.py \
  /home/marcin/ai-company-workspaces/qwen-training/studio-bundle-txnwfeuv/forma-candidate.zip \
  --bundle --minutes 120
```

Domyślnie tylko `127.0.0.1`. Dla telefonu dodać `--bind` z aktualnym adresem
LAN komputera, np. `--bind 10.0.0.57`. Skrypt wypisuje nowy URL z losowym portem.
Telefon musi mieć dostęp do tej samej sieci; adres może się zmienić po DHCP.
Wildcard, publiczny adres i adres overlay VPN są odrzucane. Nie zmieniamy
routera, zapory, usług systemowych ani konfiguracji panelu firmy.

To osobny serwer z trzema trasami: `/`, `/frame`, `/probe`. Sprawdza dokładny
Host, a obliczenia dodatkowo Origin i losowy token CSRF. Dopuszcza jedynie
ograniczone parametry kalkulatora, maksymalnie 60 obliczeń i 120 minut działania.
Demonstracja jest dostępna urządzeniom mogącym połączyć się z tym adresem LAN;
nie zawiera tokenów właściciela, dostępu do bazy ani prawdziwych danych klientów.

## Dowody i granice

- `studio-bundle-txnwfeuv/forma-candidate.zip`: 1 288 519 bytes, SHA-256
  `f0c898b0e36c609b85d31a75b93291a63ec08a51c5ec966b1b7fdb06a5f4ee73`.
- `studio-bundle-txnwfeuv/report.json`: pełna kontrola kontenera zaliczona;
  `browser_validation=pending` opisuje chwilę budowy. Późniejszy raport poniżej
  jest osobnym dowodem dotyczącym dokładnie tego ZIP-a.
- `studio-design-o1sem2gt/studio-browser-nrku0sg5/report.json`:
  **1 passed / 30.52 s**, **112 zaliczonych kontroli**, powiązanie z sumą ZIP.
  Galeria, ruch, zoom, historia, brief, kalkulator, menu, sześć viewportów,
  reduced motion, tekst 200%, granica fokusu i izolacja ramki.
- Działający podgląd LAN: **28 passed / 1.04 s**, w tym kalkulator 2125,
  odmowa obcego Host/Origin/CSRF, brak `/api/tasks` i brak dowolnych tras.
- Regresja pakowania, mediów, designu, napraw i profilu: **96 passed / 1 skipped**.
  Node: 3 testy fokusu i 8 testów geometrii/ruchu zaliczone.

To emulacja Chrome, nie test fizycznego iPhone/Safari. Osobny pilot nie został
jeszcze podłączony do produkcyjnego procesu odbioru i wydań. Pozostają dalszy
odbiór wizualny, przegląd praw do materiałów dla rzeczywistego zlecenia oraz
integracja paczki binarnej z zadaniami/dostawą. Nie zmieniamy ich statusów dla
demonstracji. Paczka nie zawiera odtwarzacza wideo ani integracji płatności.
