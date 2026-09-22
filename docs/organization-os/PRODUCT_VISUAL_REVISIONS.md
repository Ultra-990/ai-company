# Poprawki produktu na podstawie obrazu

`scripts/product_visual_revision.py` przekazuje lokalnemu modelowi rzeczywisty
PNG odrzuconego wyniku, powiązane uwagi oceny oraz chronione fakty i elementy.
Model sam zwraca operację narzędzia lub nową scenę. Asystent nie rysuje poprawki.
Mechanizm wykorzystuje przypięty lokalny model i istniejący ograniczony transport
wizyjny: jeden PNG, kontekst 8192, do 2400 tokenów odpowiedzi, bez narzędzi modelu.

## Dwa zakresy poprawki

Zakrętka: model może zastąpić końcową grupę kształtów w oryginalnym kolorze
zakrętki maksymalnie pięcioma własnymi kształtami. Pozostałe kształty oraz
napis są kopiowane dokładnie. Niejednoznaczny podział — wspólny kolor korpusu
i zakrętki lub nieciągła grupa — jest odrzucany. Nie odgaduje się geometrii
i nie poprawia odpowiedzi automatycznie.

Infografika: model tworzy nowy układ wokół tego samego produktu, zachowując
oba dokładne teksty dostawcy. Może zmienić własny nagłówek, tło i kompozycję.
Pierwsza wersja żądania zawierała także starą scenę; model kopiował jej zły
układ. Druga wersja zachowuje obraz, pomiary produktu, styl i fakty, lecz
nie podaje starych współrzędnych strony. Odtwarzanie historycznych rozmów
zachowuje dokładną serializację pierwszej wersji.

Każda próba zachowuje żądanie, odpowiedź, PNG, PDF, SVG, pomiary i hashe.
Po błędzie pomiarów dopuszczone są dwie poprawki lokalnego modelu.
Samo przejście pomiarów oznacza tylko oczekiwanie na niezależną ocenę.

## Rzeczywiste porównanie 22.09.2026

| Próba | Wynik | Ocena niezależna |
| --- | --- | --- |
| `visual-revision-ydy0u4z7` | Jedna odpowiedź, 5,283 s; 17 kształtów starej zakrętki zastąpione trzema | Przyjęta celowana naprawa: zamknięta, krótsza zakrętka; geometria trzech elementów korpusu i napis niezmienione |
| `visual-revision-cjpgxaw9` | Dwie odpowiedzi, 14,84 s; pierwsza miała kolizję produktu z tekstem, druga przeszła pomiary | Odrzucona: nadal nadmierna pusta przestrzeń i treść przy dole strony |
| `visual-revision-payf0fd4` | Jedna odpowiedź, 7,321 s; żądanie bez starych współrzędnych | Przyjęta celowana poprawa kompozycji: produkt w środkowej części, mniejsza luka pod nagłówkiem, rozdzielone fakty |

Obrazy przed i po obejrzano osobno. Źródła odtworzono z surowych odpowiedzi,
sprawdzono pomiary i rzeczywiste PDF. Poprawki są oddzielnymi próbami:
nowa zakrętka nie została wstawiona do przykładu poprawionej kompozycji,
który zgodnie z kontraktem zachowuje cały pierwotny produkt. Nie jest to
zatwierdzenie kompletnej serii ani wykazany efekt treningu wag.

Pozytywne oceny `learning-review.json` mają SHA-256:

- zakrętka: `bc8cf8b94323d7138bd4c13f6fcdd895e1562d9479d46fafffaef95a396fd544`;
- układ: `c0ab80dc37dd86e8e9e46f52c2d305cdf1a1348f1556d2f3242fbe9280a95042`.

## Dane do treningu i harmonogram

Kolektor `product-visual-revision-v1` eksportuje wyłącznie osobno przyjętą
poprawkę. Odtwarza dokładny prompt, odpowiedź, obraz oraz operację narzędzia;
wiąże pozytywną ocenę z raportem i wynikowym PNG. Do danych trafia wejściowy
obraz błędu i rzeczywista odpowiedź modelu, nie rozwiązanie napisane przez
asystenta. Rodzina `field-bottle-600-001` pozostaje w train.

Harmonogram automatycznie odkrywa oceny, eksportuje przyjęte rozmowy i audytuje
wejścia na CPU. Odrzuconą kompozycję pomija. Ponowny cykl wykorzystał istniejące
audyty bez duplikowania przykładów. Odczyt systemd potwierdził wykonanie usługi
22.09.2026 o 16:04:01–16:04:08 CEST, kod 0.

| Przykład | Tokeny | Zamaskowane | Nadzorowane | Tokeny obrazu |
| --- | ---: | ---: | ---: | ---: |
| Zakrętka | 2358 | 2198 | 160 | 475 |
| Kompozycja | 1732 | 1198 | 534 | 361 |

Oba audyty potwierdziły rzeczywiste tensory pikseli, dokładną maskę odpowiedzi
i odrzucenie wejścia bez obrazu. Nie załadowano wag ani nie inicjalizowano CUDA.
Stan intake: **73 rozmowy, pięć rodzin, sześć różnych obrazów**; validation/test
w tym intake nadal 0/0. Minima 200/25/50 niezmienione. To nadal mały zbiór,
nie 73 projekty. Automatyczne treningi i wdrażanie lepszych wag nie są podłączone.

Pełne testy: **1684 passed, 21 skipped**, 83,89 s. Gotowość pięciu usług,
samodzielny odbiór estetyki i poprawa na niezależnych zadaniach po treningu
pozostają niepotwierdzone.

Nowa bramka treningu zapisuje ten stan jako `continue_reviewed_intake`.
Żaden z tych przykładów nie uruchomił aktualizacji wag.
