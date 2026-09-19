# Automatyczne testy i naprawa aplikacji

Opcjonalne rozszerzenie: [niezmienne przykłady wymagań HTTP](AUTOMATIC_ACCEPTANCE.md).
Przygotowanie planów wdrożone; wykonanie nowej ścieżki wyłączone do bezpiecznego
pilota po wynajmie. Dotychczasowe cykle bez planu pozostają bez zmian.

## Co działa

W `/os/build` przy najnowszej paczce Qwen wybierz **Testuj i napraw
automatycznie**. Potwierdzasz jeden cały cykl, nie każdą kolejną poprawkę.
Serwer wykonuje:

1. Testy tej wersji w izolowanym kontenerze.
2. Jeżeli wykryto błąd programu: zapis wyniku kontroli i skierowanie próby
   do poprawy, przekazanie logu oraz źródeł lokalnemu Qwenowi.
3. Zapis nowej paczki bez nadpisania poprzedniej.
4. Ponowne testy; w razie potrzeby drugą próbę naprawy.
5. Raport końcowy oraz odnośnik do wynikowej paczki i testów.

Jeśli pierwsze testy są poprawne, model nie jest uruchamiany. Cykl naprawia
wykryte błędy, a nie generuje zmian dla samego zwiększenia postępu. Nie zmienia
statusu na completed i nie udaje odbioru człowieka: automatyczne odrzucenia mają
reviewer_role=automated_qa, review_method=automatic_test_feedback. Po zaliczeniu
zestawu jest gotowy kandydat do przekazania, nie opublikowana aplikacja.

## Niezmienność kryteriów i granice

- Przy rozpoczęciu zapisuje się checksumę i treść `test_app.py` oraz profil
  testera. Qwen nie może usunąć ani zmienić bazowych testów, by uzyskać sukces.
  Zmienione testy są odrzucane przed uruchomieniem kolejnego kontenera, a model
  otrzymuje oryginał do przywrócenia. Błąd w samym zestawie wymaga osobnej oceny.
- Starsze cykle z `repair_decoder=locked-test-schema.v1`: schemat JSON
  przekazywany do Ollamy zawiera `const` z dokładną treścią bazowego testu.
  Nie polegamy wyłącznie na prośbie w prompcie. Odpowiedź modelu nie jest
  przepisywana przez serwer; późniejsza kontrola checksumy nadal odrzuca zmianę,
  również gdy dostawca zignoruje schemat. Schemat ma istniejący limit 16 KB;
  większy zestaw wymaga podziału zakresu. Stare cykle zachowują stary dekoder.
- Nowe cykle używają `python-web-repair-v1`: Qwen zwraca `changes` z pełną
  treścią 1–2 zmienionych, istniejących plików. Nie może zwrócić test_app.py,
  nowego pliku, usunięcia ani niezmienionej treści. System składa nową wersję
  w pamięci z poprawki i odrzuconej wersji powiązanej checksumą instrukcji.
  Nie zapisuje generowanego kodu do repozytorium ani nie wykonuje go na hoście.
  Kontrola oryginalnych testów, źródeł i aktualności zakresu nadal obowiązuje.
- Surowa odpowiedź ma osobny artefakt i checksumę. `metrics.assembly` wskazuje
  zmienione/zachowane pliki, sumę bazy i testów. Wynik TaskAttempt to kompletna
  złożona wersja, nie surowy JSON poprawki. Nieprawidłowa poprawka jest zapisywana
  jako dowód odrzucenia (`invalid_file_repair`), bez nowej paczki i próby zadania.
  Historia Qwen w Centrum realizacji pokazuje listę zmienionych plików i przyczynę
  odrzucenia. Ręczne zgłoszenia starszego API zachowują profil pełnych źródeł.
- Skrót raportu do modelu zaczyna się od `errors`, następnie stanu HTTP/testów
  i końcówki logu. Długa lista zaliczonych testów nie wypycha przyczyny błędu
  poza początek limitu kontekstu. Pełny raport pozostaje w PackageRun.
- Niezależny harness nadal sprawdza HTTP, brak ujawnienia źródeł i izolację.
  Bazowe testy nie są automatycznie pełną specyfikacją klienta. Cykl nie obejmuje
  jeszcze ogólnego odbioru wizualnego/przeglądarkowego ani dowolnych frameworków.
