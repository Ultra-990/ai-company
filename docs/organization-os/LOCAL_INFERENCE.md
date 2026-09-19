# Rzeczywisty tekstowy wykonawca Qwen

Stan: 2026-09-13. Wynajem Vast.ai zakończony według potwierdzenia właściciela.
Wykonawca korzysta z istniejących zadań, delegacji, instrukcji i odbiorów.
To nie jest jeszcze autonomiczny runner kodu, trening modelu ani system
automatycznej sprzedaży. Każde uruchomienie jest osobną akcją właściciela.

Rozszerzenie z tego samego dnia: [fabryka aplikacji](APPLICATION_FACTORY.md)
dodaje dla roli wykonawcy profil `python-web-v1`, zapis źródeł i osobny runner
kontenerowy. Model nadal nie ma narzędzi hosta; kod wykonuje ograniczony kontener
po jawnej zgodzie, nigdy sam adapter Ollamy.

## Obsługa

Analityk [zlecenia Upwork](UPWORK.md) używa teraz osobnego, walidowanego
kontraktu JSON i limitu najwyżej 1536 tokenów. Nie zmienia to profilu wykonawcy
kodu ani zwykłych tekstowych zadań. Wspólna sesja właściciela pozwala przechodzić
między panelami bez ponownego podawania tokena; logowanie hasłem pozostaje do wdrożenia.

1. Otwórz `http://127.0.0.1:8000/os/work` i połącz tokenem właściciela.
2. Wybierz projekt. Przydziel zespół, jeśli nie ma jeszcze delegacji.
3. Przy gotowym zadaniu wybierz **Przygotuj instrukcję**. Sprawdź zakres,
   poprzedniki i kryteria. Samo otwarcie instrukcji nie uruchamia modelu.
4. Wybierz **Uruchom lokalny Qwen — wynik do odbioru**. Transport ma limit
   180 sekund, interfejs czeka nieco dłużej. Zamknięcie strony nie jest
   potwierdzeniem zatrzymania modelu; nie klikaj ponownie po błędzie sieci.
5. Sekcja **Lokalny Qwen** → **Odśwież** pokazuje ostatnie 30 przebiegów,
   identyfikator zadania, model, czas, wynik lub powód błędu. Wybierz projekt
   i **Odbierz wynik** przy zadaniu, aby przeczytać pełną odpowiedź i podjąć
   decyzję dotyczącą konkretnej wersji. Można też użyć `/os/review` i ID zadania.
6. Wynik pozostaje `awaiting_review`, zadanie `in_progress`. Nie ma
   automatycznego zaliczenia testów, przyrostu procentu ani akceptacji.
   Kolejny etap odblokowuje dopiero odbiór poprzedniego.

Pilotaż w tej instalacji: projekt **#4 „Pilotaż Qwen — standard odbioru działu
jakości”**, zadanie **#41**, wykonanie **#1**, próba zadania **#2**. Zapisano
specyfikację wygenerowaną przez model; ocena merytoryczna nadal do wykonania.

## Limity i gwarancje implementacji

- Model `qwen3.8:27b`, SHA-256 tagu przypięty w `config/local_inference.json`.
  To zastana lokalna nazwa, nie potwierdzenie oficjalnej wersji dostawcy.
  Zmiana pliku/tagu wymaga uzgodnienia konfiguracji; nie pobieramy modeli.
- Stały adres `127.0.0.1:11434`. Brak dowolnych URL, proxy środowiskowych,
  kluczy chmurowych, przekierowań oraz dostępu modelu do narzędzi.
- Jeden zarezerwowany slot aplikacji; maksymalnie 50 oczekujących/aktywnych
  wpisów. To nie ogranicza niezależnych żądań innych klientów Ollamy.
- Kontekst do 16384 tokenów, odpowiedź do 4096, 8 wątków CPU, temperatura 0.2.
  Budżet wejścia konserwatywnie sprawdzany liczbą bajtów UTF-8; instrukcja nie
  jest po cichu przycinana. Długi zakres trzeba podzielić.
- `stream:true`, `think:false`, `keep_alive:0`. W bazie zapisujemy tylko
  odpowiedź tekstową, nie wewnętrzny tok rozumowania. Odrzucamy ucięty wynik
  (`done_reason` inny niż `stop`), wywołania narzędzi i nieprawidłowy strumień.
