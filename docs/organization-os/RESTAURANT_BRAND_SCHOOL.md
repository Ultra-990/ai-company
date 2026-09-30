# Lokalna szkoła identyfikacji restauracji

`scripts/brand_school.py` wykonuje syntetyczne ćwiczenie odpowiadające
zakresowi ogłoszenia o identyfikacji restauracji. Lokalny model przygotowuje
plan stylu, dwa koncepty logo, uzasadnia wybór i projektuje wizytówkę.
Asystent rozwija wymagania, narzędzia i niezależną ocenę; nie rysuje logo
ani nie poprawia współrzędnych za model.

## Widoczność elementów obu logo — 30.09.2026

`--repair-artwork KATALOG --visible-shape-checks --artwork-reasoning`
włącza naprawę v5 wraz z kontrolami scen v4. Element, którego ukrycie nie
zmienia żadnego piksela o co najmniej 20 w kanale RGB kolorowego podglądu,
wraca do autora jako niemający mierzalnego wkładu. Dotyczy obu konceptów,
nawet niewybranego. Używa istniejących dowodów usuwania elementów, bez
dodatkowego wywołania modelu. Przyczyna może obejmować brak farby,
zasłonięcie, redundancję lub niski kontrast; to nie klasyfikacja kształtu.

`--run --visible-shape-checks` stosuje tę kontrolę przed akceptacją każdego
logo oraz przy eksporcie, pod osobnym kontraktem `brand-visible-source.v1`.
Weryfikator odtwarza pomiary z PNG. Nie zmienia reguł starszych przebiegów.
Integracja źródła pokryta testami; rzeczywista próba v5 poprawiła Maple
`artwork-repair-5wzsvck9` w jednym wywołaniu (19,593 s). Nowa latarnia
widoczna, pozostałe pięć SVG/PNG niezmienione. Cała paczka nadal wymaga
korekty opisu B; nie jest nowym zaliczonym egzaminem. 87 testów przeszło.

## Pełny egzamin v4 — 30.09.2026

`--delivery-exam-complete` zamraża nowe briefy Maple Lantern, Pebble Kitchen
i Meadow Loom. Łączy scoped scenes v1, naprawę obu konceptów/karty v4
i tekst v7 warm. Starsze v2/v3 zachowują swoje warunki. Odczyt i wznowienie
sprawdzają właściwy kontrakt źródła; znana naprawa nie staje się świeżym
egzaminem przez podmianę raportu.

Pierwszy `delivery-exam-ld9zzmd9`: 201,283 s, technicznie 2/3 baza i 1/3
rozumowanie, niezależnie 1/3 w obu (Pebble). W żadnym ramieniu dodatkowa
naprawa grafiki nie wywołała autora; porównanie nie mierzy przewagi profili.
Meadow sam poprawił układ, ale jego opis „woven line” nie odpowiada dwóm
niesplecionym owalom. Maple zatrzymała zapętlona ścieżka drugiego logo.

Osobne dokończenie Maple (96,214 s) dało czytelną kartę i drugie logo,
lecz zachowane logo A ma niewidoczne elementy i fałszywy opis latarni.
Pełna paczka nadal odrzucona. Recenzja tekstu (14,258 s) wykazała też
błędną interpretację relacji względem środka jako rozdzielenia całych ramek.
Potrzebna kontrola opisów wobec widocznego wyniku, a nie tylko deklarowanej
geometrii. Te ograniczenia pozostają jawne; bez kwalifikacji i treningu.
116 powiązanych testów przeszło. Nie powtarzamy inferencji wyłącznie po to,
żeby uzyskać korzystniejszy wynik z tego samego znanego zadania.

## Wymagania etapów, oba logo i liczba wierszy — 30.09.2026

Nowa generacja: `--run --scoped-scenes`. Kontrakt `brand-scoped-scene.v1`
podaje osobno zadanie logo oraz karty i wiąże tekst w schemacie z danymi
briefu/planu. Błędny tekst daje dokładne expected/observed. Model sam
wybiera kształty i układ; nie otrzymuje gotowych współrzędnych. Marginesy
obejmują kształty i grubość obrysu; eksport i weryfikacja egzekwują kontrakt.

