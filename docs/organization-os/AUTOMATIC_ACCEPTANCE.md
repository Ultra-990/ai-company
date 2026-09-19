# Automatyczne przykłady odbioru HTTP

## Stan wdrożenia — 2026-09-14

Zaimplementowano zapisywanie planu, integrację z cyklem automatycznych poprawek
i formularz w `/os/build`. Sprawdzono na izolowanych bazach i atrapach modelu
oraz runnera. **Wykonywanie nowych przypadków jest wyłączone** przez
`config/acceptance_execution.json` (`enabled: false`). Przygotowanie planu
działa bez modelu, GPU, kontenera i zmiany statusu zlecenia.

Nie wykonano rzeczywistego pilota tych nowych kontroli podczas wynajmu Vast.ai.
Po potwierdzeniu końca wynajmu potrzebny jest pilot z prawdziwym runnerem,
kontrola sprzątania i ograniczeń oraz ocena naprawy Qwena. Nie włączamy flagi
automatycznie. Zgoda na małe zadania modelowe nie oznacza zgody na zakłócenie
wynajmu GPU/CPU. Przełącznik dotyczy nowej ścieżki przypadków, nie wyłącza
wszystkich wcześniejszych funkcji systemu.

## Obsługa bez uruchamiania

1. W Budowie i testach wybierz zadanie/paczkę i kliknij „Sprawdź wersję”.
2. Wybierz „Przygotuj automatyczne sprawdzanie wymagań”.
3. Wskaż wymaganie z briefu, nazwij przykład, wpisz ścieżkę GET i oczekiwany
   status HTTP. Opcjonalnie wskaż pole JSON i oczekiwaną wartość.
4. „Dodaj przykład do szkicu”; maksymalnie cztery przykłady na plan.
5. „Zapisz niezmienny plan — bez uruchamiania”. Plan jest wersjonowanym
   artefaktem, nie raportem testów. Zmienione oczekiwania to nowy plan.
   Sam zapis szkicu nie czyni go warunkiem wydania. Wybranie planu przy
   tworzeniu cyklu kontroli już tak — szczegóły poniżej.

Przykład dla aplikacji, która rzeczywiście udostępnia ten kontrakt:

```text
GET /api/estimate?hours=8&rate=322
HTTP 200
Pole JSON: total
Oczekiwana wartość: 2576
```

Nie wpisuj przykładu kalkulatora do niepowiązanego projektu. Wartość wpisuje
się jako JSON: `2576` to liczba, `"2576"` to tekst, `true` to bool, `null`
to brak wartości. Brak klucza JSON nie jest tym samym co jawne `null`.
Puste pole JSON oznacza wyłącznie sprawdzenie statusu HTTP.

Po niepewnym zapisie ponów tę samą operację. Formularz zachowuje dokładne
żądanie z UUID. Przed zmianą szkicu odśwież listę planów i sprawdź, czy
poprzedni zapis już istnieje. Odświeżenie usuwa niezapisany szkic.

## Wykonanie po odblokowaniu i pilocie

Przycisk „Testuj i napraw z tym planem” pojawia się dopiero przy włączonej
konfiguracji. Wymaga najnowszej paczki Qwen, której próba oczekuje na odbiór.
Zapisany plan można wcześniej przygotować również dla innej paczki tego
samego zadania i niezmienionego zakresu.

1. Dotychczasowy profil testów i izolacji musi się powieść.
2. Każdy przykład jest wykonywany przez istniejący izolowany podgląd HTTP.
3. Niepoprawny status, wartość, brak pola lub niepoprawny JSON dają rozbieżność
   aplikacji. Skrót oczekiwanego/rzeczywistego wyniku trafia do poprawki Qwen.
4. Nowa wersja zachowuje bazowe testy i osobny plan oczekiwań. Ponownie
   wykonywane są testy bazowe oraz te same przykłady HTTP.
5. Maksymalnie dwie poprawki, trzy zestawy, cztery przykłady na zestaw;
   dotychczasowy deadline 15 minut pozostaje bez zmian.

Awaria runnera, niepewne sprzątanie, zmiana konfiguracji/zakresu lub uszkodzone
dowody nie są traktowane jako powód do zmiany kodu. Powstaje czytelny stan
diagnozy. Zatrzymanie działa po bieżącej operacji, nie zabija cudzych procesów.
Pojedyncze wykonania mają trwałe UUID i raporty; po przerwie wznowienie nie
powtarza zakończonego przypadku. Zapisane wyniki są ponownie sprawdzane względem
sum raportów i dokładnej wersji przed użyciem w niezakończonym cyklu.

Historia cyklu rozróżnia „Test w izolacji”, „Przykłady wymagań HTTP” i „Naprawa
Qwen”. Przykłady pokazują oczekiwany/rzeczywisty wynik, ID wykonania i raportu.
Jeżeli cykl przerwano w połowie listy, pojedyncze raporty pozostają w historii
wykonań; nie powstaje fikcyjny wynik całego zestawu.

## Granice bezpieczeństwa i zakresu

- Nie ma dowolnego kodu testów, poleceń terminala, nagłówków, cookies ani
  zewnętrznych adresów. Tylko istniejąca allowlista lokalnych ścieżek podglądu.
- Każdy GET działa w osobnym czystym środowisku. Nie wspiera sesji, przepływów
  logowania, zapisów POST, bazy między krokami ani testów wizualnych UI.
