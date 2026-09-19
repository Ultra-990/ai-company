# Dlaczego działy pokazywały 0%?

Audyt odczytowy 2026-09-13: 40 zadań w bazie, 27 bez projektu. Zadania
przypisane były do trzech liści istniejącego drzewa. Licznik nie skanuje
repozytorium: liść liczy postęp zadań przez projekt, rodzic liczy średnią
ważoną dzieci. Dlatego nowe moduły, testy i dokumentacja nie zwiększały
automatycznie procentu innych działów. Jest to stan z chwili audytu, nie stała.

## Zmiana odczytu, nie podnoszenie procentów

- `measurement_state=unmeasured`: gałąź bez przypisanych zadań. UI pokazuje
  „— / brak pomiaru”, nie udaje dowodu zerowego wykonania.
- `partial`: istnieją zadania, ale część dzieci nie ma pełnego pokrycia
  lub rodzic ma zadania, którym nie przydzielono zakresu w dzieciach.
- `tracked`: liść z zadaniami lub rodzic, którego dzieci mają pomiar.
  Nie oznacza to pełnego planu, zweryfikowanego odbioru lub pokrycia testami.
- `progress` zachowuje kompatybilny wynik dotychczasowego algorytmu.
  `progress_note` jawnie opisuje źródło i ograniczenia pomiaru.
- `subtree_task_count/project_count/blocked_task_count` obejmują potomków.
  Stare `task_count/project_count/blocked_task_count` pozostają bezpośrednimi
  licznikami dla zgodności kontraktu. Pulpit korzysta z liczników całej gałęzi.
- Zadania bezpośrednio na rodzicu z dziećmi nadal nie wpływają na jego średnią.
  Teraz raportujemy to w `direct_tasks_outside_aggregation` i komunikacie.
  Nie nadajemy im arbitralnej wagi kosztem istniejącego planu.

## Fundamenty i plan pierwszego odbioru

`app/organization_os/department_foundations.py` wiąże istniejące klucze
12 działów z jawnym inwentarzem repozytorium, następnym krokiem i trzema
kryteriami gotowości. To opisy istniejących węzłów, nie druga roadmapa ani
osobne drzewo punktacji. API zwraca je jako `foundation`; nie ma tam procentów.

Sprawdzamy wyłącznie obecność wskazanych plików. **Obecność pliku nie oznacza
ukończenia działu, uruchomienia agenta lub zaliczenia testu.** Nazwy materiałów
są stałą listą kodu/dokumentacji/testów; nie skanujemy danych klientów,
sekretów ani nie udostępniamy dowolnych plików przez API.

W zwykłym pulpicie wybierz **Otwórz dział**, w Spatial **Szczegóły**:
źródło pomiaru, materiały do odbioru, „Co zbudować teraz”, kryteria gotowości.
Warstwa odczytu nie zmienia statusów, wag, przydziałów lub wyników zadań.

## Prace do rzeczywistego uzupełnienia rejestru

1. Przejrzeć 27 nieprzypisanych zadań: odróżnić próby od rzeczywistych prac.
   Nie zaliczać historycznego „COMPLETED” bez sprawdzenia kryteriów i dowodów.
2. Przypisać rzeczywiste rezultaty do istniejących liści i projektu budowy;
   jednemu rezultatowi przydzielić zakres bez podwójnego naliczania.
3. Dodać brakujący mierzalny zakres operacyjny: oferta, odbiór zlecenia,
   procedura wydania, odtwarzanie, rozliczenia. Nie budować równocześnie
   wszystkich produktów R&D, żeby uzyskać niezerowe wskaźniki.
4. Odebrać fundamenty na podstawie konkretnej wersji i wyniku testów;
   wtedy zapisać postęp w planie. Reguły dla kryteriów/dowodów poza zadaniami
   wymagają dalszego rozszerzenia pomiaru, nie samej zmiany etykiet.
