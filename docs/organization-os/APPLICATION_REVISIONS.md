# Poprawki aplikacji przez lokalnego Qwen

Jeśli poprawka wynika z błędu testów, można zamiast formularza uruchomić
[automatyczny cykl testów i napraw](AUTOMATIC_QUALITY.md). Poniższy formularz
pozostaje dostępny dla uwag właściciela i zmian niewykrywanych przez testy.

## Obsługa

W `/os/build`, przy wyniku testów paczki, wybierz **Zgłoś poprawkę do tej
wersji**. Podaj opis zmiany, oczekiwany rezultat/test odbioru oraz dowody lub
kroki odtworzenia. Zaznacz zgodę na skierowanie wyniku do poprawy. Opcjonalny
checkbox uruchamia testy kontenerowe nowej paczki po zakończeniu generowania.
Przycisk **Zgłoś i uruchom poprawkę Qwen** zapisuje żądanie, następnie uruchamia
jedną próbę modelu. Samo otwarcie formularza niczego nie zmienia.

Dotyczy najnowszej paczki wygenerowanej przez Qwen, której próba oczekuje na
odbiór właściciela. Już zaakceptowanego, zamkniętego zadania nie otwieramy
po cichu: zmiany rozwojowe prowadzi się jako osobne zadanie. Formularz nie
służy też do ponownego odrzucania wcześniej ręcznie odrzuconej próby.

W **Historii poprawek** kliknij **Wczytaj / odśwież poprawki**. Widać paczkę
bazową, opis, oczekiwanie, stan Qwen, nową paczkę i stan testów. Zgłoszenie
zapisane przed utratą połączenia można kontynuować przyciskiem uruchomienia.
Nie trzeba ponownie wypełniać formularza. Nieudana lub niepewna inferencja
wymaga kontroli istniejącej historii modelu w Centrum realizacji; nie ma
nieograniczonej automatycznej pętli ponowień.

## Spójność i wykonanie

- `POST /api/application-revisions` wymaga właściciela, UUID, task_id,
  package_id, checksumy, opisu, oczekiwania, dowodów i confirm_revision=true.
  Nie przyjmuje poleceń terminala, obrazu, modelu ani adresu providera.
- W jednej transakcji weryfikuje źródła i pochodzenie Qwen, odrzuca bieżącą
  próbę istniejącym mechanizmem odbioru, tworzy instrukcję poprawki i wpis
  kolejki LocalInference oraz niezmienny raport zgłoszenia (Artifact).
  Błąd, np. brak kontekstu, wycofuje także zmianę stanu zadania.
- Identyczne ponowienie UUID zwraca to samo zgłoszenie. Zmiana treści pod tym
  samym UUID jest odrzucana. Stara paczka nie jest nadpisywana; kolejna ma
  nowe ID, checksumę, próbę i raport pochodzenia.
- Qwen dostaje bieżący opis zadania, przyczynę odrzucenia, oczekiwany rezultat
  i pełny poprzedni wynik ze źródłami. Nie pobiera automatycznie wszystkich
  logów: w zgłoszeniu trzeba zawrzeć istotny błąd lub sposób odtworzenia.
- `POST /api/application-revisions/{id}/run` korzysta z istniejącego limitu
  jednego modelu, kontroli aktualności instrukcji, przypiętych wag/modelu i
  deadline. Profil poprawki kodu zwiększa kontekst o 16384, maksymalnie do
  32768, aby pomieścić stare źródła bez ich obcinania. Limit wyjścia pozostaje
  4096 tokenów i 32000 znaków; nadal może być potrzebny mniejszy zakres.
  Nie jest to trening modelu ani uruchamianie wielu agentów naraz.
- Gdy właściciel zaznaczy auto_test, nowe źródła trafiają do niezmienionego
  ograniczonego runnera Python web. UUID testu jest deterministycznie związany
  ze zgłoszeniem: ponowienie żądania nie wykonuje drugi raz modelu ani testów.
  Jeśli zapisano model, ale przerwano przed testami, ponowienie kończy ten krok.
- Zaliczenie testów nie oznacza poprawności całego zlecenia. Nowa próba
  pozostaje `awaiting_review`; właściciel sprawdza wymagany scenariusz w
  podglądzie. Nie ma publikacji ani automatycznej akceptacji klienta.
- Stan i źródła są w dotychczasowej bazie, bez nowej tabeli i równoległej
  roadmapy. Klient nie ma dostępu do endpointów ani plików panelu poprawek.

## Testy

`tests/test_application_revisions.py`: wersjonowanie, idempotencja, uprawnienia,
nieaktualna paczka, atomowy rollback, błędny JSON modelu, testy wykonywane
tylko raz i brak automatycznego zakończenia zadania. Zwykłe testy używają atrap.

`scripts/check_work_browser.py`: formularz, retry po 503 z tym samym UUID,
wyświetlanie opisu jako tekstu, link nowej paczki i czyszczenie po wylogowaniu.

`scripts/check_revision_pilot.py`: jawna próba prawdziwego Qwen i Dockera na
kopii źródeł kalkulatora w osobnej testowej bazie. Nie modyfikuje działającego
zadania 45 ani paczki 5. Raport i ZIP powstają w oddzielnym katalogu
`/home/marcin/ai-company-workspaces/revision-pilot-*`. Źródła starej wersji są
testowym wejściem; tylko poprawkę generuje prawdziwy model. Próba ta obejmuje
testy jednostkowe/HTTP/izolacji i kontrolę tekstu UI, nie pełny wizualny odbiór
nowego interfejsu. Wyniki konkretnych przebiegów są w WORK_LOG.md.
