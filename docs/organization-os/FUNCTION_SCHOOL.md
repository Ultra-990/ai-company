# Szkoła funkcji lokalnego modelu

`scripts/function_school/run.py` uruchamia trzy krótkie ćwiczenia: koszyk
ze stanem magazynowym, rezerwacje z kolejką FIFO i portfel wirtualnych punktów.
Kontrakty oraz 23 niezależne testy powstały przed inferencją. Cały kod
`solution.py` pisze lokalny Qwen; asystent nie dostarcza implementacji.

```bash
.venv/bin/python scripts/function_school/run.py
.venv/bin/python scripts/function_school/run.py --run --max-attempts 2
```

Bez `--run` nie ma inferencji ani kontenerów. Domyślnie do dwóch prób na
ćwiczenie, trzy ćwiczenia kolejno. Budżet 1200 sekund sprawdzany przed nową
próbą; rozpoczęte wywołanie ma własny timeout (model 180 s, runner 45 s).
Blokada procesu nie pozwala uruchomić drugiego kursu równolegle. Kontrola
Ollama/ComfyUI/Docker/GPU przed generacją i sprawdzianem; problem infrastruktury
zatrzymuje kurs, nie obniża wyniku modelu i nie uruchamia automatycznej naprawy.

Kod modelu uruchamia się wyłącznie w istniejącym `python-web-v1`: przypięty
obraz, brak sieci/GPU, readonly źródła/root, ograniczenia czasu i zasobów.
Host nie importuje ani nie wykonuje rozwiązania. Stały serwer health jest
elementem uprzęży testowej, a nie implementacją ćwiczenia. Testy mają także
niezmienność wejścia, ponowione żądania, błędne typy i zachowanie sum.

Raport, dokładne prompty, odpowiedzi, źródła i wykonania pozostają lokalnie
w `ai-company-workspaces/function-school/course-*`. Nieudany sprawdzian
wraca do modelu wraz z jego poprzednim kodem. Udana naprawa może wyprowadzić
lekcję z zamkniętej mapy nazw testów. Zaliczenie od razu nie tworzy fikcyjnej
lekcji. To zapis doświadczenia, bez aktualizacji wag i bez harmonogramu.

Po zaliczeniu powstaje dokładny kandydat `company-sft.v1`, zawsze `pending`
i `train`. Kolektor ponownie sprawdza hashe promptu/odpowiedzi/źródeł/testów/
wykonania, pochodzenie modelu, izolację i liczbę testów. Nie zatwierdza
prywatności ani jakości. Dotychczasowe bramki danych nadal obowiązują.
Trzy rodziny rozwojowe nie mogą później udawać niezależnego holdoutu.
Testy funkcjonalne nie są audytem złośliwego kodu ani odbiorem całej aplikacji.

20.09.2026: `course-ksxznylh` — 3/3 pierwsze próby, 23/23 metody testowe,
18.257 s całego przebiegu, wszystkie kontenery posprzątane. Przegląd oryginalnych
źródeł nie wykazał dopasowania do testów ani dodatkowych efektów ubocznych.
Trzy kandydaty pozostały pending; offline tokenizacja 3/3 (885, 706, 646 tokenów),
bez ucinania. Nie jest to dowód poprawy modelu: każde zadanie zdał już za
pierwszym razem. Testy mechanizmu i danych: 44 passed, bez pominięć.
