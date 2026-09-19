# Centrum realizacji — `/os/work`

Generowanie plików, testy kontenerowe i pobierane wydania:
[Fabryka aplikacji — instrukcja](APPLICATION_FACTORY.md), panel `/os/build`.

14.09.2026: [podgląd i wersjonowana edycja plików](PACKAGE_EDITS.md) w Budowie
i testach. Wiele katalogów, nowa paczka bez nadpisania bazy, bez uruchamiania kodu.

Dodano [kontrolę struktury i składni projektów wielomodułowych](MULTIFILE_RUNNER.md).
Panel wskazuje problemy z plikami i katalogami testów. Nowy tester kontenerowy
przeszedł rzeczywisty pilot 19.09. W panelu działają już testy wielomodułowe,
historia raportów, bezstanowy podgląd, odbiór konkretnej paczki i wydanie ZIP;
automatyczne poprawki wymagają dalszej integracji. Nie zmieniono kontraktu
dotychczasowego profilu wykonawczego.

2026-09-13: dostępne [rzeczywiste wykonanie lokalnego Qwen](LOCAL_INFERENCE.md).
Przy instrukcji zadania wybierz **Uruchom lokalny Qwen — wynik do odbioru**.
Historia znajduje się w sekcji **Lokalny Qwen**; stara kolejka próbna nadal
wykonuje wyłącznie symulacje. Model generuje tekst, nie uruchamia kodu.

Stan: 2026-09-12. Pierwszy działający odcinek procesu przyjęcia zlecenia
i przygotowania plików. Nie jest jeszcze autonomiczną fabryką aplikacji.

Dodano [zespoły działów i trwałe delegacje](AGENT_TEAMS.md): kierownik,
wykonawca, niezależny kontroler, instrukcja i poprzedni etap przy każdym
zadaniu. Przycisk **Przydziel kierownika i agentów** nie uruchamia inferencji.

Dodano [instrukcje, import wyników i odbiór w tym samym panelu](AGENT_HANDOFF.md).
Przy gotowym etapie wybierz **Przygotuj instrukcję**, dostarcz rzeczywisty
rezultat, potem **Odbierz wynik**. Jest to jawny import właściciela, bez AI.

2026-09-13: [kolejka próbna lokalnego modelu](LOCAL_MODEL_QUEUE.md).
Przy instrukcji wybierz **Dodaj instrukcję do kolejki próbnej**, zamknij okno
i w sekcji kolejki wybierz **Symuluj jedną oczekującą pozycję**. To sprawdza
obieg ze stałą atrapą, nie wykonuje zadania ani nie uruchamia Qwen.
Poprawki zachowują historię, a kolejne etapy wymagają odbioru poprzednich.

To **panel właściciela**, nie klienta. Docelowy rozdział kont i płatności
opisuje [plan kont klientów](CLIENT_ACCOUNTS_PLAN.md); nie jest jeszcze wdrożony.

Skrót **Projekty i aktywność klientów** prowadzi do `/os/clients`: historii
publikacji i zgłoszonej nawigacji odbiorców kodów. Nie jest to monitoring ekranu
ani dowód wykonania pracy. [Zasady i obsługa](CLIENT_PORTAL.md).

## Przewodnik bieżącego projektu — 14.09.2026

Wybierz projekt z listy lub otwórz `/os/work?project=ID`. Panel „Twój następny
krok” na początku centrum pokazuje cztery istniejące etapy, liczbę odebranych
wyników, aktualny problem i przycisk prowadzący do odpowiedniej kontrolki.
Kliknięcie etapu przenosi fokus na jego kartę, bez przepisywania numeru.
Wykonanie, zapis instrukcji, odbiór i publikacja pozostają osobnymi działaniami.

### Przygotowanie i wznowienie etapu

Gdy przydział i zależności są poprawne, wybierz **Przygotuj bieżący etap — bez
uruchamiania modelu**. Koordynator wybiera dokładnie etap widoczny w panelu,
zapisuje instrukcję z kontekstem poprzednika lub uwagami do odrzuconego wyniku
i otwiera istniejący dialog pracy. Nie deleguje nowych ról, nie uruchamia
modelu, nie kolejkuje zadania i nie zmienia jego postępu.

