# Wieloplikowe źródła i nowe wersje

Stan: 19.09.2026. Dostępne przechowywanie, podgląd i edycja źródeł w wielu
katalogach. Sama edycja nie wykonuje źródeł. Oprócz płaskiego Python stdlib
dostępne są osobno testy profilu wielomodułowego o ustalonej strukturze.
Nie instalujemy zależności i nie wykonujemy kodu edytora na hoście.

Po zapisaniu paczki z katalogami można uruchomić [kontrolę struktury i składni
profilu wielomodułowego](MULTIFILE_RUNNER.md). To analiza plików, nie wykonanie
aplikacji. Pilot izolacji zakończono 19.09; nowy profil ma już testy, raporty
i eksport kandydata oraz bezstanowy podgląd. Nowa wielomodułowa paczka po
własnych testach może zostać odebrana i wydana; nie dziedziczy odbioru bazy.
Automatyczna naprawa tego profilu nie jest jeszcze wdrożona.

## Obsługa właściciela

1. W Centrum realizacji otwórz link przy paczce prowadzący do **Budowy i testów**.
   Wczytaj tę wersję przyciskiem formularza wyboru paczki.
2. Sekcja **Pliki paczki — podgląd i zmiany** zawiera listę ścieżek z katalogami.
   Wybierz plik i użyj **Otwórz plik**. Kod wyświetla się jako tekst, bez HTML,
   skryptów, importów Pythona czy dostępu do ścieżek systemu plików.
3. Zmień treść i użyj **Dodaj zmianę do szkicu**. Możesz zmienić kilka plików
   i dodać nowe, np. `src/module.py` lub `assets/main.css`, podając ich ścieżki.
   **Usuń ze szkicu** nie usuwa pliku z paczki — wycofuje tylko proponowaną zmianę.
4. Podaj opis i wybierz **Zapisz nową wersję źródeł**. Otrzymasz nowy numer
   paczki, link do niej oraz przycisk pobrania ZIP. Kontynuuj edycję w nowej
   wersji; ukończony szkic pozostaje zamrożony, by nie tworzyć przypadkiem
   następnych odgałęzień od starej bazy.
5. Nowa wersja wymaga własnych testów i odbioru. Historyczny raport dotyczy
   historycznej paczki; stary zaakceptowany wynik nie zatwierdza nowego kodu.

Szkic istnieje tylko w pamięci karty. Zmiana paczki, wylogowanie lub zamknięcie
strony go usuwa. Przy niepewnym zapisie ponów **tę samą treść** — identyfikator
żądania zapewni powrót do tej samej wersji. Przed edycją innej treści rozstrzygnij
poprzedni zapis lub sprawdź listę paczek. Nie jest to edycja współdzielona na żywo.

## Ochrona danych i ograniczenia

- Oryginalna paczka nigdy nie jest nadpisywana. Niezmienione pliki kopiowane są
  bajtowo jako UTF-8 do nowej wersji. Potwierdzenie wiąże bazę, nową wersję,
  sumy kontrolne oraz listę zmian. Nie kopiuje odbioru ani wyników testów.
- Chronione są istniejące pliki rozpoznane po typowych nazwach testów:
  katalogi `test`, `tests`, `__tests__`, `test_…`, `conftest.…`, `test.py`,
  `tests.py`, `…_test.py`, `….test.…`, `….spec.…` (bez rozróżniania wielkości liter).
  Można dodawać nowe pliki testów. To ochrona konwencji nazw, nie analiza
  semantyczna wszystkich testów i nie gwarancja jakości testowania.
- Wspólne limity paczki: 100 plików, 256 KiB na plik, 1 MiB łącznie,
  wyłącznie tekst UTF-8. Brak ścieżek absolutnych, ukrytych segmentów,
  przejścia `..`, kolizji wielkości liter oraz plik/katalog.
- Pole `execution_profile` metadanych wskazuje zgodny układ albo `null`.
  To nie pomiar zasobów ani wynik testu. Przy `null` panel ukrywa uruchomienie
  obecnego runnera, ale zachowuje podgląd, edycję i eksport źródeł.
- Obsługa szerszego runnera, zależności i importu repozytoriów pozostaje
  kolejną pracą. Profil wielomodułowy przeszedł rzeczywiste testy izolacji,
  API i podglądu Chrome po potwierdzeniu końca wynajmu Vast.ai.

## API

Tylko właściciel, istniejące uwierzytelnienie. Odczyty mają `no-store`.

- `GET /api/tasks/{task_id}/workspace-packages/{id}/source?path=src/module.py`
  zwraca treść jednego pliku, sumy kontrolne i informację o ochronie testu.
  Odczytuje wyłącznie manifest paczki, nie dysk hosta.
- `POST /api/tasks/{task_id}/workspace-packages/{id}/edits` przyjmuje UUID
  `request_id`, `base_checksum`, `purpose`, mapę `changes` i listę `removals`.
  Interfejs udostępnia dodawanie i zmianę; API może też usuwać niechronione pliki.
  Pusta zmiana, nieistniejące usunięcie, kolizje i zmiana chronionego testu
  są odrzucane. Limit ciała JSON wynosi 8 MiB przed dekodowaniem.
- Powtórne identyczne żądanie zwraca tę samą paczkę i potwierdzenie. Ten sam
  UUID z innym zakresem daje konflikt. Zapis źródeł, potwierdzenia i audytu
  jest atomowy. Nie uruchamia modelu, testów, runnera, wdrożenia ani publikacji.

Testy: `tests/test_package_edits.py`, `tests/test_package_editor.cjs`,
`tests/test_build_package_editor.cjs`; bez rzeczywistego kodu klienta i GPU.
