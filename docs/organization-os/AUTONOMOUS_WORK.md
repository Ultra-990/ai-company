# Samodzielna praca lokalnych modeli

Właściciel 28.09.2026 polecił kontynuować rozwój do uzyskania samodzielnej
pracy. Przedmiotem oceny jest kompletna realizacja w zdefiniowanym zakresie,
a nie sam poprawny JSON, liczba testów infrastruktury czy liczba rekordów SFT.
Obowiązują reguły autorstwa lokalnych modeli z `AGENTS.md`.

## Kolejność wskazana przez właściciela 29.09.2026

Po potwierdzeniu gotowości modelu właściciel chce rozszerzyć jego umiejętności
w kierunku możliwości asystenta prowadzącego: analiza wymagań, planowanie,
programowanie, testowanie, diagnozowanie błędów i korzystanie z narzędzi.
Każdą kompetencję trzeba sprawdzić na osobnych zadaniach; nie zakładamy
automatycznie równego poziomu modeli ani nie obiecujemy go na podstawie SFT.

Następnie lokalny model ma kontynuować rozbudowę AI Company i zaprojektować
nowy interfejs. Asystent prowadzący rozwija narzędzia/naukę i niezależnie
ocenia pracę, zachowując autorstwo modelu. Szczegółowe instrukcje panelu
klienta i panelu właściciela właściciel przekaże po ukończeniu tych etapów.
Obecne działania nadal dotyczą pierwszego etapu, czyli gotowości modelu.

Właściciel dodatkowo wymaga maksymalnego przyspieszenia prac. Stosujemy
krótkie próby konkretnej usterki i literalne poprawki modelu, zanim ponowimy
pełne generowanie. Niezależne lekkie odczyty wykonujemy razem, a testy
dobieramy do zmiany. Pełne egzaminy uruchamiamy po wykazaniu poprawy
mechanizmu. Skrócenie czasu nie zmienia kryteriów odbioru ani autorstwa.

Kontrola treści ma oddzielny test `scripts/product_headline_holdout.py`
(16 nowych syntetycznych nagłówków, oczekiwane oceny poza żądaniami).
`scripts/product_headline_repair.py` przyjmuje zweryfikowany pakiet
i związany z nim raport lokalnego recenzenta, zmienia wyłącznie tekst
wadliwego nagłówka, ponownie renderuje i sprawdza jego znaczenie. Weryfikator
odtwarza literalną zmianę i rozmowy, raportuje też nowe zastrzeżenia recenzenta
wobec pozostałych paneli. Oddzielna pozytywna ocena obrazu i treści pozwala
złożyć nową paczkę przez `--assemble-reviewed`; cała paczka nadal wymaga
własnego odbioru. Pierwotny egzamin i dane treningowe pozostają bez zmian.

Naprawiony rysunek źródłowy można wykorzystać przez
`scripts/product_infographic_school.py --continue-source-repair KATALOG`.
Wymagane są: literalne poprawki lokalnego modelu, niezależne odtworzenie
pomiarów i związana pozytywna ocena faktycznego obrazu źródła. Kontynuacja
zachowuje ten sam brief, styl i poprawiony rysunek, generując tylko brakujące
panele. Nie tworzy fikcyjnej pełnej odpowiedzi modelu: pochodzenie źródła
wynika z oryginalnej odpowiedzi oraz zapisanych patchy. Nie wolno mieszać
tej kontynuacji z nowym egzaminem lub lekcją do innego zadania.

Eksperymentalne `--repair-visible-routes` w pilotażu geometrii uruchamia
kontrakt oznaczeń v6. Sam koniec linii ukryty pod właściwą częścią nie
wystarcza: jej dalsza trasa nie może przechodzić pod farbą innej części
produktu, bo widoczne wskazanie byłoby mylące. Renderer próbkuje trasę
co najwyżej w 2049 punktach; nie jest to pełny dowód widoczności dowolnych
krzywych lub złożonych zasłonięć. V5 pozostaje historycznym/domniemanym
kontraktem dotychczasowych przebiegów. V6 jest jawny dla napraw i złożonych
z nich nowych pakietów; stare wyniki nie są przepisywane.

## Kryterium zakończenia dla każdej usługi

Pięć usług pozostaje zgodnych z `scripts/upwork_qualification.py`: przegląd
techniczny, obrazy wnętrz/Pinterest, odtworzenie ulotki wektorowej, infografiki
produktowe i identyfikacja restauracji. Macierz historycznych dowodów nadal
ma znaczenie, ale samo ustawienie wszystkich pól na `true` nie jest dowodem
samodzielności.

Przed kwalifikacją kompletnego przebiegu wymagamy:

- trzech różnych, zamrożonych przed inferencją briefów końcowych spoza nauki;
- wykonania całego pakietu przez lokalne modele i narzędzia z zachowaniem
  surowych odpowiedzi, wersji kodu, konfiguracji, wejść i hashy artefaktów;
- niezależnej kontroli obowiązkowych faktów, plików, pochodzenia, eksportu
  i jakości właściwej danej usłudze, a także porównania ze wspólną bazą;
- zaliczenia wszystkich trzech pakietów bez ręcznych zmian produktu
  i bez doraźnych podpowiedzi asystenta w trakcie ocenianego przebiegu;
- dwóch zamrożonych prób korekt rzeczywistych błędów, rozpoznanych przez
  system i poprawionych w ograniczonym budżecie bez utraty już poprawnych cech;
