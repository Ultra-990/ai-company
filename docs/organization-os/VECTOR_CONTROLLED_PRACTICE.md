# Samodzielnie sprawdzane ćwiczenia naprawy SVG

`scripts/vector_practice.py` przygotowuje dane z kontrolowanych usterek na
niezależnie zaakceptowanych wzorcach train. Pierwsze wywołanie lokalnego
modelu tworzy jedną celową usterkę atrybutu tekstu. Drugie wywołanie otrzymuje
obraz wzorca, katalog uszkodzonego SVG i pomiary geometrii. Nie otrzymuje
odpowiedzi twórcy usterki, oryginalnego SVG ani rozmowy poprzedniego wywołania.

Lokalny model wybiera zarówno wartość błędną, jak i naprawę. System stosuje
dosłowne operacje, sprawdza dopuszczalny element i atrybut, porównuje wynik
ze źródłem oraz odczytuje rzeczywiście wyrenderowany PNG/PDF. **Do nauki
trafia wyłącznie odtworzenie każdego bajtu zaakceptowanego SVG.** Wynik
mieszczący się w tolerancji obrazu, ale różniący się źródłem, jest odrzucany.

Nie są to nowe realizacje klienta, naturalne błędy modelu ani próby po
treningu. Pole `defect_origin=deliberate_local_model_perturbation` i opis
pochodzenia pozostają w rekordzie treningowym. Odbiór nazywa się
`exact_replay_of_independently_reviewed_reference`; nie podszywa się pod
osobną ocenę wzrokową nauczyciela. Poprawność oryginalnego wzorca nadal
wymaga wcześniejszej niezależnej oceny związanej z jego hashem.

Program jest ustalony przed wykonaniem: osiem linii, po jednym ćwiczeniu
rozmiaru fontu, współrzędnej x i współrzędnej y — 24 przypadki na rodzinę.
Plan wyznacza kierunek i minimalną wielkość usterki, nie wartości naprawy.
Każde wywołanie zaczyna się kontrolą zasobów. Brak zgody zasobowej zatrzymuje
pracę; skrypt nie zatrzymuje innych procesów. Render używa własnego Chrome
bez pulpitu i GPU. Oryginały oraz nieudane próby pozostają zachowane.

Przykładowe wywołanie po sprawdzeniu dostępności zasobów:

```bash
.venv/bin/python scripts/vector_practice.py /prywatny/wzorzec/report.json --count 24 --run
```

`--start` wybiera początek w ustalonej liście; bez `--run` brak inferencji.
`--verify` odtwarza dokładne operacje z odpowiedzi, sprawdza wejścia, obrazy,
PDF, rodzinę i niezależną ocenę wzorca, bez kolejnego wywołania modelu.
Tożsamość historycznego wykonawcy nie jest zastępowana tożsamością przyszłego
modelu produkcyjnego. Kod wykonawcy jest przechwytywany raz przy starcie
procesu i zapisywany w katalogu nowych serii.

Po pozytywnej kontroli powstaje dokładny `experience.json`. Istniejący
harmonogram nauki wykrywa go automatycznie. Do 16 oddzielnych rozmów jest
audytowanych w jednym załadowaniu procesora multimodalnego; limit dwóch
nowych audytów na cykl pozostaje bez zmian. Każdy przykład nadal ma własne
sprawdzenie pochodzenia i prawdziwy obraz. Powtórne wykrycie nie zwiększa
licznika przez duplikowanie danych.

Ten krok ogranicza konieczność ręcznego odbierania powtarzalnych napraw.
Nie automatyzuje tworzenia i oceny nowych kierunków graficznych, doboru
całego programu nauki, treningu wag ani wdrożenia modelu. Duża liczba
wariantów trzech wzorców nie zastępuje różnorodnych rodzin i sprawdzianów.

## Rzeczywista seria 21.09.2026

| Rodzina train | Zaplanowane ćwiczenia | Dokładne naprawy | Pozostałe |
| --- | ---: | ---: | --- |
| Warsztat ogrodniczy | 24 | 23 | Jedna usterka nie przeszła eksportu PDF |
| Degustacja restauracyjna | 24 | 24 | Brak |
| Giełda płyt | 24 | 22 | Jeden błędny eksport PDF i jedna blokada zasobów |

Łącznie 141 wywołań lokalnego modelu i 680,194 s etapów generowania/renderu.
Trzy zatrzymane przypadki nie dotarły do wywołania naprawiającego. **69
rzeczywistych napraw odtworzyło źródło bajt po bajcie**; niezależnie ponowiono
cały replay i kontrole PNG/PDF. Nie trzeba było ręcznie zmieniać odpowiedzi
ani oceniać wzrokowo każdej kopii wcześniej zaakceptowanego źródła.

Nie jest to wskaźnik skuteczności modelu przy dowolnej grafice: 72 próby
pochodzą z trzech wzorców, z jednego jawnie określonego atrybutu do naprawy.
Nie wykonywano treningu wag ani odpowiedzi z rodzin validation/test.
Prywatna ocena `controlled-practice-001-assessment.json` ma SHA-256
`cfa598365226424d81b00098afe22186a2f11acf6f9d0934433be289fd9969a1`.

Po audytach CPU zbiór multimodalny zawiera 71 unikatowych rekordów: 69
z tej serii i dwa wcześniejsze. Wszystkie mają rzeczywiste piksele oraz
sprawdzone maskowanie instrukcji; zakres 1552–2449 tokenów. Końcowa migawka
`controlled-practice-001-intake.json` ma SHA-256
`4f9a90dc21644abdfb63892734182c0a9294fd96df3951511542d618ddaad18a`.
Pełne testy infrastruktury: 1602 zaliczone, 21 pominiętych.