Przy utracie odpowiedzi odśwież projekt i ponów przygotowanie: identyczny
kontekst otworzy tę samą instrukcję. Po zmianie zadania, wyniku, planu,
przydziału lub rejestru wykonania stary przycisk dostanie konflikt — nie
przeskoczy sam do innego etapu. Po odbiorze wróć do przewodnika, aby przygotować
kolejny etap; odrzucenie prowadzi do poprawy bieżącego, a nie pominięcia go.

API: `POST /api/work-orders/{project_id}/prepare-next`, tylko właściciel,
JSON: `task_id` i `expected_revision` z pola `coordination` odczytanego projektu.
Rewizja wykrywa zmianę stanu, nie jest tokenem uprawniającym do wykonania.
Zapis jest transakcyjny, a instrukcje korzystają z istniejącej deduplikacji
po treści i audytu. Nie ma nowej kolejki ani procesu działającego w tle.
Zablokowany/anulowany projekt lub plan nie pozwala przygotować instrukcji
także przez starsze API zadania. Zapisany prompt nie omija tej kontroli przy
ponownym eksporcie do wykonawcy. Odczyt historycznej instrukcji pozostaje możliwy.

### Historia dla projektu

W sekcji **Historia i wznawianie pracy** wybierz wybrany projekt lub wszystkie
projekty, następnie **Pokaż stan i historię Qwen**. Opcja **Tylko oczekujące,
trwające i niepewne** pozwala znaleźć również dawne nierozstrzygnięte wpisy;
nie znikają dlatego, że powstało 30 nowszych wyników. Przycisk **Starsze
wykonania** pobiera następną stronę. Zmiana projektu lub filtrów czyści poprzedni
widok. Odczyt historii nie uruchamia Qwena ani nie anuluje żadnego procesu.
Istniejące kontrolowane ponowienie pozostaje osobnym działaniem.

### Interpretacja stanów

- Brak delegacji kieruje do przydziału agentów; najpierw przygotuj zespoły,
  jeśli jeszcze nie istnieją.
- Wynik do odbioru i poprawa prowadzą do karty zadania oraz istniejących
  instrukcji/kontrolek. Przewodnik sam nie akceptuje ani nie naprawia wyników.
- Oczekująca, trwająca lub niepewna inferencja kieruje do historii. Odczytaj ją
  przyciskiem, zanim ponowisz pracę; zapisany stan nie jest pomiarem sprzętu.
- Ukończone zadanie bez odebranej, spójnej ostatniej próby to brak dowodu,
  a nie odebrany etap. Suma kontrolna potwierdza integralność, nie jakość pracy.
- Odbiór wszystkich etapów kieruje do plików i testów. Nie zastępuje bramki
  wydania, decyzji publikacji ani odbioru klienta.

Dane pochodzą z pola `guidance` istniejącego owner-only API szczegółów
zlecenia. Nie ma nowej tabeli, własnego procentu ani dodatkowej roadmapy.
Odświeżanie korzysta z istniejącej pętli 30 s, wstrzymanej podczas pracy
w formularzu, przewodniku lub dialogu. Przycisk „Odśwież” pobiera bieżący stan.
Odczyt nie uruchamia modeli, testów ani zapisów. Dostępność GPU nie jest
monitorowana przez ten panel; wynajem Vast.ai wymaga osobnego potwierdzenia.

## Obsługa

Wspólny pasek nawigacji oferuje **Wstecz**, **Pulpit**, wybór palety i trybu
jasnego/ciemnego. Wygląd nie zmienia się sam przy przechodzeniu między stronami.
Szczegóły: [wygląd i nawigacja](APPEARANCE.md).

1. Otwórz `http://127.0.0.1:8000/os/work` lub kliknij **Centrum realizacji ↗**
   tuż pod górnym paskiem na `/os/spatial` lub `/os`. Skrót jest widoczny
   również na telefonie i nie wymaga otwierania kuli ani załadowania drzewa.
   Dotychczasowe wejście w menu Właściciela również pozostaje dostępne.