Naprawa ukończonego źródła: `--repair-artwork KATALOG --complete-scene-checks
--artwork-reasoning`. V4 sprawdza oba logo i kartę, nie tylko wybrany znak.
Budżet to trzy próby na etap, do dziewięciu dodatkowych wywołań. Kontrole
monochromu, chronionych etapów, kopii dostawy i autorstwa pozostają aktywne.
Ramki powiększone o połowę obrysu nie dowodzą obwiedni wszystkich łączeń miter.

Poprawka treści: `--revise-wordmark-text KATALOG --warm-revision`. V7
uzupełnia dotychczasowy odczyt relacji o twierdzenia dotyczące liczby wierszy
samej nazwy. Model musi podać dokładny cytat, a wynik porównywany jest z
rzeczywistą strukturą SVG. Nie dodaje wywołań do pięciokrokowej serii.
Recenzję v7 bez korekty sprawdza `brand_guide_revision.py --verify KATALOG
--review-only`, ze świeżym renderem obu logo i weryfikacją dwóch wywołań.

`python -m scripts.brand_scene_recovery --run KATALOG` służy do osobnego
rozwojowego dokończenia źródła zatrzymanego po trzech błędnych próbach logo B.
Plan/logo A są chronione, wcześniejsze odpowiedzi i wynik pozostają zachowane.
Nowy budżet jest jawny, niezależny od wyczerpanego egzaminu; nie kwalifikuje usługi.

Rzeczywiste poprawki Tide (22,606 s), Stone (15,073 s), Willow (69,112 s
plus 11,477 s recenzji) odebrane jako kompletne syntetyczne pakiety.
104 testy przeszły. Historyczny egzamin nadal 0/3; potrzebny nowy zamrożony
pełny przebieg oraz oddzielne dowody korekt. Nie zmieniono oryginalnych wag.

## Egzamin v3 i wznawianie po preflight zasobów

`--delivery-exam-strict` zamraża trzy nowe briefy: Willow Hearth, Stone
Market i Tide Garden, z kontrolą karty v3 oraz opisów/tła v6. Budżety
pozostają równe, pierwotne źródło wspólne na parę, profile różnią się tylko
dodatkową naprawą grafiki. Starsze `--delivery-exam` zachowuje kontrakt v2.

Po terminalnym przerwaniu przez preflight można uruchomić:

```bash
.venv/bin/python -m scripts.brand_delivery_resume --resume KATALOG_EGZAMINU
.venv/bin/python -m scripts.brand_delivery_resume --verify KATALOG_KONTYNUACJI
```

To ograniczona kontynuacja oryginalnego egzaminu, nie nowy egzamin i nie
reset budżetu. Wymaga niezmienionych briefów/kodu, zachowuje wcześniejsze
źródła i ukończone ramiona. Ponawia grafikę jedynie, gdy preflight przerwał
ją przed dodatkową inferencją. Nie obsługuje dowolnego błędu modelu ani
kolejnych przerwań kontynuacji; wtedy pozostawia raport nieukończenia.

Rzeczywisty egzamin przerwał trzysekundowy test przepustowości Vast.ai.
Kontynuacja dokończyła brakujące etapy, a odczytowy audyt potwierdził
pochodzenie i zachowane rendery. Wynik: technicznie 2/3 w obu ramionach,
niezależnie 0/3. Pozostały błędna nazwa, fałszywy opis liczby wierszy i
margines drugiego logo; potrzebne poprawki przed kolejnym pełnym przebiegiem.

## Selektywne poprawki z kontrolą dekoracji i tła — 30.09.2026

`--repair-artwork KATALOG --strict-card --artwork-reasoning` włącza
kontrakt v3: dekoracje spoza wstawionego logo nie mogą wchodzić w ramki
tekstu wizytówki. Uwzględnia grubość obrysu, pomija pełne tło w kolorze
papieru, uwierzytelnia kolejność kształtów i sprawdza również końcowy eksport.
Kontrola ramki jest konserwatywna dla pustych figur i krzywych; nie zastępuje
oglądu. Model otrzymuje pomiary, sam wybiera rozwiązanie i współrzędne.

