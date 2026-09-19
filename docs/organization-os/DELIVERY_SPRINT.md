# Sprint: od planu do sprawdzonego wyniku

2026-09-13. Właściciel oczekuje intensywnej pracy w perspektywie kilku dni.
To horyzont sprintu, nie potwierdzony termin ukończenia wszystkich dziedzin firmy.

## Kolejność i kryteria

1. Spójne wejścia pulpitu i Spatial: Centrum realizacji, historia i podgląd
   klienta w obu widokach — wdrożone, testowane. Nie tworzymy kolejnego UI.
2. Instrukcja pojedynczego zadania dla lokalnego modelu: zakres, kryteria,
   kontekst poprzednika, wersja — wdrożony eksport promptu, bez inferencji.
3. Kontrolowana lokalna inferencja: jeden przebieg naraz, zatwierdzona rezerwa
   CPU/RAM/GPU, limit kontekstu/wyniku/czasu, przerwanie własnego żądania,
   bez automatycznych retry. Przed uruchomieniem właściciel musi określić
   zasoby dostępne poza wynajmem Vast.ai. Niskie użycie GPU nie wystarcza.
   Przygotowano [kolejkę próbną](LOCAL_MODEL_QUEUE.md): FIFO, trwałe rezerwacje,
   symulacyjny adapter, kontrola wersji i błędów. Adapter rzeczywistej inferencji
   pozostaje niepodłączony, a wynik symulacji nie jest wynikiem zlecenia.
4. Wynik → paczka plików → izolowana kontrola: istniejące importy i paczki,
   walidacja ścieżek, brak zapisu do repozytorium i hosta przez model.
   Runner kodu wymaga osobnego zaprojektowania granic; sam prompt ich nie zapewnia.
5. Próba pełnego przepływu na małym demonstracyjnym zleceniu: uzgodniony
   zakres, wynik, faktycznie wykonane kontrole, odbiór właściciela, jawna
   publikacja klientowi. Tylko taki przebieg potwierdza gotowość danej usługi.

## Jak mierzymy przyspieszenie

Liczymy odebrane rezultaty i czas przepływu, nie liczbę nazwanych agentów.
Nie aktywujemy wszystkich działów naraz. Jedno małe zlecenie ma kierownika,
wykonawcę i kontrolę; inne działy pozostają zaplanowane. Osobne zadania
mogą powstawać niezależnie, lecz wspólny lokalny model podlega budżetowi
sprzętu, nie liczbie ról. Trening i pobieranie kolejnych modeli nie są
warunkiem pierwszej próby; decyzja o nich wymaga pomiaru braków na zadaniach.

Ograniczenia niezmienne: brak ingerencji w najemców, Docker, Windows, konta
klientów, płatności i publikacje bez właściwego zakresu zatwierdzenia.
