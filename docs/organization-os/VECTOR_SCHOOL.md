# Szkoła odtwarzania ulotek

Stan 21.09.2026: lokalny Qwen wykonał syntetyczny wzorzec i cztery próby
odtworzenia z obrazu. SVG oraz PDF powstały, lecz **0/4 odtworzeń odebrano**.
Poprawki rozwiązywały część problemów, równocześnie zmieniając poprawne
elementy. Nie jest to gotowość do zlecenia klienta ani poprawa wag modelu.

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