`--revise-background-text KATALOG --warm-revision` włącza kontrakt v6
nad v5. Zestawia tusz z dostarczonym papierem i nie przepuszcza automatycznie
angielskich odniesień do nieokreślonego ciemnego tła przy ciemnym tuszu.
Także negacje trafiają do doprecyzowania: filtr nie rozstrzyga ich zakresu.
Autor sam pisze zasadę opartą na dostarczonej palecie. Maksymalnie pięć
wywołań, krótka istniejąca retencja; bez nowych wywołań i renderów dla tych
dwóch kontroli. Wszystkie starsze kontrakty nadal dostępne bez zmian znaczenia.

Rzeczywisty Saffron: jedna poprawka karty, 55,206 s; opis 16,125 s.
Pełny poprawiony syntetyczny pakiet przeszedł niezależny odbiór i świeży
render kontrolny. To znana naprawa, nie nowy egzamin; pierwotne 2/3 pozostaje.
86 powiązanych testów przeszło. Pakiet prywatny `guide-revision-cliptb8z`.

## Zakres pierwszego briefu

Juniper Table jest fikcyjną restauracją o sezonowym, roślinnym menu,
skierowaną do dorosłych spotykających się na swobodne kolacje. Nazwa,
charakter i fikcyjne kontakty `.example` są zamrożone przed generowaniem.
Nie jest to rzeczywiste zlecenie, istniejąca restauracja lub portfolio klienta.

Model wybiera paletę, fonty z dostępnej pary Arial/Georgia, hasło i zasady
stylu. Koncepty różnią się symbolami lub kompozycją i muszą zachować
własny plan typograficzny. Wybór konceptu odbywa się na podstawie danych
sceny; nie udaje wizyjnej oceny dwóch podglądów. Ocena wzrokowa jest osobna.

Pakiet zawiera edytowalne SVG, podglądy PNG, rzeczywiste PDF, plan JSON,
zasady stylu Markdown i archiwum ZIP. Logo ma pole 600×360, wizytówka 850×550
i fizyczny PDF 85×55 mm. Mały podgląd logo ma 240×144 piksele.

## Autorstwo i kontrola

Model zwraca współrzędne, kształty, teksty, kolory i umiejscowienie logo.
Kompilator jedynie serializuje wartości do XML. Na wizytówce powtarza
wybrane logo bez zmian, stosując wyłącznie translację i skalę wybraną
przez model. Wersja jednokolorowa jest jawnym działaniem narzędzia:
wszystkie istniejące kolory fill/stroke poza none zastępuje kolor
monochrome_ink wybrany wcześniej przez model. Nie jest to ręczny retusz.

Profile brand_logo i brand_card rozszerzają wspólny bezpieczny renderer.
Dotychczasowy profil ulotki zachowuje stronę A5, osiem tekstów i zakaz grup.
W wizytówce dopuszczona jest tylko jedna warstwa grup z ograniczoną
translacją i skalą. Skrypty, zewnętrzne zasoby, CSS, rastry w SVG i dowolne
transformacje pozostają zabronione. Chrome działa headless, w osobnym
profilu i grupie procesów, bez sesji graficznej właściciela.

Sprawdzane są: dokładna nazwa i kontakty, zgodność palety i typografii,
obecność parametrów sceny, marginesy, widoczność tekstu, kolizje symbolu
z napisem, mały tekst na wizytówce oraz realne rozmiary PDF i PNG.
PDF musi zachować tekst, osadzone fonty i wektorową zawartość. Kontrole
geometrii są wymaganiami tego ćwiczenia, nie pełną oceną estetyki marki.

Błąd walidacji wraca do lokalnego modelu wraz z jego surową odpowiedzią
i hashami dowodów. Maksymalnie dwie poprawki na etap. Problemy zasobów
lub dostawcy modelu nie uruchamiają tej pętli. Każda wersja pozostaje
zapisana; generator nie zastępuje błędnych wartości rozwiązaniem nauczyciela.

```bash
.venv/bin/python scripts/brand_school.py --run
```

Bez `--run` skrypt tylko pokazuje brief. Wyniki są prywatnie zapisywane
w ai-company-workspaces/brand-school. Samo utworzenie pakietu nie oznacza
odbioru ani eksportu danych treningowych. Gotowość do druku wymagałaby
rzeczywistych wymagań drukarni; ten pilot nie deklaruje CMYK, spadów,
oceny oryginalności lub praw do komercyjnej marki.

