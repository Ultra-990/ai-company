# Przekazanie aplikacji klientowi — instrukcja i szkic wiadomości

Wdrożony zakres: profil `python-web-v1`. Brak modeli, inferencji, kontenerów,
sieci zewnętrznej, połączenia z Upwork i automatycznej wysyłki w tym kroku.
Odczyt istniejącego wydania można wykonywać bez obciążania GPU.

## Właściciel

1. Otwórz `/os/build` (Budowa i testy), sekcję „Wyniki i przekazanie”.
2. Przy właściwym wykonaniu sprawdź gotowość i przygotuj zatwierdzone wydanie.
   Jeżeli wymaga nowych testów lub inferencji, poczekaj na koniec wynajmu Vast.ai.
3. Wybierz **Instrukcja klienta i wiadomość do Upwork**. Jeżeli brakuje odbioru
   lub zapisu wydania, panel wyjaśni blokadę — nie ominie jej dla dokumentów.
4. Przeczytaj checklistę, instrukcje i metrykę wydania PL/EN oraz szkic wiadomości EN. Szkic można
   zaznaczyć/skopiować lub pobrać jako TXT i dostosować przed wysłaniem.
5. Pobierz zatwierdzony ZIP z tego samego wykonania i sam przekaż go klientowi.
   Dokumenty nie wysyłają wiadomości, nie przyjmują odbioru klienta ani nie
   zmieniają statusu zadania, projektu, płatności czy publikacji.

Instrukcja działa bez dostępu klienta do panelu właściciela. Wyjaśnia aplikację
serwerową, katalog `sources/`, adres HTTP zamiast `file://`, start na Linux/macOS
i Windows PowerShell, testy oraz sposób zgłoszenia błędu. To instrukcja profilu,
nie wygenerowany opis poszczególnych funkcji; opis funkcji pozostaje w README
źródeł i wymaga sprawdzenia. Nie deklaruje hostingu, SLA ani pełnego odbioru.

## ZIP i wersjonowanie

Dotychczasowe `sources/`, `delivery.json` i `test-report.json` pozostają.
Do zatwierdzonego wydania, ale nie ZIP-a kandydata, dodano:

- `CLIENT-START-HERE.md`: instrukcja EN;
- `CLIENT-START-HERE.pl.md`: instrukcja PL;
- `DELIVERY-SUMMARY.md`: metryka wydania EN;
- `DELIVERY-SUMMARY.pl.md`: metryka wydania PL;
- `handoff.json`: wersja szablonu `client-handoff.v2`, SHA-256 źródeł, raportu,
  zapisu wydania i wszystkich czterech dokumentów.

Metryka zawiera listę plików, ich rozmiary i SHA-256, źródłową wersję,
zapisany profil testów oraz liczbę sprawdzonych przykładów HTTP, jeżeli
istnieje wybrany i zaliczony plan. Liczba ta pochodzi z ponownie zweryfikowanego
dowodu wydania, nie z liczby szkiców lub ręcznych deklaracji. Bez planu jest
jawne „nie wybrano osobnego planu”, nie „brak testów” i nie „pełny zakres gotowy”.
Wskazane bajty dotyczą źródeł, nie całego ZIP-a. Metryka zawiera też instrukcję
zgłoszenia problemu: wersja, kroki, wejście, wynik oczekiwany i rzeczywisty,
środowisko, powtarzalność i wpływ — bez sekretów czy danych osobowych.

Spis plików nie jest automatycznie listą działających funkcji. Metryka nie
kopiuje prywatnego briefu, nazw/ścieżek przypadków HTTP, ich danych wejściowych,
odpowiedzi ani logów. Nie udaje potwierdzenia zakresu biznesowego, wyglądu,
pełnego audytu, wdrożenia lub odbioru klienta. Aplikacyjne funkcje nadal wymagają
oceny README i uzgodnień. Nowe dokumenty nie usuwają prywatnych treści, które
mogły wcześniej znaleźć się w źródłach/test-report.json — właściciel sprawdza je
przed wysłaniem, jak dotąd.

Szkic wiadomości i checklista właściciela nie są automatycznie dołączane do ZIP-a.
Dokumenty nie kopiują opisu zadania, uwag, treści promptów, tytułów ani sekretów
sesji. Nie oznacza to automatycznej kontroli sekretów w samych źródłach i raportach
dotychczasowej paczki — je również należy sprawdzić przed udostępnieniem.

Dokumenty powstają deterministycznie przy odczycie, nie są nowym artefaktem w DB.
Zmiana szablonu nie zmienia źródeł ani starego raportu; może zmienić bajty ZIP-a.
SHA-256 źródeł NIE jest sumą całego ZIP-a. Sumy instrukcji są osobne, a pobrane
dawniej ZIP-y nie są modyfikowane. Istotna zmiana kontraktu wymaga nowej wersji
szablonu. Ta funkcja nie sprawdza licencji lub zgodności biznesowej za właściciela.

## API i kontrola

`GET /api/package-runs/{run_id}/handoff` — tylko właściciel, ten sam mechanizm
sesji/uwierzytelnienia co inne operacje wydania; `Cache-Control: no-store`.
Zwraca dokumenty, checksumy, metadane plików bez treści i checklistę.
Od wersji v2 zwraca również `delivery_summary` (schemat `delivery-summary.v1`)
z tym samym technicznym podsumowaniem. `verified_http_examples: null` oznacza
brak osobnego wybranego planu, a nie zero wykonanych testów. W panelu metrykę
można przeczytać lub pobrać oddzielnie. Każde pobranie ponownie kontroluje wydanie.
404: brak wykonania; 409: brak aktualnego odbioru/zapisu wydania lub niespójność;
503: problem odczytu bazy. Nie ma nowego endpointu mutującego.

Wspólny walidator z ZIP-em sprawdza powiązania konkretnego testu, paczki,
raportu i zaakceptowanej próby. Nowy niezaliczony test tej paczki unieważnia
gotowość starego wydania. Pobranie dokumentu w panelu ponawia kontrolny GET;
już skopiowanej lub pobranej treści nie można zdalnie wycofać.

Testy: `tests/test_delivery_handoff.py`, `tests/test_delivery_summary.py`
oraz `node tests/test_delivery_handoff.cjs`.
Baza testowa, model i runner zastąpione atrapami; kontroler testowany w symulowanym
DOM, nie w prawdziwej przeglądarce. Brak rzeczywistej wysyłki i uruchamiania
instrukcji na Windows/macOS. Testy tego modułu nie są dowodem jakości produktu klienta.
