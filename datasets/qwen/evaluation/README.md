# Oddzielna ocena napraw Qwena

Zestaw `repair-suite-001.json` powstał przed inferencją. Cztery rodziny nie
występują w 12 odebranych przykładach treningowych. Kod wejściowy jest wadliwy;
model ma jedną próbę naprawy na podstawie kontraktu i rzeczywistego logu błędów.
Niezależne testy pozostają niezmienione. Kod Qwena wykonuje tylko kontener.

Jest to **jawny, syntetyczny zestaw regresyjny**, nie prywatny końcowy holdout
ani reprezentatywny pomiar gotowości do dowolnych zleceń Upwork. Po obejrzeniu
wyników nie należy stroić modelu pod te przypadki i przedstawiać ich jako
nadal nieznanego testu. Dalsza ocena potrzebuje również nowych rodzin.

## Pierwszy wynik bazowy — 2026-09-13

| Przypadek | Wynik jednej próby | Metody unittest po naprawie |
| --- | --- | --- |
| Cytowane pola CSV, nowe linie i puste pola | zaliczone | 6 |
| Suma przedziałów, stykanie, kopie danych | zaliczone | 7 |
| Parametry formularza, powtórzenia i kodowanie | zaliczone | 6 |
| Średnia ruchoma, pełne okna i walidacja | zaliczone | 5 |

Łącznie **4/4 przypadki, 24 metody testowe** plus przypadki parametryczne.
Każda wadliwa wersja najpierw zawiodła na rzeczywistych asercjach. Wszystkie
osiem kontenerów potwierdziło kontrole izolacji i posprzątało swoje zasoby.
Przeczytano cztery odpowiedzi: używają standardowych operacji, bez odczytu
testów, uruchamiania procesów, dostępu do sieci czy ingerencji w runner.
Import urllib.parse dotyczy parsowania tekstu, nie pobierania URL.

Model: lokalny `qwen3.8:27b`, digest
`22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`.
Temperature0.2, context16384, output≤1200, threads8, think=false,
timeout90s, keep_alive0. Łącznie45.374s (inferencja+kontenery).
Nie wykonano retry, dostrajania promptów ani poprawek po wyniku tej serii.
Brak ustalonego seeda; jeden przebieg nie ocenia zmienności próbkowania.

[Pełny raport](baseline-001.json) SHA-256:
`1a37f1f4802bee6680b079fcb4dc725a8f81cab3ed4fc8f91b7f76f004884be2`.
Oryginał w workspace: `qwen-training/repair-evaluation-49tzsib6/report.json`,
SHA-256 `e86c0c20a93fc10f6994708d40e276685da28c6c9b5ec8d6c1689e8a3295d6f6`.
Różnica hashy wynika z formatowania kopii JSON, nie zmiany danych.

## Powtórzenie i porównywanie

```bash
.venv/bin/python scripts/evaluate_qwen_repairs.py
.venv/bin/python scripts/evaluate_qwen_repairs.py --run
```

Bez flagi tylko opis. Z flagą maksymalnie cztery inferencje i osiem kontenerów
sekwencyjnie, nowe archiwum bez nadpisania. Infrastruktura uszkodzona, brak
modelu lub niepotwierdzone sprzątanie oznaczają niepełną ocenę i pass_rate=null.
Nie jest to automatycznie dowód błędu rozumowania modelu. Prawidłowo wykonane
testy z wynikiem negatywnym są failed_tests, błędny JSON jest invalid_output.
Harness HTTP sprawdza zaufaną atrapę pomocniczą, nie produkt Qwena.

Surowy log testów jest ograniczony do12000znaków, a jego fragment w promptach
do10000; raport przechowuje dokładne wiadomości. Dla późniejszego porównania
bazy z adapterem należy odtworzyć TE SAME wiadomości, schemat, limity i testy.
Ponowny pomiar czasu logów może zmienić tekst promptu, więc nie wystarcza
sam identyczny identyfikator suite. Skrypt jest obecnie przypięty do bazy;
przyjmowanie innego adaptera i automatyczna porównywarka nie są jeszcze wdrożone.

## Ochrona przed mieszaniem zbiorów

Katalog ma przypięty hash w `scripts/qwen_evaluation_catalog.py`. Zmiana
przypadków wymaga nowej wersji, nie cichej podmiany po obejrzeniu odpowiedzi.
Walidator SFT odrzuca te rodziny w train i validation także przy wczytaniu
osobnego pliku. Wykrywa też dokładny brief z innym wrapperem/nazwą rodziny.
Brak lub zmiana katalogu blokuje walidację. Parafrazy nadal wymagają ręcznej
kontroli — nie deklarujemy automatycznego wykrywania semantycznego przecieku.

Raporty nie są rekordami treningowymi. Nie dopisano ich do liczby50 wymaganych
przykładów test w formacie SFT i nie włączono do uczenia. Mamy nadal12train,
0validation i0odebranych SFT test; osobno cztery wykonane próby oceny kodu.
Na tych czterech prostych zadaniach baza już zalicza wszystkie testy;
nie dowodzi to potrzeby ani korzyści z QLoRA. Potrzebne są trudniejsze próby
wieloplikowe, zgodność API/UI i kompletne realizacje, nie tylko większa liczba
wariantów tych samych ćwiczeń.