2. Podaj istniejący token właściciela (`OWNER_API_TOKEN` skonfigurowany dla
   procesu aplikacji), kliknij **Połącz**. Nie zapisuj tokena w repozytorium,
   opisie zlecenia ani dokumentacji. Token workera nie ma tu dostępu.
3. Wpisz tytuł, cel, odbiorców, ograniczenia, konkretny liść drzewa oraz
   kryteria odbioru (osobne wiersze). Nie wpisuj sekretów i niepotrzebnych
   danych osobowych. Dane są zapisywane w istniejącej lokalnej bazie SQLite.
4. **Utwórz projekt i zadania** zapisuje atomowo projekt, plan i cztery
   zadania: specyfikacja, implementacja, testy, odbiór/przekazanie.
   Każde ma proponowaną rolę i kryterium etapu; żadne nie jest wykonane.
5. Jeśli to strona internetowa, wybierz **Przygotuj szkielet strony**.
   Powstaje rzeczywista, niezmienna paczka z `index.html`, `styles.css`,
   `brief.json`, `README.md`. **Pobierz ZIP** zapisuje ją na Twoim komputerze.
   Rozpakuj w osobnym folderze i otwórz `index.html`; instalacja zależności
   nie jest potrzebna. Nie wczytuj obcych paczek HTML w originie panelu firmy.
6. Dopracuj źródła w osobnym projekcie. W istniejącym `/os` → menu właściciela
   → **Paczki projektów i odbiór wyników** możesz zapisać kolejne wersje,
   używając widocznego ID zadania implementacji.
7. Przy paczce kliknij **Sprawdź pliki**. Trwały raport pokazuje podstawowe
   kontrole HTML/JSON i odnośników, bez uruchamiania kodu. Szczegóły i granice:
   [kontrola paczek](PACKAGE_CHECKS.md). Raport można później otworzyć z artefaktów.
8. **Zapisz na dysku Linux** eksportuje tę wersję do przygotowanego katalogu
   na partycji `/home`; panel pokazuje ścieżkę. **Sprawdź zapis na dysku**
   kontroluje później jego integralność. To nie uruchamia programu.
   Zasady i limity: [magazyn eksportów](STORAGE.md).
9. **Podgląd strony** otwiera wersję HTML/CSS wewnątrz odizolowanej ramki.
   Przełącz **Szeroki / Telefon**, sprawdź numer paczki i jej SHA-256.
   Escape zamyka okno. Skrypty, formularze i połączenia sieciowe są wyłączone;
   brak funkcji w tym widoku nie oznacza automatycznie błędu paczki.
   Szczegóły: [profil i zabezpieczenia podglądu](PREVIEW.md).

Szablon strony ma responsywny układ, wariant jasny/ciemny, skip link i style
fokusu. Nie zawiera JavaScript, formularzy, analityki, zewnętrznych fontów
ani żądań sieciowych. Treści briefu są escapowane. To własny stały szablon,
**nie odpowiedź modelu AI ani realizacja projektu premium**. Nie realizuje
automatycznie dowolnych funkcji opisanych w briefie. Testy i odbiór konkretnej
strony pozostają do wykonania. Zapis paczki nie podnosi procentu żadnego zadania.

## Idempotencja i błędy

Formularz generuje UUID `request_id`. Powtórna wysyłka tego samego opisu
z tym samym ID zwraca istniejący projekt. Zmieniony opis z zajętym ID daje
409. UUID nie jest tokenem dostępu.

Po timeout/503 najpierw odśwież listę. Ponowienie niezmienionego formularza
zachowuje UUID. **Rozpocznij nowy formularz** świadomie rozpoczyna inne
zlecenie. Po zamknięciu/wylogowaniu karty UUID i niezapisany formularz są
czyszczone: przed ponownym wpisywaniem sprawdź istniejące zlecenia.

Przygotowanie szkieletu jest oddzielnym, wersjonowanym zapisem. Kolejne
kliknięcie tworzy kolejną paczkę; po niepewnej odpowiedzi sprawdź listę
artefaktów przed powtórzeniem. Lista pokazuje ostatnie 50 artefaktów projektu;
pełna paginowana historia paczek zadania pozostaje w dotychczasowym panelu.