- jawnego zatrzymania i raportu przy wyczerpaniu budżetu lub braku danych,
  zamiast oznaczania wadliwego wyniku jako ukończonego;
- niezależnego końcowego przeglądu kompletnych dowodów. Ocena autora
  własnej pracy nie zastępuje tej kontroli.

Wynik dotyczy przetestowanego zakresu, nie dowolnego zlecenia klienta.
Próby rozwojowe, poprawki po komentarzach asystenta i znane egzaminy są
oznaczane osobno. Nie zmieniamy wyników historycznych po rozszerzeniu
kontroli: aktualna ocena powstaje w odrębnym audycie. Nie przenosimy
przykładów egzaminacyjnych do zbioru treningowego.

## Kolejność pracy

Najpierw usuwamy potwierdzone ograniczenia narzędzi i niejasności instrukcji,
następnie zbieramy niezależnie zaakceptowane przykłady pełnych realizacji
i korekt. Trening wag wymaga poprawnych danych, zachowania bazowych wag
i porównania base/adapter na osobnych zadaniach. Adapter bez wykazanej
poprawy nie jest promowany.

Pierwsze próby infografik: rozdzielone instrukcje poprawiły źródła,
ale ówczesne kompletne kompozycje pozostawały odrzucone. Transformacja źródła była
ograniczona do skali 1,5 i dodatnich przesunięć, co utrudniało uzyskanie
czytelnego dużego produktu przy pustych marginesach oryginalnego płótna.
Wersjonowany kontrakt rozszerzył narzędzie bez zmiany samych kształtów;
sprawdzono go na tym samym źródle i stylu, z niezależnym odbiorem paneli.

Po pierwszych próbach rozszerzonego kontraktu i rozumowania pełny pakiet
ma już czytelny większy produkt. Otwarte problemy to znaczenie linii
wymiarowych, powiązanie materiałów z odpowiednimi częściami i niepotwierdzone
obietnice nagłówków. Następny kontrakt powinien wiązać wskazane przez model
elementy sceny z pomierzonymi granicami produktu/części, bez narzucania
gotowej kompozycji i bez ręcznego poprawiania współrzędnych. Znane błędy
pozostają próbami rozwojowymi; nowe briefy końcowe trzeba zamrozić osobno.

Kontrole funkcjonalnych oznaczeń zostały wdrożone eksperymentalnie
(`--functional-callouts`). Mierzą faktyczną geometrię i widoczną farbę
części; v2 wykrywa także przecięcia łączników. Rozumowanie poprawiło
układ materiałów, a rozdzielenie instrukcji paneli usunęło obcą miarkę
z care. Dwie zaakceptowane poprawki są danymi rozwojowymi. Składanie
zatwierdzonych rewizji (`--assemble-reviewed`, `--reviewed-revision`)
zachowuje literalne SVG i wymaga osobnego odbioru całej paczki.

Istotne próby i wyniki zapisujemy w `docs/WORK_LOG.md`. Historyczna
kwalifikacja przeglądu technicznego nie zostaje automatycznie zamieniona
w potwierdzenie wszystkich kryteriów samodzielnego przebiegu powyżej.

Pełny egzamin v2 zakończył się wynikiem technicznym 0/3 vs 1/3, lecz
odbiorem jakościowym 0/3 vs 0/3. `product_exam_visual_assessment.py` łączy
weryfikację niezmienionych wykonań z odrębnym oglądem źródła i czterech
paneli. Nawet trzy pozytywne odbiory wymagają jeszcze osobnych dowodów
autonomicznych korekt; narzędzie nie kwalifikuje samoczynnie usługi.

Badawcze `--source-contour` mierzy obrys korpusu w PNG źródłowym, aby
wykryć kwadratowe uskoki barków i przewężenie przy podstawie. Nie generuje
współrzędnych ani nie poprawia grafiki. Nie ocenia pełnej estetyki, zakrętki
czy dowolnych produktów z uchwytami/nóżkami; kolorowe pasy nie są uznawane
za fizyczne przerwy. Historyczne pakiety zachowują swoje dawne kontrakty.

Aktualizacja 29.09: v3 ma jeden niezależnie odebrany pełny pakiet w profilu
z rozumowaniem (GLEN), wobec zera w bazowym. Weryfikacja odtworzyła własne
korekty modelu bez dodatkowych wskazówek. Nadal brakuje trzech różnych
odebranych zleceń. Kontur v2 obejmuje także przewężenia przy barkach;
kontrola farby wykrywa dekorację scalającą się z wstawionym produktem.

Małe literalne poprawki geometrii naprawiły jedną miarkę, ale inne
technicznie poprawne wyniki odrzucono wizualnie. Pozostają osobną diagnozą,
bez automatycznej promocji. Lekcja z odebranego przykładu treningowego jest
osobno uwierzytelniana; nie jest aktualizacją wag. Pełne znane ćwiczenie
FIELD z tą lekcją i kontrolą farby zostało odebrane. Weryfikację przeniesienia
na nowe zadania prowadzi v4, z tą samą lekcją i budżetem dla obu profili.

V4 zakończone: 0/3 bazowy, 2/3 z rozumowaniem technicznie, ale 0/3 i 1/3
po odbiorze. DALE zaakceptowany; BRIAR odrzucony za niepotwierdzoną obietnicę
całodziennej wystarczalności, HIGHPOINT nie ukończył źródła. Potwierdzone
łańcuchy korekt nie zastępują odbioru całej pracy. Następne braki to
kontrola znaczenia nagłówków i proporcje/etykiety długich nazw.
