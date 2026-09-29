# Lokalna szkoła identyfikacji restauracji

`scripts/brand_school.py` wykonuje syntetyczne ćwiczenie odpowiadające
zakresowi ogłoszenia o identyfikacji restauracji. Lokalny model przygotowuje
plan stylu, dwa koncepty logo, uzasadnia wybór i projektuje wizytówkę.
Asystent rozwija wymagania, narzędzia i niezależną ocenę; nie rysuje logo
ani nie poprawia współrzędnych za model.

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