## Zaobserwowane problemy

Pierwsze próby ujawniły kolejno nazwy kolorów zamiast HEX, zbyt długie
i ucięte opisy, sprzeczność fontu konceptu z własnym planem, ucięte nazwy,
nakładanie symbolu na napis i kontakt poza dolnym marginesem wizytówki.
Pierwszy pełny pakiet identity-lqrcvf6m został oznaczony needs_revision,
obejrzany i zachowany. Nie przyjęto go jako poprawnego przykładu do treningu.
Po tych wynikach doprecyzowano kontrakt i dodano pomiary renderowania
do automatycznego feedbacku. Nie poprawiano samych plików projektu.

## Wynik próby 22.09.2026

`identity-_u6wyy68`: pięć odpowiedzi przypiętego lokalnego Qwen, 33,496 s,
bez poprawek w tym przebiegu. Model przygotował oba koncepty, wybrał A
i rozmieścił logo oraz teksty na wizytówce. Niezależny audyt potwierdził
71 hashy artefaktów, dosłowne odtworzenie SVG z odpowiedzi, sześć PDF
z osadzonymi fontami i bez rastrów oraz zgodność 21 plików ZIP.

Obejrzano oba koncepty, wizytówkę, wersję jednokolorową i mały podgląd.
Teksty są czytelne, bez wcześniejszego ucięcia i kolizji. Pakiet zalicza
syntetyczną próbę techniczną, z ograniczeniami projektu: prosty, mało
wyróżniający symbol alternatywny, brak diagramu pola ochronnego i minimalnego
rozmiaru reprodukcji w zasadach stylu. To jeden brief, nie potwierdzenie
profesjonalnej gotowości usługi ani samodzielnego odbioru estetyki.

Audyt pozostaje obok raportu jako `independent-audit.json`, SHA-256
`20d96a4542e059ece46675fd4fc4b038e15fdae0202fe583fcb434724dc766e8`.
Nie zmieniono oryginalnego raportu, nie wyeksportowano danych do treningu,
nie trenowano wag i nie wdrożono adaptera w tym etapie. Pętla poprawek
ma test infrastruktury; ta udana próba nie wymagała jej uruchomienia.

## Pełne porównanie trzech nowych briefów

`scripts/brand_school.py --full-exam` zamraża trzy syntetyczne briefy testowe
(Tide & Hearth, Ember Yard, Willow Breakfast), przypięty model, budżety
i kopie kodu przed inferencją. Porównuje profil bazowy oraz rozumowanie,
z naprzemienną kolejnością i jednakowym limitem 8192 tokenów odpowiedzi,
16384 kontekstu, 180 s i trzech prób na każdy z pięciu etapów. Nie przyjmuje
dodatkowych wskazówek ani kontynuacji wcześniejszych projektów.

`scripts/verify_brand_package.py KATALOG` odtwarza sceny z dosłownych
odpowiedzi i łańcuchy poprawek, wybór i powtórzenie logo, konwersję
jednokolorową oraz instrukcję stylu. Sprawdza rzeczywiste PDF-y, wymiary PNG,
hashe i dokładną zawartość 21 plików ZIP. Zachowane pomiary układu nie
zastępują niezależnego oglądu obrazu i znaczenia tekstu.

`scripts/brand_full_exam.py --assess KATALOG` weryfikuje równe warunki,
niezmieniony kod i pochodzenie wyników wszystkich sześciu wykonań. Wynik
techniczny pozostaje oddzielony od końcowego odbioru; żadna z tych komend
nie kwalifikuje samodzielności ani nie eksportuje egzaminu do treningu.

Pierwsze uruchomienie `brand-exam-s5xiz5s0` zostało przerwane kodem 143
podczas szóstego wykonania. Przyczyna nieustalona; potwierdzono brak procesu
i pustą listę modeli Ollamy. Zapisano oddzielne `interruption.json`,
zachowując raport i odpowiedzi niedokończonego `identity-cnq86kmu`.
**Brak kompletnego wyniku egzaminu**; nie powtórzono ukończonych prób.

