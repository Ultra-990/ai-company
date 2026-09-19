# Próba realizacji strony usługowej — 19.09.2026

Cel: sprawdzić drogę od opisu zlecenia do działającej strony i paczki źródeł,
korzystając z lokalnego Qwena i istniejących mechanizmów wykonania. **To własny,
syntetyczny brief**, nie ogłoszenie pobrane z Upwork ani praca dla klienta.
Właściciel nadal sam przyjmuje zlecenia i kontaktuje się z klientami.

## Zakres i rezultat

Fikcyjne studio FORMA: strona usługowa, kalkulator orientacyjnej ceny, menu
mobilne, FAQ, jasny/ciemny motyw. Bez przyjmowania zamówień, wysyłania wiadomości,
płatności, logowania i publikacji. Implementacja: istniejący profil
`python-web-multifile-v1`, Python stdlib i lokalny HTML/CSS/JS.

Qwen wygenerował dziewięć plików. Logika cen i testy modelu pozostały
niezmienione podczas poprawek. Testy odbioru ustalono przed generowaniem;
model dostał wymagania, nie ich kod ani możliwość osłabienia asercji.

| Etap | Faktyczny wynik |
| --- | --- |
| Pierwsza generacja | Logika zaliczona, brak `/health`; runner odrzucił aplikację |
| Poprawka 1 | Testy logiki i osiem prób HTTP zaliczone; w przeglądarce niewłaściwy format kwoty |
| Poprawka 2, tylko `app.js` | Poprawione kwoty i walidacja pustego pola; testy logiki/HTTP ponownie zaliczone |
| Przeglądarka | Kalkulator, menu, Escape/fokus, FAQ, nawigacja do wyceny, motywy, układ 1440/390px i reduced motion zaliczone |
| Paczka | ZIP kandydata przez istniejące API; każda treść źródła porównana z testowaną wersją |
| Odbiór/wydanie | Nie wykonano; bramka wydania nadal zamknięta bez odbioru |

Powstał też rzeczywisty fix platformy: ramka podglądu zachowuje dozwolone
atrybuty korzenia i body (`lang`, `dir`, `class`, `id`, `data-theme`) przed
wykonaniem skryptów. Wcześniej gubiła m.in. początkowy motyw strony.
Nie kopiuje root event handlers/style ani polityk bezpieczeństwa z paczki.
Nie zmieniono CSP, izolowanego origin, dostępu do tokenów lub sieci.

## Co dokładnie sprawdzono w przeglądarce

- Trzy wyceny rzeczywistym API: 2125, 9437.5 i 2800 PLN; pusty parametr
  zatrzymany w formularzu bez wywołania API.
- Jedno h1, main/footer, etykiety formularza, aria-live, obecność skip-link.
- Brak poziomego scrolla dokumentu przy 1440 i 390px; nie jest to dowód,
  że żaden element nie został obcięty, dlatego obejrzano również screenshoty.
- Motyw zmienia faktyczne tło i wraca do stanu początkowego.
- Menu mobilne otwiera się; Escape zamyka je i przywraca fokus.
- Link prowadzi do wyceny, natywne FAQ otwiera się i zamyka.
- Emulowane reduced motion nie pozostawia długich animacji CSS.
- Brak dostępu do DOM rodzica w nieprzezroczystej ramce.

Kliknięcia kontrolek wykonywane przez DOM/CDP; Escape to rzeczywiste zdarzenie
klawiatury. To nie pełny audyt klawiatury, czytników ekranu, kontrastu, wydajności,
urządzeń iOS ani penetracyjny test bezpieczeństwa. Chrome miał wyłączone GPU.

Główny agent obejrzał desktop jasny/ciemny oraz menu/wycenę mobilną tych samych
źródeł. Werdykt: czytelny prototyp funkcjonalny, **nie odbiór jakości premium**.
Do poprawy: własny kierunek artystyczny, bardziej dopracowany skład i grafika,
zbędny przycisk menu na desktopie, dominująca instrukcja uruchomienia,
redakcja polskich treści. Nie uznajemy zaliczenia pytest za poziom Awwwards.
Pole `visual_review: pending` w automatycznym raporcie pozostaje niezmienione;
niniejszy przegląd nie jest akceptacją klienta ani właściciela.

## Narzędzia i granice automatyzacji

```bash
# Bez wykonania modelu — pokazuje brief i checksumę niezależnych testów:
.venv/bin/python scripts/check_qwen_multifile.py --scenario studio

# Po sprawdzeniu zasobów — jedna generacja i izolowane testy:
.venv/bin/python scripts/check_qwen_multifile.py --scenario studio --run

# Ograniczona poprawka konkretnego raportu; bez --run tylko kontrola wejścia:
.venv/bin/python scripts/repair_upwork_web_pilot.py /sciezka/do/report.json --editable app.js --feedback "Konkretny zaobserwowany błąd"
```

Poprawka wymaga istniejącego raportu tego briefu pod Linux workspace, zgodnych
hashy, tego samego modelu i braku odbioru/publikacji. Maksymalnie dwie poprawki
w łańcuchu. Nigdy nie zmienia testów, modułu cen, README ani dodaje ścieżek.
Pełne źródła nowej wersji są składane z oryginału i odpowiedzi modelu;
`generation.kind=assembled-revision` odróżnia je od surowej generacji.
Każda poprawka ponawia te same testy. Wszystkie wersje pozostają zachowane.

Feedback w tym pilocie przygotował główny agent z raportów i przeglądu kodu.
Nie jest to jeszcze automatyczna naprawa dowolnego frontendu w panelu klienta.
Nie zmieniono produkcyjnego routingu ani statusów realnych projektów. Nie ma
automatycznej wysyłki na Upwork, zmiany zakresu klienta czy dopuszczania wydania.
Nie rozpoczęto treningu; ten brief i wyniki są materiałem ewaluacji, nie train.

