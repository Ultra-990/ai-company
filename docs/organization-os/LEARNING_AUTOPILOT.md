# Automatyczne przygotowanie danych do nauki

Stan 21.09.2026: działa pierwszy etap — zbieranie niezależnie ocenionych
rozmów obraz–tekst i audyt CPU. **Automatyczne treningi wag nie są jeszcze
podłączone.** Wcześniejsze małe pilotaże nie wykazały poprawy; harmonogram
nie powtarza ich jako pozornej nauki i nie wdraża adapterów.

`scripts/learning_autopilot.py --once` przegląda wyłącznie prywatne,
syntetyczne ćwiczenia wnętrz i wektorów. W każdym cyklu ponownie sprawdza
oryginalną odpowiedź modelu, obrazy i niezależną ocenę. Odrzucone przykłady
oraz rodziny development/validation/test nie trafiają do treningu.
Zmiana lub wycofanie oceny usuwa przykład z bieżącej liczby gotowych danych.
Blokada plikowa zapobiega jednoczesnym cyklom; do dwóch nowych audytów CPU
w cyklu ogranicza obciążenie. Poprawne, niezmienione audyty są używane ponownie.

`vector_learning_records.py` eksportuje dokładną ocenioną odpowiedź narzędzia
lokalnego modelu i rzeczywisty PNG wzorca. Wspólny audyt sprawdza hash,
oryginalną rozmowę, maskowanie instrukcji i obecność pikseli. Kopie obrazów
muszą pozostawać w paczce; symlinki i wyjścia poza katalog są odrzucane.
Nowy eksport nie zmienia historycznego doświadczenia ani raportu wykonania.

Rzeczywista próba wektorowa: 2166 tokenów, 2132 zamaskowane, 34 nadzorowane,
468 tokenów obrazu, tensor pikseli 1872×1536. Usunięcie obrazu jest odrzucane.
Nie ładowano wag i nie inicjalizowano CUDA. Pierwsza próba ujawniła import
zależności aplikacji w izolowanym środowisku ML; usunięto to powiązanie,
zachowując oddzielne środowiska. Ponowny audyt przeszedł.

Pierwszy rzeczywisty cykl przyjął dwa przykłady z dwóch rodzin, odrzucił
trzy źródła bez zaakceptowanych rekordów train. Następny cykl użył obu
istniejących audytów bez powtórzenia pracy procesora multimodalnego.
To liczby nowego zbioru multimodalnego, nie suma wszystkich historycznych
zbiorów tekstowych i zestawów egzaminacyjnych.

Próg 200 train / 25 validation / 50 test pozostaje niezmieniony. Potrzebne
są szersze dane, rejestr oddzielnych sprawdzianów oraz trener całego zbioru
z porównaniem bazy i adaptera. Osobna ocena musi poprzedzać wdrożenie.

Prywatny stan: `ai-company-workspaces/learning-autopilot/state.json`.
Właściciel może odczytać ograniczone podsumowanie przez
`GET /api/learning/status`; odpowiedź nie zawiera ścieżek, promptów ani wyników.
Pole `fresh` oznacza aktualność raportu do 15 minut, nie dowód życia procesu.
Sam odczyt niczego nie uruchamia. Endpoint będzie dostępny po załadowaniu
nowej wersji aplikacji.

Szablony harmonogramu użytkownika są w `config/systemd/`: cykl co pięć minut,
CPU do dwóch rdzeni, pamięć do 4 GiB, limit czasu sześć minut, bez dostępu
do GPU, sieci IP i pulpitu. Timer zainstalowano i włączono 21.09.2026.
Odczyt systemd potwierdził wykonanie o 04:58:27 CEST, kod zakończenia 0
oraz aktywny timer oczekujący na następny cykl. Usługa typu oneshot pomiędzy
cyklami jest nieaktywna; nie oznacza to zatrzymania harmonogramu.
Jest to usługa użytkownika, działająca wraz z jego menedżerem systemd;
nie włączano linger ani dodatkowej usługi systemowej.
