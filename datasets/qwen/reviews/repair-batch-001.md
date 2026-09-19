# Przegląd trzech przykładów napraw — 2026-09-13

Recenzent: asystent prowadzący, niezależny od lokalnego Qwena. To odbiór
syntetycznych danych treningowych, nie zgoda właściciela na wydanie produktu.
Kod każdej odpowiedzi przeczytano; nie zmieniono trzech odpowiedzi drugiej serii.

## Dowody

[Zapis testów przed i po naprawie](repair-batch-001-evidence.json) obejmuje
oryginalne fixture, źródła, hashe, pełne wyniki kontenerów i kontrolę sprzątania.
SHA-256 tego dokumentu JSON:
`770d8a3cf7f977188cba05a6c5909b7646c86d43aaf3b0cf06b5565204fc3b1c`.
Referencja do surowego raportu i jego hash są również w JSON.

W drugiej serii synthetic-repair.v2 wykonano sześć kontenerów (przed/po),
trzy inferencje Qwen, łącznie 14.763 s. Przed poprawkami testy rzeczywiście
wykazywały błędy, po poprawkach zaliczono 13 metod unittest i ich przypadki
parametryczne. Wszystkie kontenery potwierdziły kontrolowane właściwości
izolacji i zostały usunięte przez runner po swoim losowym ID oraz etykiecie.

## Kontrola merytoryczna

- **pagination-boundary:** kontrola listy, dodatnich int i wykluczenie bool;
  indeks `(page-1)*size`, nowy wycinek, puste strony poza końcem. Sprawdzono
  odtwarzanie listy z kolejnych stron dla 24 długości i 7 rozmiarów oraz
  nienaruszanie wejścia. Nie ma stałych wyników podstawionych pod testy.
- **duration-carry:** odrzucenie nie-int/bool i wartości ujemnych; modulo
  3600 dla minut, modulo 60 dla sekund; godziny nie zawijają się po dobie.
  Granice oraz odtworzenie sekund z wyniku dla zakresu 0–199999 co 137.
- **stable-deduplication:** zbiór służy wyłącznie do członkostwa, wynik powstaje
  w kolejności pierwszych wystąpień; brak normalizacji, trim i zmiany wielkości
  liter. Odrzucenie nie-str przed hashowaniem, brak mutacji wejścia.
  Testy Unicode obejmują odrębne postaci é i e+znak łączący oraz emoji.

Żadna odpowiedź nie importuje narzędzi, nie czyta testów, nie zapisuje plików,
nie otwiera sieci ani procesów. Recenzja źródeł uzupełnia testy: sam raport
gościa nie jest wystarczającym dowodem, jeśli niezaufany kod próbuje oszukiwać
runner. Kontener współdzieli kernel; nie jest gwarancją izolacji kodu wrogiego.

## Wykryty brak pierwszej serii

Seria repair-drafts-hhdqqsrn miała 3/3 zaliczone, ale przegląd ujawnił brak
walidacji typu items w paginacji i brak odpowiadającego mu testu. Przykładu
nie zatwierdzono. Dodano test test_invalid_items i ponowiono generowanie;
Qwen sam dopisał brakującą walidację. Stare raporty pozostają w workspace.
Nie zmieniano kryteriów tak, aby błędna odpowiedź zaczęła je spełniać.

## Ograniczenia

Trzy proste naprawy funkcji, nie kompletnych aplikacji. HTTP w tej próbie
obsługuje zaufana atrapa health/root wymagana przez istniejący runner;
nie jest wynikiem budowy aplikacji przez Qwena. Brak testu UI i odbioru klienta.
Wszystkie rodziny należą do **train**. Wynik 3/3 nie jest pomiarem na holdoucie
ani dowodem poprawy po QLoRA; w tym kroku nie aktualizowano wag.
