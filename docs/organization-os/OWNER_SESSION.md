# Wspólne logowanie właściciela

Wdrożenie: 2026-09-13. W górnym pasku `/os` kliknij **Zaloguj właściciela**,
wpisz skonfigurowany token i zatwierdź. Kolejne panele korzystają z jednej
sesji bez ponownego kopiowania tokena.

## Zakres interfejsu

- Pulpit i Spatial pokazują stan sesji oraz logowanie/wylogowanie.
- Realizacja, Budowa i testy oraz Historia klientów automatycznie otwierają
  odczyt danych po rozpoznaniu sesji.
- Odbiór nadal wymaga wskazania ID zadania, a publikacja — projektu i treści.
  Sesja usuwa tylko konieczność wpisywania tokena; nie zatwierdza żadnej decyzji.
- `/os/client-preview` używa sesji właściciela. `/client` jej nie wykorzystuje:
  klient musi podać osobny kod udostępnionego projektu. Lokalna strona klienta
  ma widoczny odnośnik do właściwego podglądu właściciela.
- Dawne pola Bearer pozostają trybem jednorazowym, jeśli nie zalogowano sesji.
  Starszy archiwalny pulpit nie został przebudowany na sesje.
- Centrum pomocy opisuje nowy sposób logowania, ale samo pozostaje publiczną
  instrukcją bez potrzeby sprawdzania sesji.

## Czas życia i wylogowanie

Sesja ma bezwzględny limit 8 godzin. Wylogowanie usuwa ją po stronie serwera.
Wylogowanie w jednej karcie informuje pozostałe przez BroadcastChannel;
niezależnie od komunikacji kart API egzekwuje cofnięty dostęp. Na innym
urządzeniu następne żądanie nie uzyska dostępu. Operacja przyjęta przed
wylogowaniem może się zakończyć — wylogowanie nie jest jej anulowaniem.

Zmiana tokena Owner/Worker i restart procesu API unieważniają sesje.
Podczas rozwoju `uvicorn --reload` także powoduje ponowne logowanie po
przeładowaniu kodu. Sesje są w pamięci jednego procesu, najwyżej 32 aktywne;
nie jest to współdzielony magazyn dla wielu workerów czy klastrów.
Przy wylogowaniu lub wygaśnięciu strona przeładowuje się, usuwając dane i
niezapisane formularze z karty. Zapisz pracę przed świadomym wylogowaniem.

## Bezpieczeństwo

- Token API wysyłany tylko podczas logowania; nie wraca w odpowiedzi i nie
  trafia do cookie/localStorage/sessionStorage. Skrypty API nadal mogą używać
  dotychczasowego Bearer; błędny jawny nagłówek nie przechodzi na sesję.
- Cookie `ai_company_owner`: losowe 256 bitów, HttpOnly, SameSite=Strict,
  host-only, Path=/api, limit 8 h. Serwer przechowuje hash identyfikatora,
  CSRF, origin, fingerprint konfiguracji tokenów i czas wygaśnięcia.
- HTTPS używa Secure. HTTP dopuszczono wyłącznie dla kanonicznych nazw
  localhost/127.0.0.1/::1. Adresy localhost i 127.0.0.1 są różnymi originami.
  Nie wystawiono serwera ani nie zmieniono sieci/HTTPS hosta.
- Każde żądanie cookie wymaga X-Owner-Origin zgodnego z adresem aplikacji
  i zapisaną sesją. Jawny Origin nie może być inny ani null. Mutacje wymagają
  dodatkowo prawdziwego Origin i X-Owner-CSRF. Obce Sec-Fetch-Site są odrzucane.
  Brak polityki CORS zezwalającej innym stronom na te nagłówki.
- JS jawnie korzysta z OwnerSession.fetch tylko w panelach właściciela.
  Nie nadpisuje globalnego fetch, nie wysyła sesji na zewnętrzne URL ani do
  `/api/client/`. Uprawnienia workerów i klientów pozostają oddzielne.
- Osobna aplikacja klienta nie rejestruje owner-session API i nie udostępnia
  jego zasobów JS/CSS. Opaque preview iframe nie spełnia kontroli Origin.
- HttpOnly nie usuwa wszystkich skutków XSS. Utrzymujemy CSP, escapowanie
  danych, izolację generowanego kodu i autoryzację każdego działania.

API: POST `/api/owner-session` — wymagany Bearer właściciela i origin,
GET — sprawdzenie cookie/CSRF/wygaśnięcia, DELETE — unieważnienie z CSRF.
Odpowiedzi są no-store. Logowanie nie zapisuje automatycznie statusów zadań.

## Weryfikacja

Lokalny Qwen przygotował listę ryzyk i testów (19.65 s; 356 tokenów wejścia,
766 wyjścia). Nie generował ani nie wykonywał kodu bezpieczeństwa na hoście.
Wnioski sprawdzono w testach, nie potraktowano odpowiedzi jako odbioru.

`test_owner_sessions.py`: cookie, Origin/CSRF, ról nie można zamieniać,
błędny Bearer, wylogowanie/replay, TTL, restart, rotacja, HTTPS i limit sesji.
`check_work_browser.py`: jedno logowanie, przejścia między panelami, ukryte
pola tokena, odczyty bez Bearer, wylogowanie i brak tokena w storage.
`check_client_browser.py`: dotychczasowy dostęp klienta i podgląd właściciela.
Testy używają sztucznych danych i atrap API; wyniki w WORK_LOG.md.
