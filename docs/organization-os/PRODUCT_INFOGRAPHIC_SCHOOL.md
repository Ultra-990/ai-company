# Lokalna szkoła infografik produktowych

`scripts/product_infographic_school.py` sprawdza pełną serię czterech grafik
dla jednego fikcyjnego produktu. Jest to próba rozwojowa odpowiadająca zakresowi
ogłoszenia o infografikach, nie rzeczywista oferta Amazon ani dowód konwersji.

## Zamrożony brief i autorstwo

FIELD 600 jest syntetyczną butelką. Brief ustala wygląd, nazwę oraz tekst
dostawcy dotyczący pojemności, zawartości zestawu, wymiarów, materiałów
i pielęgnacji. Cztery cele komunikacyjne są oddzielne: pojemność, wymiary,
materiały, pielęgnacja. Nieznane pozostają parametry termiczne, szczelność,
certyfikaty, wpływ środowiskowy i gwarancja; nie wolno ich dopisywać.

Lokalny model wybiera paletę i fonty, rysuje wzorzec produktu, pisze nagłówki
oraz ustala wszystkie współrzędne czterech grafik. Tekst dostawcy jest
wejściem ćwiczenia do dokładnego zachowania, nie swobodnym zadaniem copywriterskim.
Asystent nie rysuje ani nie poprawia produktów. Kompilator serializuje
odpowiedź do edytowalnego SVG i powtarza wzorzec bez zmiany jego kształtu,
kolorów lub napisu, z przesunięciem i skalą wybranymi przez model.

Wzorzec jest ilustracją lokalnego modelu. Próba nie sprawdza jeszcze
wiernego wykorzystania zdjęć prawdziwego produktu ani fotorealizmu.
Do rzeczywistej realizacji nadal potrzebne są zdjęcia, potwierdzone dane,
zasoby marki i wymagania docelowego rynku oraz kategorii.

## Przebieg i ocena

Model najpierw tworzy styl i wzorzec 600×800, potem cztery grafiki 1500×1500.
Przy układaniu grafik otrzymuje pomierzone granice wzorca i deklarację
dosłownego powtórzenia produktu przez narzędzie. Nie musi przepisywać
rysunku ani ponownie generować jego nazwy. Każdy etap zachowuje surową
odpowiedź, żądanie i maksymalnie dwie próby poprawy po niezależnym błędzie.
Awaria infrastruktury nie jest błędem projektu do poprawiania przez model.

Kontrole wymagają dokładnego tekstu specyfikacji, zgodności palety i fontów,
czytelnego rozmiaru tekstu, marginesów oraz braku kolizji tekstów z produktem.
Samo przejście tych kontroli nie dowodzi prawdziwości dowolnego nagłówka,
dobrego wyglądu butelki lub skuteczności sprzedażowej. Te aspekty wymagają
osobnej oceny. Nie ma automatycznego zatwierdzania estetyki ani eksportu SFT.

Renderer używa izolowanego Chrome headless bez pulpitu i zewnętrznych stron.
Przetwarza tylko walidowane statyczne SVG; nie wykonuje kodu modelu.
Eksporty obejmują SVG, PNG 1500×1500, małe PNG 600×600 i rzeczywisty PDF.
PDF służy tu przeglądowi wektorów, nie deklaracji gotowości do druku.
Pakiet zawiera też styl, brief, manifest hashy i ZIP.

Weryfikacja bez inferencji odtwarza SVG z oryginalnych odpowiedzi,
sprawdza rzeczywiste wymiary PNG, teksty/fonty/wektory PDF oraz zgodność
plików eksportowych i ZIP. Raport pozostaje `pending_independent_review`
do osobnego odbioru; `verified` oznacza kontrolę techniczną.

```bash
.venv/bin/python scripts/product_infographic_school.py --run
.venv/bin/python scripts/product_infographic_school.py --resume /home/marcin/ai-company-workspaces/product-infographic-school/series-FAILED
.venv/bin/python scripts/product_infographic_school.py --verify /home/marcin/ai-company-workspaces/product-infographic-school/series-ID
```

Bez flag skrypt pokazuje brief bez uruchamiania modelu. Kod wykonywany
w próbie jest kopiowany do prywatnego katalogu wyników przed startem.

