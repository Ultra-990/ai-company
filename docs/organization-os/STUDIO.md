# Pulpit strukturalny — przebudowa Studio

## Kierunek wizualny

Referencją właściciela jest futurystyczny pulpit z holograficznymi oknami.
Nie używamy zdjęcia stockowego ani jego znaku wodnego jako elementu aplikacji.
Scenę budują natywne elementy HTML/CSS/SVG: światło, perspektywa paneli,
przygaszone tło, kuliste centra właściciela i Brain. Nie jest to jeszcze
silnik przestrzenny WebGL ani aplikacja natywna Linux.

Nieaktywne działy są cofnięte perspektywą i przygaszone. Po otwarciu działu
okno wyprostowuje się, trafia na pierwszy plan, pokazuje kolor działu,
opis i dane. Ikony operacji pozostają rozróżnialne także na nieaktywnym oknie.
Po aktywowaniu innego działu poprzednie okno wraca do swojej pozycji.
Nie dodajemy fikcyjnych wykresów ani losowych procentów dla ozdoby.

## Obsługa

- `/os`: pełny pulpit z 12 działami; na mniejszym ekranie przewijana lista.
- Kula właściciela lub przycisk **Właściciel** otwiera stan organizacji.
  Przycisk w pasku pozostaje dostępny, gdy duże okno przykrywa kulę.
- Brain ma własny dialog. Menu nie jest już potomkiem wizualnej warstwy kuli:
  trafia do natywnej górnej warstwy dialogowej, a nie konkuruje z jej `z-index`.
- Okna: przeciąganie za nagłówek, szczegóły, minimalizacja, maksymalizacja
  i zamknięcie. Zamknięte/minimalizowane okna można przywrócić z listy na dole.
- **Przywróć układ** przywraca wszystkie działy do pozycji początkowych.
- **Zależności** pozwalają ukryć dodatkowe połączenia między działami.
- Powiadomienia w oknie działu filtrują po `organization_unit_id`.
- **Jasny/Ciemny** przełącza wspólne tokeny kolorów pulpitu, dialogów i klienta.
  Zapisywana jest tylko preferencja motywu. Przy jej braku używamy preferencji
  systemu. Tryb ograniczenia ruchu respektuje `prefers-reduced-motion`.

## Zmiany wpływające na wydajność

- Okna mają trwałą tożsamość według klucza działu. Bez zmian danych nie
  odtwarzamy ich zawartości i nie tracimy stanu otwarcia przy odświeżaniu.
- Linie SVG mają trwałą tożsamość według relacji. Duplikaty relacji w danych
  nie powodują rysowania kolejnych identycznych linii.
- `pointermove` aktualizuje stan przeciągania. Jedno `requestAnimationFrame`
  stosuje ostatnią pozycję i aktualizuje połączenia; nie ma osobnego pełnego
  przebudowania sieci dla każdego zdarzenia myszy.
- Odczyty geometrii wszystkich węzłów są zgrupowane przed zapisami SVG.
- Usunięto stale animowane kreski, szerokie rozmycia i `backdrop-filter`
  dla wszystkich okien. Nie ma ciągłej pętli renderującej w spoczynku.
- Odświeżanie API nadal odbywa się co 30 sekund, ale tylko na widocznej karcie.
  Żądania nie nakładają się. Błąd jednego źródła nie kasuje całego pulpitu;
  zachowany stan jest oznaczony jako niepełny.

Mechanizmy opisują: [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame),
[natywna warstwa dialogowa](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog)
i [ograniczenie ruchu](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion).

To usunięcie wykrytych kosztownych operacji, nie deklaracja określonego FPS.
Krótki test przeglądarkowy potwierdza zachowanie i geometrię, nie zastępuje
profilowania na stanowisku właściciela podczas rzeczywistej pracy.

## Sprawdzenie bez ingerencji w Vast.ai

`scripts/check_os_browser.py --output <katalog-testowy>` uruchamia wyłącznie
własny tymczasowy proces Chrome w trybie headless z wyłączonym GPU.
Łączy się odczytowo z już działającym `127.0.0.1:8000`, sprawdza warstwy,
trwałość elementów, przeciąganie, motywy i układ mobilny. Przykładowy widok
klienta jest symulowany tylko wewnątrz przeglądarki. Nie powstaje token klienta
ani zapis w produkcyjnej bazie. Proces przeglądarki jest zamykany po teście.

Właściciel dopuścił krótkie użycie GPU do grafiki 2026-09-12. Te testy go nie
wymagały. Nie uruchamiano modeli, treningu, kontenerów ani benchmarków.