Zachowane wyniki: bazowy Tide & Hearth 33,131 s, Ember Yard 29,668 s,
Willow Breakfast 32,254 s — wszystkie technicznie kompletne. Rozumowanie:
Tide & Hearth 144,268 s technicznie kompletny; Ember Yard 107,953 s,
nie naprawił kolizji symbolu z napisem w limicie prób.

Niezależny odbiór zaakceptował syntetyczny pakiet Willow
`identity-v0fs3gxq`. Pozostałe ukończone zestawy wymagają zmian: bazowy
Tide podaje nieuzasadnione minimum logo 12 mm (napis około 2,72 pt),
rozumowanie obiecuje inny mały wariant i inne grubości fontu niż faktycznie
dostarczone, a bazowy Ember zaleca ciemny tusz na ciemnym papierze i ma
bardzo słaby kontrast alternatywnego symbolu. Dłuższe rozumowanie nie
zapewniło poprawnego pełnego pakietu. Recenzje zapisano obok artefaktów.

## Ograniczone poprawki instrukcji przez lokalny model

`scripts/brand_school.py --revise-guide KATALOG` sprawdza źródłowy kompletny
pakiet i przekazuje recenzentowi rzeczywiste teksty/fonty z SVG, katalog
plików, identyczność małego SVG z wybranym logo i brak zweryfikowanego
minimum drukarskiego. Nie przekazuje ludzkiej diagnozy. Lokalny autor może
zmienić tylko indeksy zasad zakwestionowane przez lokalnego recenzenta.
Pozostałe pola planu i wszystkie 18 plików grafik pozostają identyczne.
Limit: jedna ocena, jeden patch i jedna ponowna ocena; maksymalnie 3 wywołania.

Nowy ZIP powstaje tylko przy pozytywnej ponownej ocenie, a jego status nadal
wymaga niezależnego odbioru. `scripts/brand_guide_revision.py --verify KATALOG`
odtwarza trzy żądania i odpowiedzi, literalne zmiany, tekst instrukcji,
manifest i ZIP; ponownie weryfikuje źródło, z którym porównuje chronione
grafiki. Oryginalne paczki i wyniki egzaminu pozostają bez zmian.

Wyniki 29.09:

- `guide-revision-skdhoi3t`: 14,573 s, usunięte niezweryfikowane minimum
  12 mm w bazowym Tide & Hearth. Niezależnie odebrany poprawiony pakiet
  syntetyczny; pole ochronne pozostaje opisane jakościowo, bez gotowości
  drukarskiej. Ogląd niezmienionych obrazów dziedziczony przez identyczne hashe.
- `guide-revision-wssvw5dq`: 16,472 s, `needs_revision`. Autor poprawił
  wagi fontu na faktyczne 700/400, ale recenzent je odrzucił mimo zgodnych
  danych i żądał dowodów drukarskich dla porady o podglądzie cyfrowym.
  Występują też ucięte uzasadnienia. Nie złożono nowego ZIP-a ani nie
  zastąpiono nieudanej oceny ręcznym sukcesem.
- `guide-revision-um5vc3r4`: 14,415 s, poprawione użycie ciemnego tuszu
  w Ember Yard na warunkowe użycie przy wystarczającym kontraście.
  Odebrana sama poprawka zasad; cały pakiet nadal wymaga zmiany bladego
  alternatywnego symbolu i niespójnych opisów konceptów w planie.

`scripts/brand_school.py --guide-review-exam` zamraża cztery nowe syntetyczne
zestawy metadanych: 16 zasad, osiem poprawnych i osiem wadliwych. Oczekiwane
oceny nie są w żądaniach. `guide-holdout-1er2kor3`: 15/16 trafnych oznaczeń
w 22,759 s. Błąd: utożsamienie wybranego logo z nieistniejącym osobnym SVG
samego napisu. Dwa poprawne oznaczenia mają ucięte uzasadnienia. Weryfikator
odtworzył wynik i rozdzielenie oczekiwań; niezależny przegląd nie kwalifikuje
recenzenta. Nie wdrożono go jako samodzielnej bramki pełnej realizacji.

