# Porównanie wersji źródeł

Właściciel może sprawdzić zmiany Qwena lub ręcznej poprawki bez uruchamiania
modelu, aplikacji, testów czy kontenera. Porównanie nie zastępuje testów,
odbioru wymagań ani przeglądu bezpieczeństwa i nie zwiększa postępu.

## Obsługa

1. Otwórz `/os/build` — Budowa i testy.
2. Wczytaj zadanie i paczkę albo znajdź jej zakończone wykonanie w historii.
3. Kliknij **Porównaj pliki z wcześniejszą wersją**.
4. Wybierz starszą paczkę tego samego zadania i **Pokaż zmiany**. Lista
   pobierana jest po 20 pozycji; przycisk pozwala wczytać kolejne starsze.
5. Zobacz pliki dodane, usunięte, zmienione i identyczne. Przy zmianie kliknij
   **Pokaż różnice**, aby odczytać tekst z prefiksami `-` (baza) i `+` (wybrana wersja).

Lista pokazuje wcześniejsze ID, nie udowodnioną relację rodzic–poprawka.
Właściciel wybiera bazę świadomie. Obie wersje są opisane ID i SHA-256;
porównanie nie wybiera automatycznie „najlepszej” paczki.
Gdy nie ma starszej wersji, panel wyjaśnia brak porównania.

## Zakres i limity

Metadane wszystkich plików pochodzą z ponownie zweryfikowanych manifestów.
Źródła pojedynczego pliku są zwracane dopiero po żądaniu szczegółów.
Porównanie wierszy obsługuje najwyżej 16 KiB UTF-8 i 300 wierszy na każdą
stronę, z limitem wyjścia 48 KiB. Limity stosowane są przed kosztownym
algorytmem dopasowania. Duże pliki zachowują metadane i komunikat, zamiast
udawać identyczność lub pokazywać nieoznaczone częściowe wyniki.
Zakończenia wierszy są normalizowane wyłącznie do prezentacji; zmiany samych
zakończeń/końcowej nowej linii mają osobny komunikat. Źródła nie są zmieniane.

Kod wyświetlany jest przez textContent w pre, nie jako HTML. Nie ma eval,
importowania plików paczki ani wykonywania poleceń. Zawartość może być prywatna:
to narzędzie właściciela, nie publiczny widok klienta czy załącznik do ZIP-a.
Po odmowie odczytu poprzedni wynik jest czyszczony; zmiana wyboru odrzuca
spóźnioną odpowiedź dla innej bazy. Istniejąca sesja i blokada równoczesnych
operacji panelu pozostają obowiązujące.

## API

`GET /api/tasks/{task_id}/workspace-packages/{package_id}/comparison?base_id={id}`

Opcjonalne `&path=app.py` dodaje szczegół wybranego pliku. Obie paczki muszą
należeć do tego samego zadania. API dopuszcza także porównanie tej samej
wersji oraz jawne porównanie w odwrotnym kierunku. Pole path jest kluczem
manifestu, nigdy ścieżką odczytywaną z hosta.

Odpowiedź `package-comparison.v1`: identyfikatory i checksumy obu paczek,
liczniki zmian, metadata przed/po oraz opcjonalny ograniczony diff.
Tylko właściciel; brak sesji 401, niewłaściwa rola 403, brak paczki/pliku
lub obca paczka 404, niespójność 409, niepoprawne parametry 422, błąd DB 503.
Cache-Control: no-store, X-Content-Type-Options: nosniff. Wyłącznie odczyt:
bez nowych artefaktów, decyzji, mutacji statusów i delegacji.

## Weryfikacja

`tests/test_package_comparison.py` oraz `node tests/test_package_comparison.cjs`.
Izolowana baza i symulowane DOM/API. Brak testu rzeczywistej przeglądarki,
wywołań modeli, kontenerów i ingerencji w Vast.ai.
