# Osobne panele, konta klientów i opłacony dostęp

Wymaganie właściciela z 2026-09-12. **Plan rozbudowy, nie wdrożona funkcja**.
Nie uruchomiono płatności, rejestracji, wysyłki e-mail ani publicznego serwera.

## Stan istniejący

- `/os` i `/os/work`: wewnętrzne zarządzanie właściciela z Owner API Token.
- `/client`: klient widzi tylko jawnie opublikowany podgląd konkretnego projektu
  przez czasowy, odwoływalny kod. To nie konto z hasłem i nie potwierdzenie wpłaty.
- `app/client_main.py`: osobna powierzchnia ASGI bez endpointów zarządzania.
  Nie wystawiać `app.main:app` do internetu; istnieją starsze wewnętrzne odczyty.

## Docelowy podział

Właściciel: agenci, delegacje, zasoby, koszty, pełne zlecenia, decyzje i audyt.
Klient: własne zamówienia, uzgodniony zakres, materiały, postęp przeznaczony
dla niego, wiadomości, poprawki, odbiór i status płatności. Żadnego dostępu do
innych klientów, sekretów, surowych instrukcji agentów ani infrastruktury.

Oddzielne strony/aplikacje to tylko część granicy. Każdy endpoint sprawdza
tożsamość i przynależność obiektu po stronie serwera. Podanie cudzego ID lub
tokena publikacji nie może nadawać uprawnień właściciela ani konta klienta.

## Kolejność implementacji

1. Konto klienta, weryfikacja adresu, hasło przechowywane wyłącznie jako
   odpowiedni hash, odzyskiwanie dostępu i ochrona prób logowania.
2. Wygasające/odwoływalne sesje, bezpieczne ciasteczka, ochrona CSRF i audyt.
   Produkcyjnie TLS. Oddzielny zakres sesji klienta i właściciela; właściciel
   docelowo MFA. Nie zastępować hasła stałym tokenem wklejanym do panelu.
3. Powiązanie klient → zamówienie → projekt → jawnie dostępne materiały.
   Testy izolacji dwóch klientów przy każdej operacji.
4. Produkt/usługa, ustalony zakres i limit kosztu. Utworzenie konta lub zapłata
   nie pozwala na dowolne narzędzia, nieograniczoną inferencję ani publikację.
5. Integracja wybranego operatora najpierw testowo. Dostęp po wiarygodnym,
   zweryfikowanym zdarzeniu serwerowym; nie po wejściu na stronę „sukces”.
   Kwota, waluta i zamówienie muszą odpowiadać zapisanej ofercie. Obsłużyć
   ponowienia, kolejność zdarzeń, błędy, anulowanie i zwroty bez podwójnego nadania.
6. Uprawnienie do konkretnej usługi przypisane kontu automatycznie. Opcjonalny
   jednorazowy kod aktywacji nie jest tokenem właściciela ani dowodem wpłaty.
   Wygasanie dotyczy kupionej usługi; klient zachowuje dostęp do historii i wsparcia.
7. Osobne odbiory: kontrola techniczna właściciela i decyzja klienta o dostawie.
   Zgoda klienta nie podnosi samodzielnie uprawnień agentów.
8. Próba całego procesu w sandboxie płatności, odzyskiwania konta, rozdzielenia
   klientów i odwołania dostępu przed uruchomieniem publicznym.

## Decyzje potrzebne przed integracją płatności

- Co jest sprzedawane: indywidualnie wyceniane zlecenie, abonament czy kredyty?
- Operator płatności, waluta i podmiot sprzedający; bez zakładania kont i wydatków
  przez agenta. Dla płatności wewnątrz marketplace potrzebna osobna integracja
  i sprawdzenie bieżących zasad, nie założenie przekierowania klienta poza platformę.
- Zatwierdzone limity realizacji i zasoby, które nie kolidują z wynajmem Vast.ai.

Do wyboru tych zasad nie należy aktywować prawdziwych obciążeń ani nadawać
klientowi dostępu do istniejącego centrum właściciela. Istniejący portal
publikacji może pozostać funkcją pomocniczą, ale nie udaje płatnego konta.
