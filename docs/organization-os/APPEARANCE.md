# Wspólny wygląd i nawigacja

Stan: 2026-09-12. Zamiast osobnych zestawów barw każdy widok aplikacji
korzysta z `theme.js` oraz `theme.css`.

## Ustawienia

Na początku strony znajdują się **Wstecz**, **Pulpit**, wybór **Paleta** oraz
przełącznik trybu jasnego/ciemnego. Paleta i jasność to dwa osobne ustawienia:

Na `/os` i `/os/spatial` Pulpit jest częścią wspólnego przełącznika
**Pulpit | Spatial**. Ma to samo położenie i przyklejony pasek w obu widokach;
aktywny widok ma `aria-current=page`. Bez JavaScript zostaje zwykły link do pulpitu.

- **Biała / czarna**: tło dokładnie #ffffff lub #000000; powierzchnie paneli
  mają delikatne szarości, żeby dało się odróżnić okna od tła.
- **Zielona**: zielonkawe powierzchnie i akcenty w obu jasnościach.
- **Niebieska**: niebieska rodzina powierzchni i akcentów w obu jasnościach.

Domyślnie paleta neutralna i jasność systemowa, chyba że wcześniej zapisano
wybór jasności. Dwie publiczne preferencje `organization-theme` oraz
`organization-palette` są w localStorage; zmiany synchronizują też otwarte
karty tej samej domeny. Brak dostępu do storage nie blokuje strony — ustawienie
działa w bieżącej karcie. Tokeny, treści projektów i historia URL nie trafiają
do tych ustawień. Wylogowanie usuwa dane robocze i token, ale zachowuje wygląd.

Wspólne kolory obejmują `/os`, `/os/spatial`, `/os/work`, lokalny `/client`,
starszy dashboard `/` i `/progress`, a także okna dialogowe. Kolory statusów
i ikon operacji nadal rozróżniają znaczenie — nie wszystko ma ten sam akcent.
Podgląd paczki HTML/CSS zachowuje design oglądanego projektu i celowo nie
otrzymuje kolorów panelu właściciela.

## Powrót i szczegóły

- **Pulpit** w wewnętrznej aplikacji prowadzi zawsze do `/os`.
- **Wstecz** używa historii, gdy dostępny jest referrer z tej samej domeny;
  wejście bez takiej informacji prowadzi do pulpitu. Nie zapisujemy poprzednich
  URL ani nie obchodzimy polityki no-referrer w prywatnych panelach.
- Lokalny podgląd portalu klienta ma powrót do `/os`. Oddzielna aplikacja
  `app.client_main` zachowuje własny `/client` jako stronę główną: nie ma
  linku ani dostępu do wewnętrznego pulpitu właściciela.
- Spatial: okno szczegółów ma **Wstecz**, **Menu właściciela** oraz **Pulpit**.
  Wstecz przechodzi przez ostatnio odwiedzone panele i podpunkty, a z pierwszego
  panelu wraca do sceny. Historia panelu jest wyłącznie w pamięci, do 50 wpisów;
  zamknięcie ją czyści. Escape nadal zamyka modal.
- Panele właściciela, Brain, powiadomień, odbioru i udostępniania na `/os`
  mają opisany powrót do pulpitu. Zamknięcie odbioru/udostępniania nadal czyści
  tokeny przez dotychczasową obsługę zdarzenia close.

## Spatial bez przewijania małych kart

Karty zawierają tylko nazwę, postęp, krótki stan oraz przycisk szczegółów.
W oddaleniu pozostają większa nazwa, procent i przycisk; reszta jest ukryta,
aby nie wyświetlać drobnego tekstu bez sensu. Opisy i podpunkty nie są kopiowane
do ciasnej karty. Pełny zakres jest w modalu do 940 px szerokości z tekstem
16 px; większa zawartość może być normalnie przewijana w tym panelu.

Kliknięcie karty wybiera dział. Kółko nad sceną przybliża/oddala ten dział,
bez zmiany selekcji ani pozycji dokumentu. W widoku mapy oraz poza sceną kółko
przewija stronę normalnie. Pozostają przesuwanie za nagłówek,
minimalizacja, otwieranie szczegółów, zamknięcie, katalog i bezpośrednie kroki.

## Kule-planety i księżyce

Kule Właściciela oraz Brain w `/os` i `/os/spatial` mają lekki efekt księżyca
na pojedynczej eliptycznej orbicie. Księżyc pojawia się przy hover lub focus-visible;
pozycja aktualizowana jest przez requestAnimationFrame tylko podczas interakcji
z widoczną kulą. Scena WebGL nie jest przez to stale renderowana.
Tylna połowa orbity i księżyc korzystają z maski SVG wycinającej sylwetkę sfery;
przednia połowa jest widoczna przed kulą. Księżyc za kulą poza jej sylwetką
pozostaje widoczny, jak przy przestrzennym przesłanianiu.
Po zakończeniu interakcji znika, a pętla jest zatrzymywana. Elementy dekoracyjne
mają aria-hidden i pointer-events:none, więc nie przesłaniają kliknięcia menu.
W `prefers-reduced-motion` księżyc może być widoczny, ale nie krąży. Na dotyku
nie jest wymagany hover: dotknięcie kuli nadal otwiera menu.

To lekka dekoracja SVG/JS z projekcją orbity i maską sylwetki, nie symulacja
orbitalna ani nowy model 3D. Nie uruchamia modeli AI ani kontenerów.

## Weryfikacja

- `tests/test_shared_appearance.py`: wspólne zasoby i linki na sześciu stronach,
  granica oddzielnego portalu klienta, usunięcie nadpisywania motywu przez workbench.
- `scripts/check_work_browser.py`: 36 porównań tła/palety/jasności między
  stronami, nawigacja mobilna, dotychczasowa izolacja źródeł i tokena.
- `scripts/check_spatial_browser.py`: brak scrolla kart, większe szczegóły,
  cofanie w panelu, efekt obu księżyców i reduced motion. Tylko własny Chrome,
  GPU wyłączone; WebGL testowany krótkotrwale przez oprogramowanie SwiftShader.
