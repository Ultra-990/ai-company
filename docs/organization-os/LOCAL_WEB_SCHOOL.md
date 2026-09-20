# Szkoła lokalnego wykonawcy stron

Decyzja właściciela z 20.09.2026: do ukończenia projektu to modele wykonują
strony i inne produkty. Asystent rozwija system, uczy i ocenia. Nie naprawia
za model źródeł produktu. Poprzednie trzy demonstracje były w większości
dziełem asystenta i nie stanowią egzaminu samodzielności lokalnych modeli.

## Działający zakres

`scripts/web_school/run.py` jest osobnym, ograniczonym wykonawcą ćwiczeń.
Nie używa szablonów stron z `web_trials/templates`. Całe HTML, CSS, JS,
ilustracje CSS/SVG i obsługę interakcji pisze przypięty lokalny Qwen.
Nauczyciel dostarcza brief, syntetyczne dane i kontrakt selektorów testowych.
Pierwsza rodzina to sklep ze znaczkami: filtry, sortowanie, galeria, koszyk,
demonstracyjne podsumowanie, rozwijane menu i responsywność.

```bash
.venv/bin/python scripts/web_school/run.py
.venv/bin/python scripts/web_school/run.py --run --max-attempts 3 --practice-next
```

Bez `--run` wypisuje tylko zadanie. Z flagą: kontrola zasobów przed każdym
wywołaniem, trzy osobne odpowiedzi plikowe na próbę, najwyżej trzy próby.
Ollama: przypięty digest, kontekst 16384, limit 6000 tokenów na plik,
deadline 180 sekund, cztery wątki, keep_alive=0. Brak zmiany konfiguracji
produkcyjnej modelu. Błąd zasobów/transportu zatrzymuje własny eksperyment.
Pierwsze 4096 okazało się za małe przy pełnym pliku naprawy; odrzucamy
ucięte odpowiedzi. Prompt prosi o zwięzłe pliki, a kontekst JS nie zawiera
niepotrzebnego arkusza CSS. To zmiana parametrów nauczania, nie źródeł strony.

Każda próba ma dokładne prompty, surowe odpowiedzi, pliki, hashe, raport
niezależnych testów i zrzuty ekranu. Wyniki są w prywatnym katalogu Linux
`/home/marcin/ai-company-workspaces/web-school/`. Nic nie nadpisuje starych
demonstracji. Pliki produktu są dokładnymi treściami odpowiedzi modelu.
Raport nieudanych kontroli trafia do modelu; kolejne pliki ponownie pisze
model. Brak ręcznego fallbacku do implementacji asystenta.

Przed naprawą osobne wywołanie lokalnego Qwena diagnozuje przyczyny błędów
(limit 1000 tokenów). Wykonawca dostaje tę diagnozę wraz z niezależnymi
obserwacjami; nie jest ona odbiorem jakości. Błąd walidacji plików nie usuwa
wcześniejszych niezaliczonych kontroli funkcji — pozostają w kontekście
aż do ponownego egzaminu. Pozwala to uniknąć naprawiania jednego błędu
kosztem zapomnianego wymagania.

## Egzamin i jego ograniczenia

Egzaminator jest kodem nauczyciela, nie kodem testów zaproponowanym przez
ucznia. Osobny Chrome headless, bez GPU, dźwięku i sesji graficznej. Źródła
są statycznymi danymi serwera, nie są importowane/wykonywane na hoście.
Dokument ma CSP sandbox, brak connect-src, zasoby z zamkniętej listy.
Przechwytywanie żądań Chrome odrzuca adresy poza trzema plikami ćwiczenia.
Nie otwieramy prawdziwego panelu firmy ani sesji przeglądarki właściciela.

Kontrole dotyczą zgodności katalogu, filtrów i ich przecięcia, wyszukiwania,
sortowania, kolejności galerii, unikalności koszyka, sum i usuwania,
unieważniania podsumowania, menu, szerokości 320/390/768 i reduced motion.
To ograniczony egzamin rozwojowy: akcje DOM nie zastępują pełnej kontroli
klawiatury/dotyku, dostępności, estetyki, wydajności czy bezpieczeństwa.
`functional_pass` nie oznacza odbioru wizualnego, publikacji ani wykonania
prawdziwego zadania w bazie. Odpowiednie flagi pozostają false.