- Limit dwóch poprawek i trzech zestawów testów. Powtarzanie tych samych źródeł,
  wadliwy wynik modelu, zmieniona konfiguracja, nieaktualna próba, błąd sprzętu
  lub niepewne sprzątanie zatrzymują cykl z wyjaśnieniem. Nie dajemy modelowi
  uprawnień do naprawiania hosta, wyłączania izolacji ani restartu Dockera.
- Deadline 15 minut od utworzenia cyklu; przed operacją sprawdzany jest zapas
  na jej limit i sprzątanie. Stałe limity Qwen i runnera nie są zwiększane.
- Log programu jest niezaufanymi danymi dla diagnozy. Nie przyznaje uprawnień,
  nie zmienia zakresu ani kryteriów i nie jest poleceniem terminala.
- Kod generowany działa wyłącznie w dotychczasowych kontenerach, nie na hoście.
  Nie jest to izolacja dla celowo wrogich programów. Nie ma płatnych API.

## Historia, przerwanie i wznowienie

W panelu **Automatyczna kontrola i naprawa** kliknij **Odśwież cykle kontroli**.
Każdy test i naprawa ma własny identyfikator. Cykle są przechowywane jako
wersjonowane raporty Artifact; zadania, źródła, inferencje i testy pozostają
w dotychczasowych tabelach. Bez nowej roadmapy ani duplikowania zadań.

Żądanie startu i operacje składowe mają deterministyczne UUID. Ponowienie tego
samego cyklu odczytuje już zakończone operacje, zamiast ponownie odrzucać próbę
lub wykonywać model. Blokada per zadanie działa między procesami na tym hoście;
po awarii procesu zwalnia ją system. Istniejące niepewne sloty Qwen/runnera nadal
wymagają bezpiecznego uzgodnienia i nie są pomijane podczas wznowienia.

Cykl wykonuje się na serwerze w ramach ograniczonego żądania, bez dodatkowego
demona. Zamknięcie karty nie potwierdza anulowania. Restart serwera może wymagać
ręcznego wznowienia zapisanego cyklu, a po deadline nowego zgłoszenia. Nie jest
to jeszcze stały autonomiczny scheduler. Zakończony raport jest historycznym
dowodem: wydanie ponownie sprawdza aktualną wersję i decyzje.

**Zatrzymaj po bieżącej operacji** zapisuje prośbę o przerwanie cyklu. Nie zabija
modelu ani kontenera w trakcie pracy; blokuje następny krok. Można też wylogować
panel, co czyści token i widoki, ale samo w sobie nie anuluje wykonania.

API owner-only, bez tras w aplikacji klienta:

- `POST /api/application-quality`: UUID, task_id, package_id, checksum,
  max_repairs 1–2, confirm_automatic_repairs=true.
- `POST /api/application-quality/{id}/run`: wykonanie / wznowienie cyklu.
- `POST /api/application-quality/{id}/stop`: zatrzymanie po bieżącej operacji.
- `GET /api/application-quality`: ostatnie 20 cykli wraz z krokami i wynikiem.

## Dowód działania

`tests/test_application_quality.py` sprawdza naprawę po błędzie, ponowne testy,
idempotencję, awarię po zapisaniu wyniku modelu, ochronę testów, uprawnienia,
limit, deadline, brak postępu, zmianę polityki, przerwanie i współbieżność.
Zwykłe testy używają atrap i osobnych baz.

`scripts/check_revision_pilot.py --automatic` uruchamia prawdziwego Qwena oraz
kontenery na celowo zepsutej kopii kalkulatora: zamiast mnożenia jest dodawanie.
Nie modyfikuje produkcyjnego zadania 45 ani paczki 5. Pilot wymaga:
niezaliczonego pierwszego testu → poprawki modelu → zaliczonego kolejnego testu,
identycznego bazowego pliku testów i niezależnego wywołania HTTP z wynikiem 2576.
Raporty i ZIP znajdują się w `ai-company-workspaces/automatic-quality-pilot-*`.

Przebieg 2026-09-13 zaliczony: jedna naprawa Qwen (30.892 s), oba kontenery
posprzątane, dodatkowy HTTP 8 × 322 = 2576. To dowód tego scenariusza,
nie gwarancja naprawienia wszystkich przyszłych błędów.