- Oczekiwane HTTP: 200–499. Opcjonalna ścieżka kluczy JSON do czterech poziomów,
  bez indeksów tablic. Tylko wartości skalarne, ograniczony rozmiar odpowiedzi,
  brak akceptacji NaN, nieskończoności i zduplikowanych kluczy.
- Plan ma SHA-256, źródłową paczkę i checksumę całego briefu. Jest niezależny od
  wygenerowanych źródeł; model nie może go przepisać, żeby „zaliczyć test”.
- To dowód konkretnych przykładów, **nie pełnego pokrycia wymagania**. Wymaganie
  może obejmować więcej zachowań niż wskazany przypadek. Wyniki nie nadpisują
  ręcznych ocen, procentu projektu, odbioru właściciela ani klienta.
- Po wybraniu planu do cyklu jego kompletne zaliczenie dla dokładnej wersji
  jest warunkiem odbioru i wydania. Nie zastępuje testów bazowych i odbioru.
  Zadania bez wybranego planu zachowują poprzedni proces.
- Kod klienta nigdy nie jest wykonywany na hoście. Dotychczasowe ograniczenia
  runnera pozostają; nie jest to sandbox dla celowo wrogiego kodu.
- Nic nie jest wysyłane do Upwork. Właściciel prowadzi kontakt i przekazanie.

## API i testy

Owner-only GET/POST
`/api/tasks/{task_id}/workspace-packages/{package_id}/acceptance-plans`.
POST: UUID `request_id`, `source_checksum`, `scope_checksum`, lista `cases`.
GET: ostatnie 20 planów zadania; niezgodne z bieżącym zakresem oznaczone
`invalid`. Odczyt nie zapisuje ani nie wykonuje. Bez nowej tabeli/migracji.

Opcjonalnie przy tworzeniu `/api/application-quality`:
`acceptance_plan_id` + `acceptance_plan_checksum` (wymagane razem).
Cykl bez planu zachowuje dotychczasową ścieżkę. Uruchomienie cyklu z planem
przy wyłączonej fladze daje 409 przed wykonaniem modelu lub kontenera.

## Warunek odbioru i wydania — rozszerzenie 2026-09-14

Ostatni **jawnie wybrany do cyklu** plan zadania jest obowiązujący. Utworzenie
innego szkicu go nie zastępuje. Cykl bez planu nie może usunąć tego wymagania:
próba utworzenia takiego cyklu daje konflikt z instrukcją wyboru planu.
Nowy cykl ze świadomie wybranym planem go zastępuje i wymaga własnego wyniku.
Zatrzymanie cyklu nie znosi warunku; po poprawkach trzeba ukończyć kontrolę.
Plan wybrany przez API nawet przy wyłączonym wykonaniu jest już wiążący —
nie wybieraj go dla realnego zadania, którego kontrola musi czekać na wynajem.

Przy akceptacji właściciela sprawdzane są źródła odbieranej próby, powiązanie
z wynikiem modelu, zakończony cykl, aktualny brief, profile i każdy raport HTTP.
To **odczyt istniejących dowodów**, bez nowych procesów, inferencji i zapisów
kontroli. Odmowa nie zmienia statusu/procentu i nie zapisuje fikcyjnego odbioru.
Odrzucenie wyniku do poprawy pozostaje dostępne także przy niespełnionym planie.

„Sprawdź gotowość do przekazania” pokazuje osobną pozycję planu i przyczynę
blokady, zanim poprosi o odbiór. Kontrola obowiązuje również bezpośredni zapis
wydania, ponowienie zapisu, pobranie już przygotowanego wydania i dokumenty
przekazania. Zmiana dowodu po odbiorze nadal może zablokować pobieranie.
Nie cofamy automatycznie historycznej decyzji właściciela i nie modyfikujemy
wcześniejszych artefaktów — aktualna gotowość jest sprawdzana ponownie.

Raport odbioru i zapis wydania przechowują `acceptance_proof`: ID cyklu,
ID i checksumę planu, ID i checksumę wyniku, liczbę przykładów. Ta referencja
jest też w `delivery.json` zatwierdzonego ZIP-a. Nie dołączamy pełnych prywatnych
briefów ani logów jako nowej dokumentacji klienta. Kandydat do diagnozy nadal
może być pobrany bez zatwierdzenia; nie jest wydaniem ani odbiorem.

Warunek wykorzystuje istniejące artefakty i nie wymaga migracji. Nie zmieniono
rzeczywistych planów, zadań ani dotychczasowych wydań podczas implementacji.
Testy: `tests/test_acceptance_gate.py`; symulacja potwierdza blokady, poprawny
odbiór, spójność ZIP/raportów, brak powtórnych wykonań i zachowanie historii.
Rzeczywisty pilot z runnerem nadal oczekuje na bezpieczny termin.

- `tests/test_acceptance_cases.py`: walidacja, oczekiwania, zapis/zakres/auth.
- `tests/test_automatic_acceptance.py`: naprawa i retest, brak naprawy zdrowego
  kodu, limit, stop, przerwanie i wznowienie, uszkodzone raporty, blokada wynajmu.
- `tests/test_acceptance_plans.cjs`: DOM/API w pamięci, formularz bez wykonania,
  niepewny zapis, wybrany plan w żądaniu cyklu, rozróżnienie wyników.

Testy używają atrap. Nie dowodzą jeszcze działania nowych przypadków na
prawdziwym kontenerze ani skuteczności konkretnego modelu.
