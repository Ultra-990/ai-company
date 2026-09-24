# Automatyczne przygotowanie danych do nauki

Stan 21.09.2026: działa pierwszy etap — zbieranie niezależnie ocenionych
rozmów obraz–tekst i audyt CPU. **Automatyczne treningi wag nie są jeszcze
podłączone.** Wcześniejsze małe pilotaże nie wykazały poprawy; harmonogram
nie powtarza ich jako pozornej nauki i nie wdraża adapterów.

`scripts/learning_autopilot.py --once` przegląda wyłącznie prywatne,
syntetyczne ćwiczenia wnętrz i wektorów. W każdym cyklu ponownie sprawdza
oryginalną odpowiedź modelu, obrazy i niezależną ocenę. Odrzucone przykłady
oraz rodziny development/validation/test nie trafiają do treningu.
Zmiana lub wycofanie oceny usuwa przykład z bieżącej liczby gotowych danych.
Blokada plikowa zapobiega jednoczesnym cyklom; do dwóch nowych audytów CPU
w cyklu ogranicza obciążenie. Poprawne, niezmienione audyty są używane ponownie.

Rozszerzenie: [kontrolowane usterki SVG](VECTOR_CONTROLLED_PRACTICE.md)
pozwalają odbierać lokalne naprawy przez dokładne odtworzenie wcześniej
niezależnie zaakceptowanego źródła. Każda naprawa zachowuje jawne pochodzenie
syntetycznej usterki. Harmonogram zbiera te rozmowy w grupy do 16 przykładów
na audyt CPU, nadal sprawdzając osobno każdą odpowiedź, źródło i ocenę.

`vector_learning_records.py` eksportuje dokładną ocenioną odpowiedź narzędzia
lokalnego modelu i rzeczywisty PNG wzorca. Wspólny audyt sprawdza hash,
oryginalną rozmowę, maskowanie instrukcji i obecność pikseli. Kopie obrazów
muszą pozostawać w paczce; symlinki i wyjścia poza katalog są odrzucane.
Nowy eksport nie zmienia historycznego doświadczenia ani raportu wykonania.

Od 22.09.2026 harmonogram zbiera też [wizyjne poprawki produktu](PRODUCT_VISUAL_REVISIONS.md).
Przyjęte są dwie niezależnie ocenione rozmowy: strukturalna naprawa zakrętki
i przeprojektowanie układu infografiki. Odrzucona próba pozostaje pominięta.
Dokładne odpowiedzi, wejściowe PNG i maskowanie sprawdzono na CPU; stan to
84 train, pięć rodzin i sześć różnych obrazów. Kolejny cykl nie zduplikował
rekordów. Odczyt systemd potwierdził późniejsze automatyczne wykonanie bez błędów.
Przyjęcie dotyczy wskazanych poprawek, nie jakości całego produktu lub usługi.

Rzeczywista próba wektorowa: 2166 tokenów, 2132 zamaskowane, 34 nadzorowane,
468 tokenów obrazu, tensor pikseli 1872×1536. Usunięcie obrazu jest odrzucane.
Nie ładowano wag i nie inicjalizowano CUDA. Pierwsza próba ujawniła import
zależności aplikacji w izolowanym środowisku ML; usunięto to powiązanie,
zachowując oddzielne środowiska. Ponowny audyt przeszedł.

Pierwszy rzeczywisty cykl przyjął dwa przykłady z dwóch rodzin, odrzucił
trzy źródła bez zaakceptowanych rekordów train. Następny cykl użył obu
istniejących audytów bez powtórzenia pracy procesora multimodalnego.
To liczby nowego zbioru multimodalnego, nie suma wszystkich historycznych
zbiorów tekstowych i zestawów egzaminacyjnych.

Próg 200 train / 25 validation / 50 test pozostaje niezmieniony. Potrzebne
są szersze dane i rejestr oddzielnych sprawdzianów.
[Trener zbioru](VISION_CORPUS_TRAINING.md) wykonał już ręcznie uruchomioną
próbę z porównaniem bazy i adaptera; nie wykazała poprawy. Harmonogram
nie uruchamia tego trenera. Osobna ocena musi poprzedzać wdrożenie.

## Wymaganie docelowe: nauka bez asystenta

Właściciel ponownie potwierdził 22.09.2026, że system ma rozwijać modele
bez dalszej kontroli asystenta prowadzącego. To wymaganie odbioru projektu,
nie opis obecnej funkcjonalności. Ręczna ocena każdego nowego przykładu
lub zgoda asystenta na każdy trening nie mogą być docelową zależnością.