## Pamięć doświadczeń a trening wag

Po przejściu z błędów do kompletu zaliczonych kontroli system wyprowadza
krótkie lekcje z nazw niezależnych testów. Treść pochodzi z zamkniętej mapy
reguł nauczyciela, nie z deklaracji modelu „nauczyłem się”. `--learn-from`
wczytuje je z wcześniejszego przebiegu dopiero po sprawdzeniu źródeł,
raportów i wersji egzaminatora. Edycja źródeł po teście unieważnia dowody.

`--practice-next` po zaliczeniu uruchamia automatycznie jeszcze jedno
ćwiczenie tej samej rodziny ze zmienionymi cenami i kategoriami. Korzysta
z zapisanych lekcji bez interwencji asystenta. Ten drugi przypadek jest
ćwiczeniem, **nie niezależnym holdoutem ani dowodem uogólnienia**. Brak
wcześniejszych błędów oznacza brak nowej lekcji; nie produkujemy fikcyjnego
postępu. Pamięć i samonaprawa nie aktualizują wag.

Pamięć obejmuje też błędy struktury plików sprzed uruchomienia przeglądarki.
Przed wyprowadzeniem takiej lekcji loader ponownie sprawdza dokładne
wcześniejsze odpowiedzi walidatorem i potwierdza poprawność końcowej wersji.
Nie przepisuje historycznych raportów po zmianie mechanizmu pamięci.

`scripts/web_school/collect.py RUN_DIRECTORY` odkłada dokładne odpowiedzi
zaliczonej próby jako kandydatów `company-sft.v1` ze statusem `pending`.
Sprawdza autorstwo, digest i niezmienność źródeł. Nie zmienia odpowiedzi ani
nie ucina za długich rekordów. Każdy wariant tej rodziny ma split train.
Sam zielony test nie zatwierdza danych: potrzebny przegląd kodu, obrazu,
prywatności, praw i tokenizacji. Ponowny zapis kolekcji jest odrzucany.
Główny cykl wywołuje tę kolekcję automatycznie po zaliczeniu ćwiczenia.

Docelowy dalszy cykl: nowe rodziny train/validation/test → sprawdzone dane →
osobny adapter → porównanie z bazą na nieużywanych zadaniach → wdrożenie
tylko po poprawie, z zachowaniem bazy. Ten moduł jeszcze nie uruchamia
samoczynnego treningu wag, harmonogramu ani promocji modelu. Nie omija
istniejących bramek danych z QWEN_TRAINING.md i WEB_MODEL_SPECIALIZATION.md.
Nie jest też jeszcze podłączony do panelu `/os/build` i kolejki produkcyjnej.

## Wyniki rzeczywistych prób

Raporty nieudane i zmiany egzaminatora opisujemy w WORK_LOG.md. Liczby
przypadków zaliczonych nie mogą być przedstawiane jako ocena całego modelu.

20.09.2026: pierwszy wariant zaliczony po poprawce (30/30). Drugi wymagał
kilku ograniczonych przebiegów; po diagnozie przez model końcowa poprawka
także 30/30. Obie realizacje są w całości odpowiedziami Qwena. Sześć nowych
kandydatów SFT pozostaje pending; tokenizacja 6/6 przy 16384, bez ucinania.
Testy mechanizmu i formatu danych 47/47. Nadal brak nowego adaptera i holdoutu.

`scripts/web_school/recheck.py RUN_DIRECTORY` ocenia ponownie dokładne
odpowiedzi po zmianie egzaminatora. Tworzy osobny katalog z pochodzeniem,
bez inferencji i bez nadpisywania źródeł/raportów. Nie dolicza ich jako nowych
niezależnych przykładów. `run.py --run --revise-from RECHECK_DIRECTORY`
kontynuuje niezaliczoną realizację: sprawdza zgodność odpowiedzi i dowodów,
przekazuje istniejące źródła oraz obserwacje do naprawy przez model.
Limit prób obowiązuje osobno w każdym jawnym uruchomieniu.