Po wyczerpaniu poprawek etapu można jeden raz wznowić nieudaną próbę.
Wznowienie sprawdza hashe poprzednich odpowiedzi, zachowuje ukończone etapy
i przekazuje ostatnią odrzuconą odpowiedź z błędem do modelu. Kopie wcześniejszych
odpowiedzi są jawnie oznaczone jako odziedziczone; raport odróżnia je od nowych
wywołań. Odtwarzanie i pomiary są ponawiane, inferencja ukończonych etapów nie.
Druga kontynuacja tej samej gałęzi jest odrzucana. Nie jest to jeszcze
automatyczne wznowienie przez harmonogram ani samodzielny trening wag.

## Zakres wskazówek platformy

Odczyt 22.09.2026: [wpis pracownika Amazon o obrazach produktowych](https://sellercentral.amazon.com/seller-forums/discussions/t/13af96ea-6b07-4bf9-8dbe-a13292c2e3b1)
rozróżnia zdjęcie główne i dodatkowe infografiki; zaleca też sprawdzanie
czytelności na małych ekranach. Na tej podstawie ćwiczenie dotyczy wyłącznie
grafik dodatkowych. Wpis ogólny nie zastępuje reguł konkretnej kategorii,
nie zatwierdza ilustracji fikcyjnego produktu jako rzeczywistej oferty
i nie stanowi dowodu zgodności całego pakietu z Amazon.

## Wynik rzeczywistej próby 22.09.2026

- `series-o12zcg1h`: pięć wywołań, 46,652 s, przerwanie na pierwszej
  infografice. Model powtarzał nazwę produktu, zmieniał tekst dostawcy
  i używał zbyt małych napisów. Wzorzec był nadmiernie uproszczony.
- `series-e451m0qr`: 12 wywołań, 107,751 s. Model sam skorygował wystający
  element wzorca i kolizję nagłówka z produktem. Poprawiał też liczby
  przesunięcia zapisane błędnie z prefiksem `#`. Seria przerwana na czwartej
  grafice przez kolizję napisów i przekroczony dolny margines.
- `series-yih19fc7`: ograniczone wznowienie, 19,06 s i tylko dwie nowe
  odpowiedzi. Dziewięć wcześniejszych odpowiedzi odziedziczono i sprawdzono,
  bez ponownej inferencji ukończonych etapów. Cztery grafiki ukończone
  technicznie; 19 plików ZIP, pięć głównych PDF wraz ze wzorcem sprawdzonych
  niezależnym poleceniem `--verify`. Cztery małe podglądy mają po 600×600.

Wszystkie surowe odpowiedzi, błędy, wersje kodu i dowody pochodzenia zachowano
prywatnie. Łącznie było 19 nowych wywołań modelu w tych trzech przebiegach;
odziedziczonych odpowiedzi nie liczy się ponownie jako pracy modelu.

Obejrzano wzorzec i wszystkie cztery małe grafiki. **Odbiór wizualny:
needs_visual_revision, 0/4 gotowych do komercyjnej realizacji.** Zakrętka
jest niewiarygodna, nagłówek pojemności nieprecyzyjny, dekoracje odciągają
uwagę, a hierarchia i wykorzystanie przestrzeni różnią się między grafikami.
Dokładne uwagi dla kolejnej pracy modelu zapisano w osobnym
`independent-review.json`, SHA-256
`fbdbb9bfbe9f4ccdce738ec0be619666c44c0888589cf0af118d5b37ca2fffff`.

Raport wykonania pozostaje oryginalny; ocena nie przepisuje odpowiedzi
modelu ani nie zmienia wyniku technicznego w zatwierdzenie jakości.
Brak eksportu treningowego, aktualizacji wag, wdrożenia lub publikacji oferty.
Wymagania pełnej usługi i samodzielnego odbioru estetyki nadal niespełnione.

Dalszy etap: [poprawki z rzeczywistym PNG](PRODUCT_VISUAL_REVISIONS.md)
dały dwie niezależnie przyjęte korekty częściowe i dwa sprawdzone wejścia
do uczenia. Nie zmienia to odbioru oryginalnej serii; nie złożono z nich
nowego, zatwierdzonego pakietu czterech grafik.

Testy infrastruktury: pełne `.venv/bin/pytest -q` — **1674 passed, 21 skipped**,
84,24 s. Testy nie zastępują negatywnego odbioru wizualnego powyżej.