Poprawki znanych pakietów i test recenzenta nie zastępują nowego egzaminu
całej usługi. Potrzebne są bardziej jednoznaczne fakty o strukturze wariantów,
pełne krótkie uzasadnienia oraz kontrola zgodności opisów konceptów z obrazem.
Bez eksportu do treningu, zmiany wag i automatycznej kwalifikacji.

## Kontrola całego opisu na podstawie SVG i nowe pełne przebiegi

Jawne `--revise-plan-text KATALOG` używa `brand-plan-factual-review.v2`.
Model otrzymuje pełne zweryfikowane SVG, liczby węzłów tekstu/kształtów,
atrybuty tekstu i listy plików bez kształtów lub bez tekstu. To strukturalne
fakty XML, nie dowód widoczności dowolnego SVG. Ocenia sześć pól: cztery
zasady oraz dwa opisy konceptów. Uzasadnienie ma być krótkie, kompletne
i zakończone interpunkcją. Tolerancja subiektywnego opisu symbolu nie
usprawiedliwia błędnego fontu lub położenia; zastosowanie cyfrowe nie wymaga
wymyślonego testu drukarskiego.

Patch może zmienić tylko zakwestionowane pola; schema odpowiedzi ogranicza
ich indeksy i liczbę już podczas generowania. Wagi, geometria, kolory, fonty,
tagline i pozostałe treści pozostają zachowane. V1 i jego historyczne dowody
są nadal odtwarzalne; nowy kontrakt jest jawny w raporcie.

Pierwszy znany Tide (`guide-revision-q6bj69t8`, 11,913 s) odrzucono, ponieważ
autor zwrócił także niezakwestionowane pola. Po ograniczeniu schemy nowa
próba `guide-revision-ytbe8bt0`, 18,844 s, poprawiła 700/400 w instrukcji,
700 w koncepcie A, niepotwierdzone 22 mm i położenie napisu w koncepcie B.
Literalna weryfikacja i niezależny odbiór poprawionego syntetycznego pakietu
zachowane; terminologia „horizontal lockup” pozostała luźna przy jednoznacznym
opisie napisu pod symbolem. Bez kwalifikacji lub zmiany starego egzaminu.

`--plan-review-exam` zamraża nowe 24 twierdzenia (12 poprawnych, 12 błędnych)
na podstawie istniejących grafik modelu. `guide-holdout-vik_1i_u`: 24/24,
23,988 s, wszystkie uzasadnienia sprawdzone niezależnie i kompletne.
To nowe teksty na znanych rysunkach, nie nowe zlecenia projektowe.

`--workflow-exam` tworzy trzy całkowicie nowe źródłowe pakiety: Cedar Lunch,
Copper Oven, Harbor Plate. Dwa warianty kontroli opisów otrzymują ten sam
niezmieniony pakiet źródłowy w każdej parze i jednakowy limit trzech wywołań
(8192 kontekstu, 1800 odpowiedzi, 90 s). Wspólna generacja ma standardowy
limit trzech prób na etap; kolejność wariantów jest naprzemienna. Jest to
porównanie par na wspólnym źródle, nie sześć niezależnych generacji. Zamrażane
są briefy, budżety i kod; brak ręcznych podpowiedzi i danych do nauki.

`workflow-exam-savnqkh9`, 148,161 s: technicznie 2/3 w obu wariantach,
po niezależnym oglądzie i kontroli opisów **0/3 w obu**. Weryfikator
`brand_workflow_exam.verify` potwierdził źródła, wspólne pary, budżety,
niezmieniony kod, dosłowne poprawki i wynik; nie zatwierdza wizualnie paczek.

- Cedar Lunch: jednokolorowy eksport wypełnił jasne wycięcie liścia i zmienił
  znak w pełne koło. Rozszerzona kontrola poprawiła nieprawdziwy opis liścia
  w literze C, lecz grafika pozostaje wadliwa; „beside” jest mniej precyzyjne
  niż rzeczywiste położenie osobnego symbolu ponad lewą częścią napisu.
- Copper Oven: generacja wyczerpała poprawki nakładających się napisów
  „Copper Oven” i „Baked together”; żaden wariant kontroli nie naprawia
  niekompletnego źródła ani nie tworzy z niego fałszywej dostawy.
