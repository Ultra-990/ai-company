# Diagnostyka próbki odpowiedzi API

Pierwszy fragment `platform.integrations`, wynikający z
[przeglądu ogłoszeń 14.09.2026](UPWORK_MARKET_2026-09-14.md) — szczególnie
M1 (wiązanie WeWeb/Xano), a dalej mapowanie danych M2/M3/M8.
To rzeczywista analiza dostarczonej próbki, nie działająca integracja z tymi
platformami. Nie pobiera URL, nie używa poświadczeń, modeli ani runnera.

## W panelu

`/os/upwork` → zaloguj właściciela → Wczytaj zlecenia →
**Diagnostyka odpowiedzi API — bez sieci**.
Nie trzeba zapisywać projektu ani mieć paczki aplikacji. Wklej zanonimizowaną
próbkę JSON, zadeklarowany status HTTP i kontrakt pól. Przycisk przykładu
wypełnia formularz wyłącznie syntetycznymi danymi; nie wykonuje analizy.
Sprawdzenie jest osobnym kliknięciem. Wyczyść po zakończeniu.

Powiązania są zwykłym JSON-em:

```json
[
  {"name":"title","pointer":"/data/items/0/name","expected_type":"string","required":true,"nonempty":true},
  {"name":"amount","pointer":"/data/items/0/total","expected_type":"number"}
]
```

Ścieżki korzystają z reprezentacji tekstowej
[JSON Pointer, RFC 6901](https://www.rfc-editor.org/info/rfc6901/), nie JSONPath:
indeks tablicy od zera, pusty pointer wskazuje dokument, `/` klucz pusty,
`~1` w nazwie oznacza slash, `~0` tyldę. Nie ma wildcard, wyrażeń, eval,
fragmentów URI ani odczytu plików hosta. Limity aplikacji dodatkowo
wykluczają znaki kontrolne i więcej niż 16 poziomów.

Typy: string, number, integer, boolean, object, array, null. Number przyjmuje
integer, ale bool nie jest liczbą. Tekst `"2576"` nie jest liczbą 2576.
Brak pola różni się od istniejącego null. required=false dla brakującego
pola zwraca ostrzeżenie, nie pełne zaliczenie. nonempty sprawdza null,
pusty tekst, listę lub obiekt; 0 i false nie są pustą wartością.

## API i granice dowodu

`POST /api/upwork-orders/contract-probe` z polami:

- response_text: tekst odpowiedzi JSON, do 32 KiB UTF-8;
- observed_status i expected_status: liczby całkowite 100–599;
- bindings: 1–12 powiązań o unikalnych nazwach; pola jak powyżej.

Całe żądanie ma limit 96 KiB sprawdzany strumieniowo, również bez Content-Length.
Powtórzone klucze JSON, nieprawidłowa składnia, NaN/Infinity, liczby poza
bezpiecznym zakresem ±2^53 i nadmierne zagnieżdżenie są odrzucane.
Niepoprawna próbka wewnętrzna jest wynikiem diagnostycznym failed; wadliwy
kontrakt/envelope daje 422 bez treści wejścia w błędzie, za duże żądanie 413.
Brak sesji daje 401, niewłaściwa rola 403. Sesja cookie wymaga istniejącej
ochrony CSRF. Schemat żądania dostępny w OpenAPI.

Wynik api-contract-probe.v1 zawiera checksumę próbki, statusy kontroli,
typy pól i wskazówki. Nie zawiera wartości z odpowiedzi API ani jej pełnej
treści. Nazwy i pointery pochodzą z kontraktu właściciela; także do nich
nie wpisuj sekretów. Nie wykrywamy automatycznie wszystkich danych wrażliwych.

Zgodna próbka nie potwierdza działającego połączenia, uprawnień, CORS,
renderowania UI, retry, deduplikacji ani braku błędów w innych odpowiedziach.
Zadeklarowany status HTTP nie jest zweryfikowanym statusem serwera.
release_evidence, network_used, model_used i application_executed pozostają false.
Wyniku nie można użyć jako TEST_RESULT do pominięcia bramki wydania.

Nie zapisujemy próbki, nowych projektów, artefaktów, delegacji ani statusów.
Istniejący audyt HTTP może zapisać fakt autoryzowanego POST i ścieżkę,
nie jego ciało. Formularz nie używa localStorage/sessionStorage. Czyszczenie,
zmiana wejścia i pagehide unieważniają wynik oraz przerywają oczekujący odczyt;
przerwanie przeglądarki nie cofa analizy już wykonanej przez serwer.

## Następne etapy, nie wdrożone przez tę zmianę

Transport z ograniczeniami i dozwolonymi hostami, izolowane poświadczenia,
kontrolowane testy sandbox dostawców, trwała deduplikacja operacji,
API POST/webhooki, harmonogram i jawne dopuszczenie zewnętrznych zapisów.
Nie uruchamiamy ich na koncie klienta ani sprzęcie wynajmujących.

Testy: `tests/test_api_contract_probe.py`, `node tests/test_api_contract_probe.cjs`.
Wyłącznie fikstury, izolowana baza i symulowany DOM; brak pilota prawdziwej
integracji i przeglądarki. Nie powstał kolejny automatyczny scraper Upwork.