Pełny cykl ma sam zbierać doświadczenia z pracy lokalnych modeli, odrzucać
niepotwierdzone wyniki, budować wersjonowane zbiory, planować ograniczony
trening przy dostępnych zasobach i porównywać kandydata z używaną wersją.
Odbiór danych i wag musi opierać się na dowodach niezależnych od deklaracji
uczącego się modelu. W zadaniach wizualnych same poprawne pliki i geometria
nie wystarczą do automatycznej oceny jakości projektu.

Warunki dopuszczenia pełnej automatyzacji:

- Oddzielne rodziny treningowe, walidacyjne i testowe; ukryte odpowiedzi
  testowe nie wracają do danych ani pętli poprawek. Testy trzeba odnawiać,
  aby kolejne próby nie dopasowywały się stale do jednego egzaminu.
- Wdrożenie tylko po wykazanej poprawie i braku istotnej regresji według
  wcześniej ustalonych kryteriów; odrzucenie słabszej lub równorzędnej wersji.
- Zachowanie poprzednich wag, kontrola po wdrożeniu i przetestowany powrót
  do poprzedniej wersji. Brak zasobów lub przerwanie procesu nie uszkadza
  działającego modelu ani nie uruchamia równoległych treningów.
- Powtarzalny zapis pochodzenia danych, zmian wag, kosztu, wyników i decyzji;
  limity czasu, miejsca na dysku i liczby prób bez nowych wartościowych danych.

Odbiór autonomii wymaga rzeczywistej próby kilku kolejnych cykli bez udziału
asystenta, obejmującej odrzucenie kandydata, wznowienie po przerwaniu oraz
wdrożenie lepszej wersji i kontrolowany rollback. Symulowane testy samego
harmonogramu nie dowodzą samodzielnej nauki. Osiągnięcie tej automatyzacji
nie jest automatycznie dowodem jakości porównywalnej z asystentem we
wszystkich pięciu usługach — to osobny sprawdzian.

## Stan i uruchamianie

Prywatny stan: `ai-company-workspaces/learning-autopilot/state.json`.
Właściciel może odczytać ograniczone podsumowanie przez
`GET /api/learning/status`; odpowiedź nie zawiera ścieżek, promptów ani wyników.
Pole `fresh` oznacza aktualność raportu do 15 minut, nie dowód życia procesu.
Sam odczyt niczego nie uruchamia. Endpoint będzie dostępny po załadowaniu
nowej wersji aplikacji.

Szablony harmonogramu użytkownika są w `config/systemd/`: cykl co pięć minut,
CPU do dwóch rdzeni, pamięć do 4 GiB, limit czasu sześć minut, bez dostępu
do GPU, sieci IP i pulpitu. Timer zainstalowano i włączono 21.09.2026.
Odczyt systemd potwierdził wykonanie o 04:58:27 CEST, kod zakończenia 0
oraz aktywny timer oczekujący na następny cykl. Usługa typu oneshot pomiędzy
cyklami jest nieaktywna; nie oznacza to zatrzymania harmonogramu.
Jest to usługa użytkownika, działająca wraz z jego menedżerem systemd;
nie włączano linger ani dodatkowej usługi systemowej.

## Bramka przyszłego treningu

`scripts/learning_training_gate.py` wykonuje deterministyczną decyzję na
podstawie migawki intake. Nie ładuje wag, nie uruchamia procesu i nie promuje
adaptera. Przyszłe wywołanie trenera będzie możliwe dopiero po jednoczesnym
spełnieniu minimów 200 train / 25 validation / 50 test, braku błędów intake,
niezależnym odbiorze danych, porównaniu base/adapter, zapisanym planie
rollbacku i zarejestrowanej integracji konkretnego trenera z polityką zasobów.
Brak któregokolwiek dowodu oznacza `continue_reviewed_intake`.

Po cyklu 24.09.2026 bramka zwróciła `eligible: false`: 130/25/50 rekordów,
validation i test są zarejestrowane jako dwa oddzielne, zamrożone egzaminy;
brakuje jeszcze 70 train oraz niezależnego porównania kandydata i planu rollbacku.
To nadal nie uruchamia treningu wag.
Integracja trenera jest już zarejestrowana, ale pozostałe warunki nadal celowo
blokują automatyczny trening. Sama bramka jest infrastrukturą przyszłej autonomii, nie dowodem,
że autonomiczne aktualizacje wag już działają.

Runner `scripts/learning_trainer_runner.py` jest zarejestrowanym,
odizolowanym przekazaniem do `train_vision_corpus.py`. Najpierw odczytuje tę
samą bramkę, zapisuje hashe stanu i egzaminu, a dopiero po pełnej kwalifikacji
może uruchomić trenera w prywatnym katalogu. Runner nie ma ścieżki promocji
adaptera ani zmiany routingu; wynik słabszy lub równy pozostaje kandydatem do
odrzucenia. Test planowania potwierdza odmowę na bieżącym stanie 130/25/50.