- Harbor Plate: obrazy są czytelne, lecz opis mówi o fali pod napisem
  i okręgu otaczającym tekst, podczas gdy oba symbole leżą nad napisem.
  V2 zatwierdził błędne twierdzenia, nawet przy uzasadnieniu, które jednemu
  z nich wprost przeczy. V1 również nie odrzucił całego pakietu.

Wniosek z pełnego przebiegu: dobry wynik izolowanego przeglądu tekstu nie
wystarcza. Potrzebna jest kontrola zgodności znaku po konwersji monochromowej,
przekazywanie rzeczywistych pomiarów kolizji autorowi oraz deterministyczne
sprawdzenie deklarowanych relacji przestrzennych względem pomiarów renderera.
Sam werdykt modelu nie może uchylać takiego stwierdzonego konfliktu.

## Mierzone relacje przestrzenne (eksperymentalne v3/v4)

`--revise-spatial-text KATALOG` dodaje odczyt relacji z dwóch samych opisów
oraz veto na podstawie ramek SVG: nad/pod/lewo/prawo, pozioma sąsiedniość,
otaczanie, nakładanie. Potrzeba pięciu wywołań na pełną poprawkę. Autor
pisze tekst, a narzędzie zachowuje wszystkie grafiki i chronione pola.
Weryfikator wykonuje ponowny izolowany render obu logo. Ramki mogą obalić
sprzeczność; nie dowodzą otaczania przez krzywą ani jakości wizualnej.

`--revise-spatial-subjects KATALOG` (v4) wymaga dosłownego cytatu podmiotu
i relacji, a odwrócenie relacji dla napisu wykonuje kod. Jest to ograniczony
angielski walidator, nie pełny parser języka. Błędne lub niejednoznaczne
wyjście zatrzymuje przebieg. To eksperyment, nie domyślna kontrola produkcji.

Harbor v3 guide-revision-wdysbmad: odebrana poprawka obu opisów, 23,722 s,
18 niezmienionych grafik i 21 plików ZIP. Pierwsza próba needs_revision
pozostaje zachowana. Pełny wcześniejszy egzamin nadal 0/3 dla obu ramion.

Test `--spatial-claim-exam`: v3 14/16 z dwoma odwróconymi kierunkami.
`--spatial-subject-exam`: pierwsza próba nowego katalogu i jej powtórzenie
zatrzymane przez zbyt restrykcyjną walidację poprawnych cytatów. Po naprawach
osobny replay dał 16/16 z zachowanych odpowiedzi; zero nowych wywołań,
oryginalne failed zachowane. Pełna próba v4 Harbor została z kolei poprawnie
zablokowana za błędny kierunek względem podmiotu. Wynik izolowanego replay
nie kwalifikuje recenzenta ani całej usługi do autonomicznej pracy.

## Ograniczona seria bez wielokrotnego ładowania modelu

Do `--revise-guide`, `--revise-plan-text`, `--revise-spatial-text` albo
`--revise-spatial-subjects` można dodać `--warm-revision`. Budżet i wymagania
jakości pozostają takie same. Model zostaje w pamięci do trzech sekund
między krokami; końcowy krok ma keep_alive=0. Wcześniejsze zakończenie czeka
na naturalne wygaśnięcie. Każdy krok kontroluje rezydujący model, Docker,
ComfyUI na 8188/8189 oraz pamięć GPU. Nie ma automatycznego stop/unload.
Inne wywołania i globalna konfiguracja pozostają w dotychczasowym trybie.

Dane `retained-batch.json` zachowują kolejność, retencję, kontrolę zasobów
i pomiary serwera; weryfikator porównuje je z odpowiedziami. Seria liczy
nieudane wywołania do limitu; nie uruchamia dodatkowych prób.

Jedna para rzeczywistych poprawek Harbor: warm 13,478 s vs cold 23,499 s,
42,64% krócej, końcowy plan i grafiki identyczne oraz niezależnie odebrane.
Ładowanie 2,7671 vs 13,0065 s. To obserwacja znanego zadania z warm jako
pierwszym ramieniem, nie uniwersalna gwarancja szybkości ani egzamin usługi.
Retencja nie zapewnia wyłączności GPU wobec zewnętrznych klientów; obcy
lub nieznany stan wykryty przed następnym krokiem zatrzymuje generację.

