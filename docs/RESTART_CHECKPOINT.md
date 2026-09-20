# Punkt wznowienia — 20.09.2026

## Wznowiono po restarcie

Właściciel potwierdził poprawną pracę myszy i okien oraz zezwolił na dalszą
budowę. Przyczyna problemu nieustalona. Nie trzeba ponownie pytać o tę zgodę.
Zbudowano kompletny ZIP i osobny podgląd LAN dla telefonu — aktualne polecenia,
artefakty, wyniki i pozostałe prace są w
[STUDIO_BUNDLE.md](organization-os/STUDIO_BUNDLE.md).
Naprawę pierwszego przewijania zapisano w `0bac9b4`. Następnie ukończono
[obieg źródeł i PNG przez zadanie, testy, odbiór i ZIP](organization-os/MEDIA_PACKAGES.md).
Poniższa lista jest zapisem stanu sprzed wznowienia.

Właściciel poprosił o przygotowanie, a następnie restart komputera z powodu
problemów myszy/przełączania okien Linuksa. Nie deklarujemy rozpoznania przyczyny
ani naprawy KWin. Zmiany ochronne interfejsu są w commicie `2eab5bd` na gałęzi
`chore/roadmap-bootstrap-20260909T122313Z`, zapisane również na origin.

## Przed restartem

- Bez zmian ustawień pulpitu, sterownika, usług Vast.ai, partycji czy Windows.
- Własne podglądy FORMA (PID 901496, 910694, 918250, 942791, 953644)
  zakończono SIGINT. Poprzednie adresy loopback nie będą już działać.
- Ostatnia kontrola: `docker ps` pusty, brak procesów pytest/Qwen runner
  i prywatnego Chrome testowego w sprawdzanej liście.
- Lokalny raport konsultacji Qwen zachowano poza /tmp:
  `/home/marcin/ai-company-workspaces/restart-20260920-OaBWT3/qwen-interaction-review.json`.
- Nie restartowano ani nie zamykano aplikacji użytkownika podczas przygotowania.
  Polecenie restartu wykonywane osobno, po zapisaniu tej notatki i push.

## Co sprawdzić po uruchomieniu

1. Przeczytaj AGENTS.md i ten plik; sprawdź git status. Nie nadpisuj zmian.
2. Najpierw sprawdź z właścicielem mysz i Alt+Tab bez otwierania FORMA.
   Jeżeli problem występuje bez strony, diagnoza Linuksa pozostaje otwarta.
   W logach wcześniej były KWin XCB BadDamage; niskie obciążenie nie wyklucza
   problemu grafiki/urządzeń wejścia. Nie stosuj resetu sterowników w ciemno.
3. Przed modelami/kontenerami sprawdź stan Vast.ai/zasobów. Nie zakładaj,
   że brak najmu przed restartem obowiązuje po ponownym starcie usług.
4. Uruchom tylko jedną aktualną demonstrację, jeśli pulpit działa stabilnie.
   Właściciel wkleja surowy URL do przeglądarki; linki Markdown w Codexie
   nie otwierały mu strony. Nie otwieraj ani nie steruj oknami OS automatycznie.

```bash
cd /home/marcin/ai-company
.venv/bin/python scripts/serve_studio_preview.py \
  /home/marcin/ai-company-workspaces/qwen-training/studio-design-o1sem2gt/report.json \
  --media-report /home/marcin/ai-company-workspaces/qwen-training/studio-media-8ab7jpvs/report.json \
  --minutes 120
```

Serwer wypisze NOWY adres localhost. Nie używaj starych portów. Wymaga
zatwierdzonego restricted Docker; kod wygenerowanej aplikacji nie działa na hoście.

## Stan funkcji i następne prace

- Wspólna historia sceny/sekcji, tło-powrót, zoom podczas animacji i przerwanie
  smooth scroll przez kółko: wdrożone/testowane, `8b84ce6`.
- Ochrona fokusu: widoczny/aktywny dokument, unieważnianie opóźnionych operacji,
  close w tle odłożony do powrotu; skróty Alt/Ctrl/Meta nie są komendami galerii.
  Testy headless bez DISPLAY/WAYLAND_DISPLAY/XAUTHORITY i sesyjnego D-Bus.
  Audit `studio-design-o1sem2gt/studio-browser-cutmo6rd/report.json`: 1 passed,
  SHA256 `468937f368627b0bde49267383d8942aa71f0a2ef70666de8ee37d2f8cf16de1`.
  Python 74 passed/1 skipped, Node testy polityki fokusu i geometrii zaliczone.
  NIE potwierdzono usunięcia problemu w fizycznej sesji KDE użytkownika.
- Telefon iPhone: podgląd przez Wi-Fi jeszcze NIE wdrożony. Nie wystawiaj
  panelu właściciela/całego API do LAN. Wymagany odrębny ograniczony podgląd.
- Kolejny etap produktu po stabilizacji: jedna paczka aplikacja + obrazy +
  interakcje. Obecny candidate ZIP nadal zawiera bazową aplikację, nakładka
  wizualna istnieje oddzielnie. Nie twierdź, że klient otrzymuje cały prototyp.
- Backend/modelami można realizować wydzielone prace, ale żadnego sterowania
  sesją graficzną użytkownika. Bez nowych treningów podczas diagnozy pulpitu.
- Wszystkie ważne dowody/limity w docs/WORK_LOG.md i
  docs/organization-os/STUDIO_MEDIA_PILOT.md. Nie zmieniaj prawdziwych statusów
  zadań w celu testowania UI. Nie publikuj lokalnych raportów ani danych klienta.

Restart może zakończyć sesję Codexa; automatyczne wznowienie agenta nie jest
skonfigurowane. Po restarcie właściciel otwiera tę rozmowę i prosi o kontynuację.
