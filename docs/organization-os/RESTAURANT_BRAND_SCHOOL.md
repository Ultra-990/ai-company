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