Test opt-in `tests/test_upwork_web_pilot.py::test_retained_studio_website`
czyta `AIC_STUDIO_WEB_REPORT`. Używa własnej bazy, sztucznego tokena, prywatnego
Chrome i dotychczasowego runnera; nie uruchamia generowanego Pythona na hoście.
Zapisuje osobny raport, cztery screenshoty i nieodebrany ZIP kandydata.

## Dowody lokalne

Pod `/home/marcin/ai-company-workspaces/qwen-training/`:

- Pierwotny `multifile-generation-119fc97f/report.json`, SHA-256
  `0c53e13c5f5711863e54d12c9264c4199cae2e8aa3e96cbb04f40a7d3e72f61f`.
- Poprawka 1 `studio-revision-edghx6hg/report.json`, SHA-256
  `14131d0db8f6d0c8a88802bb958626d35f1b7aed419146e48053cf232eea8839`.
- Poprawka 2 `studio-revision-1ye3x8kl/report.json`, SHA-256
  `03d916388c9fd930bb5b5b39172474743d34144ce831a441db77cca4b7fd9670`.
- Pełny audit `studio-revision-1ye3x8kl/studio-browser-r5wtkyi2/report.json`,
  SHA-256 `ddb7822af0ad63230533d2f37511483b10fb18c5bbe71a536042c59420b6097a`.
- W tym samym katalogu `studio-candidate.zip`, SHA-256
  `7f79adee65bb4143579bac5d5de1a371b76d431817b67c29828f390fed9470ad`.

Nie dodajemy binarnych paczek, baz, konfiguracji ani surowych raportów do
publicznego GitHub. Zachowano nieudany audit pierwszej poprawki oraz pierwszy
zaliczony audit drugiej poprawki (przed dodaniem kontroli ZIP).

## Osobny projektant CSS i podgląd właściciela

`scripts/design_upwork_web_pilot.py REPORT BROWSER_REPORT --run` wykonuje
jedną próbę zmiany wyłącznie `style.css`. Wymaga zgodnych hashy, zamrożonego
briefu oraz zaliczonych testów backendu i przeglądarki wersji wejściowej.
Nie zeruje limitu poprawek, nie zmienia HTML/JS/testów, nie uruchamia treningu.
Bez `--run` jedynie sprawdza wejście. Odpowiedź projektanta, jego uwagi oraz
złożone źródła są zapisywane oddzielnie. CSS nadal jest niezaufany: proste
odrzucenie importów/url nie zastępuje CSP i izolacji przeglądarki.

Próba z 19.09: `studio-design-o1sem2gt/report.json`, SHA-256
`337fd0bdf4ed2af6b16c1d03e48928b6b2615dcfdd8657aaee528eab43f73c14`.
Całość 17.703s; zmieniono tylko CSS. Backend i osiem HTTP ponownie zaliczone.
Pierwszy audit `studio-browser-5968_3cj` zaliczył kontrole funkcjonalne
i porównanie ZIP (1 passed/4.42s). Obejrzano cztery rzeczywiste screenshoty.
Wygląd pozostaje prosty i szablonowy, nie jest zaakceptowany jako premium.
Model nie wykonał m.in. jawnego wymagania ukrycia menu na desktopie.
Dodano kontrolę tego wymagania wyłącznie dla etapu `css-design`.
Powtórny audit `studio-browser-nyidp_ip` odrzucił tę samą wersję:
`design-desktop-menu-hidden` (1 failed/3.83s). Oba raporty zachowano;
starsze zaliczenie funkcji nie zastępuje późniejszej kontroli wyglądu.
Nie ukryto porażki dodatkową generacją ani zmianą progu testu.

Właściciel może obejrzeć także odrzucony wizualnie, ale działający prototyp:

```bash
.venv/bin/python scripts/serve_studio_preview.py /home/marcin/ai-company-workspaces/qwen-training/studio-design-o1sem2gt/report.json --minutes 120
```

Skrypt wypisuje losowy lokalny adres `http://127.0.0.1:PORT`. Należy otworzyć
go na tym samym komputerze; bez logowania i bez tokena właściciela.
Nie otwierać `index.html` bezpośrednio ani uruchamiać wygenerowanego `app.py`
na hoście pomimo ogólnej instrukcji w samej demonstracyjnej stronie.
To fikcyjna witryna FORMA, **nie nowy pulpit firmy i nie praca klienta**.

Podgląd trwa maksymalnie 120 minut, dopuszcza do 60 obliczeń, działa wyłącznie
na loopback. Używa istniejącej ramki o nieprzezroczystym origin i CSP,
sprawdza Host/Origin/osobny CSRF, nie udostępnia API właściciela ani plików.
Dozwolone jest tylko ograniczone `/api/estimate`; każde obliczenie przechodzi
przez dotychczasowy izolowany runner z kontrolą zasobów i sprzątania.
Brak produkcyjnej bazy, akceptacji, publikacji, zmian usług i wag modeli.
To narzędzie lokalnego przeglądu, nie serwer do wystawienia w Internecie.

Testy `tests/test_studio_preview.py` obejmują ograniczenia źródeł i żądań.
Opcjonalny `AIC_STUDIO_PREVIEW_URL` włącza test rzeczywistego lokalnego
podglądu: izolacja ramki, odmowa obcego Host/Origin i braku CSRF,
brak API zadań, rzeczywisty wynik 2125. Wynik: 16 passed/0.79s.
