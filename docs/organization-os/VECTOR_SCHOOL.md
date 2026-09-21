# Szkoła odtwarzania ulotek

Nowszy etap: [przygotowanie wzorców egzaminacyjnych](VECTOR_STRUCTURED_REFERENCES.md).
Jeden wzorzec validation odebrany, test nadal nieodebrany; bez odpowiedzi
ucznia na egzaminie i bez aktualizacji wag. Poniższe sekcje opisują wcześniejsze etapy.

## Partia trzech rodzin — 21.09.2026

`vector_curriculum.py` ustala rodziny przed generowaniem: ogród, degustacja
i giełda płyt do treningu; wieczór naukowy do walidacji; klub podróżniczy
do testu. Historyczna ulotka pozostaje w development. Metadane i hash
wiążą rodzinę z rzeczywistym briefem. Walidacja i test są blokowane przez
ścieżkę nauki; nie wygenerowano jeszcze ich odpowiedzi ani obrazów.

W 11 lokalnych wywołaniach model przygotował trzy zaakceptowane wzorce,
trzy pierwsze odtworzenia i poprawki. Początkowe odtworzenia: **0/3 odebrane**.
Źródło restauracyjne wymagało poprawienia niewidocznego nagłówka; płytowe
miało najpierw siedem zamiast ośmiu tekstów, potem przekroczony margines.
Wszystkie poprawki treści i SVG wykonał lokalny model. Asystent przekazywał
opis błędu i pomiary, zachowując oryginalne nieudane odpowiedzi.

`--source-feedback` wiąże ocenę z raportem, żądaniem i surową odpowiedzią,
również niepoprawną strukturalnie. Limit wynosi trzy naprawy źródła;
łańcuch jest weryfikowany rekurencyjnie. Źródła train wymagają pozytywnej,
niezależnej oceny obrazu powiązanej hashem przed użyciem do odtwarzania.
`--audit-source` ponawia jedynie renderowanie i pomiary istniejącego SVG.
Detektor niemal identycznego koloru tekstu i tła wykrył 13 niewidocznych
znaków nagłówka w próbie negatywnej. To przybliżona kontrola środków znaków,
nie pełna analiza kontrastu, zgodność WCAG ani zastępstwo oceny wzrokowej.

Pierwszy patch restauracji zmienił położenie, pozostawiając błąd szerokości.
Profil `--diagnostics named-deltas-v1` nazywa wymiary błędów bez podawania
wartości naprawy. W drugiej próbie model sam zmienił rozmiar podtytułu;
osiem pól zaliczyło tolerancję, siedem chronionych pozostało bez zmian.
Niezależnie odebrano **jedną lokalną lekcję użycia narzędzia**. Typografia
nie jest identyczna ze źródłem; pozostają różnice panelu i kolorów.
Nie oznacza to odbioru reprodukcji do druku lub całej usługi.

Dokładne doświadczenie zapisano prywatnie jako train, bez eksportu do SFT
i bez uruchomienia treningu wag. Obecny audyt trenera obraz–tekst obsługuje
zbiór wnętrz, nie ten zapis wektorowy. Łączny czas 11 etapów modelu/renderu
wyniósł 78,173 s; nie obejmuje pracy nad infrastrukturą ani oceny nauczyciela.
106 testów infrastruktury zaliczonych. Prywatna ocena partii:
`vector-school/cohort-001-assessment.json`, SHA-256
`fb9bad403844cadcef029c645337cee77d4be33da8df9ea505c6decd5e7a21ac`.

## Poprzednia partia rozwojowa

Stan 21.09.2026: cztery próby pełnego odtworzenia SVG nie przeszły sprawdzianu.
Następnie **jedna modelowa poprawka atrybutów zaliczyła lekcję bez regresji**:
model wskazał dwie zmiany, a system zastosował je dosłownie. Nadal nie jest
to potwierdzenie gotowości całej usługi, wiernej reprodukcji do druku ani
poprawy wag modelu. Szczegóły obu etapów poniżej.

## Precyzyjna poprawka po pełnych odtworzeniach