## Naprawa zachowanego projektu i zanikających szczegółów

`--repair-artwork KATALOG` tworzy osobny przebieg z oryginalnej paczki albo
ze źródła zatrzymanego po wyczerpaniu poprawek wizytówki. Uwierzytelnia
odpowiedzi i kopiuje etapy ponownie używane; może zmienić tylko wybrane logo
oraz kartę. Poprawny plan, drugi koncept i wybór autora zostają zachowane.
Raport jawnie liczy do sześciu dodatkowych wywołań, nie zmienia starego
budżetu/oceny i ma fresh_exam=false. Zagnieżdżone naprawy nie są źródłem.

Kolizje są zwracane wraz z rzeczywistymi ramkami tekstów, kształtów i grup.
Wybrany znak renderowany jest w kolorze i monochromie. Diagnostyczne ukrycie
każdego kształtu mierzy jego wpływ na obraz; zanik składnika blokuje wynik.
Wszystkie węzły są przywracane przed eksportem. Progi: kanał >=20, co najmniej
16 zmienionych pikseli w kolorze i mniej niż max(2, 5%) po konwersji.
Kontrola dotyczy białego podkładu i nie zastępuje wizualnego odbioru ani testu druku.
Weryfikator odtwarza również liczbę pikseli z zachowanych obrazów diagnostycznych.

`--artwork-reasoning` wybiera ograniczony istniejący profil rozumowania;
nie trenuje modelu. V2 nie narzuca przykładów baz tekstowych w naprawie,
a identyczny odrzucony JSON używa już zapisanych pomiarów. Copper poprawiony
w dwóch wywołaniach (69,369 s); Cedar w jednym (52,945 s). Próby bez
rozumowania zachowane jako failed. Warunki różniły się, więc nie wyciągamy
wniosku o przewadze modelu na kontrolowanym nowym egzaminie.

`--revise-alignment-text KATALOG --warm-revision` to jawne v5 kontroli opisów.
Dziedziczy v3 i dodaje konserwatywną kontrolę centered/centred przy odległych
środkach poziomych; nie jest ogólnym parserem znaczenia i nie dowodzi estetyki.
Cedar wymagał tej poprawki po odrzuconym „centered layout”. Końcowy opis
ma zgodne z rendererem x=160/300; cały poprawiony syntetyczny pakiet odebrano.
Stare wyniki, w tym pełny egzamin 0/3 w obu ramionach, pozostają niezmienione.

## Pełny egzamin dostawy v2

`--delivery-exam` zamraża trzy nowe briefy i kod. Wspólne źródło każdej pary
ma zwykły budżet generowania; obie naprawy grafik mają równy kontekst,
limit odpowiedzi, czas i do sześciu wywołań. Potem obie używają kontroli
opisów v5 w trybie warm. To porównanie napraw na wspólnych źródłach, nie
sześć niezależnych generacji i nie automatyczne potwierdzenie gotowości.

Pierwszy delivery-exam-4ps4ytf9: 211,241 s, technicznie 3/3 w obu ramionach,
niezależnie 2/3 w obu. Orchard Counter i North Pier odebrane, Saffron
odrzucony za dekorację wchodzącą w tekst oraz ciemny tusz zalecany na ciemnym
tle. Żaden etap naprawy grafik nie wywołał modelu: ten przebieg nie pozwala
ocenić przewagi profilu rozumowania. Podczas generowania Saffron lokalny
model sam poprawił kolizję drugiego logo; to zachowany dowód konkretnej korekty.

Weryfikacja: `python -m scripts.brand_delivery_exam --verify KATALOG`.
Dodanie `--use-recorded-render` wykonuje audyt bez nowej przeglądarki:
używa wcześniej zapisanych rzeczywistych dowodów renderowania, po sprawdzeniu
powiązania z raportem, hashy, źródeł SVG, geometrii i identyczności pikseli.
Raport wyraźnie oznacza ten tryb. Brak wcześniejszego dowodu zatrzymuje audyt.
Domyślnie wykonywane są nowe rendery. Ten sam przełącznik jest dostępny przy
`scripts/brand_guide_revision.py --verify KATALOG`.