- Osobny własny proces transportu ma twardy deadline klienta. Zamknięcie
  połączenia nie dowodzi zakończenia pracy demona; nie zabijamy Ollamy.
- Przed i po odpowiedzi kontrolowana jest aktualność instrukcji, modelu,
  polityki i Emergency Stop. Zmieniony zakres nie dostaje starego wyniku.
- Transakcja SQLite rezerwuje slot, ale nie trwa podczas generowania.
  `local_inference_runs` przechowuje pochodzenie; TaskAttempt i Artifact REPORT
  wiążą SHA-256 instrukcji, odpowiedzi, model i metryki z odbiorem.
- Brak wykonywania wygenerowanego kodu, publikacji, opłat i automatycznego
  sterowania agentami. Profile kierowników/wykonawców to role z delegacjami;
  tekst wykonuje wspólny Qwen, nie 72 stale działające procesy.

## Błędy, ponowienia i odtwarzanie

Aktualizacja 14.09.2026: historia w `/os/work` domyślnie dotyczy wybranego
projektu. Można przełączyć na wszystkie projekty, wyświetlić wyłącznie
nierozstrzygnięte wpisy oraz pobrać starsze strony. API listy obsługuje
`project_id`, `attention_only` i kursor `before`; zwraca `attention_count`
dla całego wybranego zakresu oraz `next_cursor` (30 wpisów na stronę).
Nie zmienia statusów i nie kontaktuje się z modelem. Odczyt konfiguracji
`enabled` nie potwierdza wolnych zasobów ani zakończenia wynajmu Vast.ai.


Nie ma automatycznych ponowień. Ten sam UUID lub pakiet instrukcji wskazuje
ten sam przebieg, więc ponowne kliknięcie nie tworzy drugiej inferencji.

`failed` oznacza nieprzyjęty rezultat. `uncertain` oznacza brak pewności
zakończenia transportu i blokuje slot. Wybierz **Przygotuj ponowienie po
kontroli bezczynności**: API wymaga pustej listy modeli w `/api/ps`, zachowuje
historię błędu i ustawia `queued`. Dopiero osobny przycisk uruchamia model.
Maksymalnie trzy próby jednej instrukcji. Załadowany model, także cudzy,
powoduje odmowę; nie wyładowujemy go przymusowo.

Po przerwaniu procesu API wpis może pozostać `running`. Ten sam mechanizm
odzyskiwania wymaga dodatkowo upływu limitu transportu + 15 sekund oraz
braku innego trwającego przebiegu. Wynik spóźnionego procesu nie może zostać
przypisany do zmienionego stanu. Nie uruchamiaj restartów jako metody anulowania.

GET `/api/local-inference`, POST do tej ścieżki oraz `/{id}/run`, `/{id}/cancel`,
`/{id}/retry` są owner-only. Retry wymaga UUID `request_id` i `confirm:true`.
Oddzielna aplikacja klienta nie udostępnia tych tras. Token pozostaje w pamięci
karty. Rezultaty renderowane są jako tekst, nie HTML.

## Weryfikacja

Testy transportu, stanu, autoryzacji i retry używają atrap bez GPU oraz
izolowanych baz. `scripts/check_work_browser.py` sprawdza kliknięcia,
wiązanie instrukcji, historię, ręczne ponowienie bez startu oraz escapowanie;
API w przeglądarkowym teście jest symulowane.

Rzeczywisty pilotaż: krótka próba 16.144 s; pierwszy pełny przebieg odrzucony,
diagnostyka wykazała limit odpowiedzi 1536 tokenów. Po jawnym ponowieniu
z większym budżetem: 21.098 s, 769 tokenów wejścia, 1423 tokeny generowania,
`done_reason:stop`. `/api/ps` po zakończeniu zwróciło pustą listę modeli.
To pojedynczy pomiar, nie benchmark ani gwarancja szybkości/jakości.

Kontrakt transportu oparto na oficjalnych dokumentach
[Ollama Chat](https://docs.ollama.com/api/chat) i
[Ollama Tags](https://docs.ollama.com/api/tags).