`scripts/vector_patch_school.py` uczy model korzystania z narzędzia zmiany
atrybutów istniejącego SVG. Wymaga poprawnego tekstu, jego widoczności
i zaliczonego globalnego porównania obrazu. Z pozostałych błędów geometrii
wyznacza elementy do naprawy; nie oblicza nowych wartości za model.
Model dostaje obraz wzorca, katalog własnych istniejących elementów
i pomiary błędów. Odpowiada operacjami `element/attribute/before/after`.

System sprawdza indeksy, stare wartości, dozwolone elementy i bezpieczeństwo
nowych wartości. Stosuje dosłowne operacje modelu, zachowując pozostałe
bajty źródła, zamiast przepisywać XML. Nie dodaje operacji ani nie zgaduje
wartości. Niedozwolony, nieaktualny lub pusty patch jest odrzucany.
Ta lekcja dotyczy istniejących atrybutów; nie dodaje figur, tekstu lub warstw.
Pełne tworzenie źródła pozostaje zadaniem modelu w poprzednim etapie.

Rzeczywista próba `patch-8ykjbubf` bazowała na wcześniejszej wersji
`recreate-456pyqiw`, wybranej z prób rozwojowych, bo miała najniższy błąd
obrazu i czytelne teksty. Niezależny pomiar wyznaczył dwa błędne elementy.
Qwen sam wskazał zmianę rozmiaru daty20→22 i stopki25→23. Nie otrzymał
kodowego rozwiązania od asystenta. Odpowiedź61tokenów, wejście2299tokenów,
inferencja4,011s, cały etap4,528s; niezmieniony model i digest.

Wynik:8/8tekstów dokładnych,8/8pól w tolerancji,6chronionych pól bez zmiany,
brak zasłoniętych znaków. Błąd RGB0,035415, zmienione piksele0,047257.
SVG różni się od poprzednika **tylko dwoma pozycjami bajtów**. Eksport
PDF ponownie sprawdzono przez odczyt rzeczywistego pliku. `--verify`
odtwarza operacje z oryginalnej odpowiedzi modelu, sprawdza łańcuch plików,
wejścia, wyniki pomiarów i PDF bez kolejnej inferencji.

Nauczyciel obejrzał wynik i odebrał **lokalną naprawę atrybutów**, z jawnym
ograniczeniem: nadal istnieją niewielkie różnice pierścienia, kolorów
i nietargetowanej typografii względem wzorca. Tolerancja ćwiczenia nie
oznacza idealnej reprodukcji ani zgodności z wymaganiami drukarni.
Nie porównywano tu bazy z nowymi wagami ani niezależnych rodzin zadań.

`teacher-review.json` wiąże ocenę z hashem raportu. Po zaliczeniu audytu
i niezależnej oceny `--record-experience` zapisuje dokładną rozmowę,
modelowy patch, konfigurację oraz odnośnik/hash rzeczywistego obrazu.
Format `company-vision-experience.v1`, podzbiór `development`, **nie eksport
SFT lub zbiór gotowy dla trenera**. Nie nadpisuje wcześniejszego doświadczenia
i nie akceptuje samooceny modelu. Prywatny `experience.json` ma SHA-256
`e6c4040d5fe836119a00002f5633d760ea6e3e95482fa6085e6505a18a7243fa`.
Następna partia wymaga większej różnorodności i jawnego przydziału rodzin
train/validation/test przed tworzeniem wariantów.

Uruchomienie: `.venv/bin/python scripts/vector_patch_school.py RAPORT_POPRZEDNIKA --run`.
Audyt: ten sam skrypt z `RAPORT_PATCHA --verify`.
Zapis doświadczenia: `RAPORT_PATCHA --record-experience PLIK_OCENY`.
96testów infrastruktury zaliczonych, w tym odrzucanie zmian chronionych
elementów, podmienionego źródła/odpowiedzi, innych instrukcji wejściowych,
złych wartości, samooceny i pozornych wartości logicznych zamiast odbioru.

## Autorstwo i przebieg