Lista zleceń ma paginację po 20 rekordów. Automatyczne odświeżanie co 30 s
działa tylko na widocznej karcie, poza zapisem i pracą kursora w formularzu
lub szczegółach. Nie nadpisuje treści nowego zlecenia. Lista obejmuje tylko
zlecenia utworzone tym mechanizmem — wcześniejsze projekty nie są migrowane.

## Stan wykonania i Vast.ai

- Zadania startują z `pending`, zgodą `pending`, postępem 0 i `queued_at=NULL`.
- Nawet sama zgoda istniejącego API nie aktywuje zadania bez daty kolejki.
  Nowy panel nie oferuje uruchamiania inferencji ani zwalniania tej blokady.
- Przed delegacją role są nazwami odpowiedzialności; po przydziale wskazują
  istniejące tożsamości z rejestru agentów. Nadal nie są procesami AI.
- Cztery etapy są stałym szablonem, nie planem opracowanym przez orkiestrator.
  Delegacje sprawdzają odbiór poprzedniego etapu, ale nie uruchamiają
  harmonogramu wykonawczego ani promocji projektu/planów do `completed`.
- Model/generowanie kodu, izolowane uruchamianie testów, podgląd aplikacji
  i automatyczne poprawki pozostają kolejnym etapem. Konieczne jest uzgodnienie
  zasobów, które nie naruszą wynajmu Vast.ai. Nie należy obchodzić tego SQL-em.

Migracja kolejki uzupełnia `queued_at` ze starych danych wyłącznie przy
**dodawaniu tej kolumny**, nie przy każdym otwarciu repozytorium. Dzięki temu
celowy brak zakolejkowania przetrwa ponowne uruchomienie aplikacji.

## API i zapis

Wszystkie poniższe operacje wymagają Bearer Owner i odpowiadają `no-store`:

- `GET /api/work-orders/options` — dostępne aktywne liście i jawne ograniczenia.
- `POST /api/work-orders` — UUID, tytuł, cel, odbiorcy, ograniczenia, ID węzła,
  lista kryteriów; 201 nowy projekt, 200 odtworzenie odpowiedzi, 409 konflikt.
- `GET /api/work-orders?before={project_id}` — lista z kursorem.
- `GET /api/work-orders/{project_id}` — zakres, zadania, ostatnie próby i artefakty.
- `POST /api/work-orders/{project_id}/website-starter` — zapis nowej paczki;
  pobieranie korzysta z istniejącego, chronionego API workspace-packages.

Nowa tabela `work_orders` przechowuje UUID, hash opisu, brief oraz odnośniki
do istniejących `projects`, `plans`, `tasks`. Rejestracja modelu i istniejące
`Base.metadata.create_all` tworzą ją przy starcie, bez usuwania dawnych danych.
Zapis zlecenia i jego zdarzenie audytu należą do jednej transakcji. Zapis paczki
korzysta z dotychczasowego magazynu artefaktów oraz weryfikacji SHA-256.

Token żyje tylko w pamięci/niezapisywanym formularzu karty; opuszczenie strony
i **Wyczyść dostęp** czyszczą token, brief i odczytane dane. Żądania nie
podążają za przekierowaniami. CSP blokuje skrypty inline i natywne wysyłanie
formularzy, aby awaria JavaScript nie umieściła opisu w query string.

**Nie publikuj całej aplikacji w internecie:** starsze endpointy odczytu
projektu mają odrębny zakres zabezpieczeń. Ta funkcja nie zmienia ich RBAC.

## Testowanie

`pytest -q tests/test_work_orders.py tests/test_task_queue_migration.py`
używa izolowanych baz i sztucznych tokenów. Sprawdza również rzeczywisty ZIP,
idempotencję, brak wykonania, zachowanie po migracji i odrzucanie HTML jako kodu.

`python scripts/check_work_browser.py` otwiera wyłącznie własny Chrome
z wyłączonym GPU. Wszystkie wywołania API są symulowane w tej przeglądarce;
formularz nie zapisuje danych produkcyjnych. Testuje ponowienie, formularz,
przygotowanie paczki, brak wykonania HTML, mobile i wylogowanie.