- `scripts/vector_school_contract.py`: wymagania ćwiczenia i niezależne
  sprawdzanie statycznego SVG, tekstów, układu i różnic obrazu.
- `scripts/vector_school.py`: lokalny model tworzy cały SVG. Wzorzec jest
  renderowany do PNG; pierwsza rekonstrukcja dostaje tylko te piksele
  i kontrakt, bez kodu wzorca lub jego tekstów przepisanych przez nauczyciela.
- Pierwsza poprawka dostaje własny poprzedni SVG i uwagi. Kolejne dwie
  pracują od nowa z obrazem i uwagami, bez poprzedniego SVG. Strategia,
  numer próby i dokładne wejścia są jawnie zapisane. Maksymalnie trzy poprawki.
- Asystent przygotowuje wymagania, pomiary i ocenę wizualną. Nie zmienia
  SVG, nie czyści odpowiedzi modelu i nie przepisuje produktu za model.
  Feedback nauczyciela zawiera obserwacje oraz pomiary do poprawienia.
- Każda próba zachowuje oryginalną odpowiedź, dokładny wyodrębniony SVG,
  żądanie, PNG, PDF, pomiary i SHA-256. SVG musi nadal odpowiadać treści
  modelowej odpowiedzi. Zmienione pliki źródłowe przerywają dalsze ćwiczenie.

Prywatne materiały znajdują się na Linuksie w
`/home/marcin/ai-company-workspaces/vector-school`. Brak publikacji plików
modelowych, zmian panelu, produkcyjnej bazy, routingu lub eksportu SFT.

## Zakres sprawdzianu

Ćwiczenie dotyczy fikcyjnych targów grafiki, jednej rodziny
`community-print-fair-001`, wyłącznie `development`. Wzorzec jest celowo
prosty: osiem wierszy angielskiego tekstu ASCII, płaskie figury, strona
592×840 jednostek. Nie zastępuje brakującej oryginalnej ulotki „Ping”.

Przed inferencją zapisano progi: dokładny komplet tekstów, maksymalna różnica
współrzędnych/wymiarów każdego pola tekstowego 12 jednostek, średni błąd RGB
≤0,045, udział pikseli różniących się o ponad 24 w którymś kanale ≤0,18.
To robocze progi ćwiczenia, nie skalibrowany standard zawodowej reprodukcji.
Kontrolowane są też marginesy i nakładanie pól tekstowych.

Po zauważeniu zasłoniętego podtytułu dodano pomiar elementu widocznego
w środku każdego niepustego znaku. Sam tekst obecny w DOM lub PDF nie
oznacza jego widoczności. Ten pomiar jest przybliżeniem: nie mierzy pełnego
pokrycia glifów ani kontrastu. Pierwsza rekonstrukcja nie miała jeszcze tego
pola pomiarowego; błąd wykryto i zapisano w niezależnej ocenie wizualnej.
Zaliczenie pomiarów zawsze wymaga jeszcze niezależnego oglądu, nigdy
automatycznego przyjęcia do treningu lub publikacji.

## Renderowanie i eksport

`scripts/render_school_svg.py` dopuszcza tylko ograniczony, statyczny SVG:
brak skryptów, odnośników, rastrów, obcego HTML, stylów, deklaracji XML,
zewnętrznych zasobów i zagnieżdżeń. Niedozwolony wynik jest odrzucany,
a nie naprawiany przez filtr. Generowany Python/JavaScript nie jest wykonywany.

Własny Chrome headless ma osobny profil, zachowany sandbox, wyłączone GPU,
audio i rozszerzenia, usunięte zmienne sesji graficznej. Nie otwiera panelu
właściciela ani stron sieciowych. Statyczny dokument ma CSP `default-src 'none'`,
żądania renderera są blokowane. Stały kod CDP mierzy tekst, robi PNG i
wywołuje eksport PDF. [Dokumentacja protokołu](https://chromedevtools.github.io/devtools-protocol/).
Proces własnej przeglądarki jest zamykany po etapie.

PDF jest mechanicznym eksportem w skali 148×210 mm. Sprawdzane są jedna
strona A5, zachowanie zbioru słów, osadzenie fontów i brak obrazów rastrowych.
Ostatni eksport używał osadzonych Liberation Serif/Sans — to lokalne
zamienniki zadanych rodzin Georgia/Arial, nie dowód zgodności z fontami klienta.
Nie wykonano preflightu drukarni: brak wymagań spadów, profilu koloru,
PDF/X i docelowych fontów. Pole `print_ready` pozostaje `false`.

## Rzeczywista próba 21.09.2026

Model `qwen3.8:27b`, niezmieniony digest `22130167…79643`, kontekst8192,
limit2400 tokenów, 4 wątki, bez podmiany adaptera. Kontrola zasobów przed
każdym etapem potwierdziła brak aktywnych kontenerów i wolną pamięć GPU.

Wzorzec `source-xf_vocnb` powstał w16,874s: osiem wierszy, sześć figur,
SVG i jednostronicowy PDF. Nauczyciel obejrzał go jako wzorzec ćwiczeniowy;
podtytuł przy krawędzi pierścienia ma słaby kontrast. To nie odebrany projekt
graficzny ani zatwierdzony przykład treningowy.

| Próba | Katalog | Tekst dokładny | Pola tekstowe w tolerancji | Błąd RGB | Wynik |
|---|---|---|---|---|---|
| Pierwsza | `recreate-vcfusjdd` | 8/8 | 6/8 | 0,07522 | odrzucona |
| Poprawka1 | `recreate-ur8u8a9v` | 8/8 | 6/8 | 0,04743 | odrzucona |
| Poprawka2 | `recreate-456pyqiw` | 8/8 | 6/8 | 0,03780 | odrzucona |
| Poprawka3 | `recreate-4ma9o381` | 8/8 | 2/8 | 0,04731 | odrzucona |

Pierwsza poprawka usunęła dodatkowe boczne paski. Druga naprawiła zasłanianie
podtytułu i nagłówek, ale zmieniła rozmiar daty oraz stopki. Trzecia poprawiła
datę i stopkę, jednocześnie pogarszając nagłówek i pozostałe teksty.
Najnowsza wersja nie jest automatycznie najlepszą. Cztery próby trwały
8,242/7,930/7,883/7,945s, łącznie ze sprawdzeniem i renderowaniem.

Niezależny ogląd wszystkich pięciu PNG i ocena znajdują się w prywatnym
`source-xf_vocnb/teacher-assessment.json`, SHA-256
`14a018bb5c26930dd8f626f2651c3adfca58fee8b98bdf7f88f336b10483223d`.
Żadna odpowiedź nie została wyeksportowana do treningu. Potrzebna jest
nauka lokalnych, precyzyjnych zmian z kontrolą regresji; przepisywanie całego
SVG powoduje ponowne błędy w już poprawnych elementach. Dopiero szerszy
zbiór odebranych prac, trening i osobne rodziny testowe pozwolą ocenić transfer.

## Uruchomienie i testy

Bez `--run` skrypt nie wywołuje modelu. Nowy wzorzec:
`.venv/bin/python scripts/vector_school.py --run`.
Odtworzenie: ten sam skrypt z `--source /pełna/ścieżka/report.json`.
Poprawka dodatkowo `--revise /pełna/ścieżka/poprzedni/report.json` oraz opcjonalnie
`--feedback /pełna/ścieżka/teacher-feedback.json`, związanym z hashem poprzedniego
raportu. Zgoda systemowa jest potrzebna do dostępu do lokalnej Ollamy/Chrome
poza restrykcyjnym sandboxem narzędzia; nie oznacza zmiany autorstwa pracy.

66 testów zaliczonych: kontrakt, odrzucanie aktywnego/obcego SVG, widoczność,
błędy tekstu/położenia/koloru, ochrona autorstwa i plików, związanie feedbacku,
limity poprawek, kontrola eksportu oraz dotychczasowe testy wnętrz i Ollamy.
Rzeczywiste generacje i eksporty opisane wyżej stanowią osobne dowody integracji.
