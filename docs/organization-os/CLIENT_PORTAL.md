# Panel klienta — pierwsza wersja

Nowe wymaganie: osobne konta z hasłem oraz dostęp do opłaconych usług.
[Plan kont i płatności](CLIENT_ACCOUNTS_PLAN.md) opisuje kolejne etapy.
Obecne kody publikacji nie są kontami ani potwierdzeniem zapłaty.

## Co działa

Lokalny podgląd jest dostępny pod `/client`. Klient podaje osobny kod,
który udostępnia jedną świadomie przygotowaną publikację:

- publiczną nazwę i opis projektu;
- postęp oraz status opublikowane przez wykonawcę;
- interaktywny workflow: etapy, zakres, opublikowane rezultaty, kryteria i uwagi;
- menu po lewej: Workflow, Materiały, Do odbioru, plus wybór etapów;
- czas aktualizacji oraz termin ważności dostępu.

Panel nie ma uprawnień do wykonywania zadań, zmiany postępu, technicznego odbioru wyników,
pliku bazy, kosztów, sekretów, agentów ani automatycznego pobierania kodu.
Umożliwia odczyt publikacji, zapis decyzji o udostępnionym etapie i ograniczone zgłaszanie zdarzeń
nawigacyjnych do historii właściciela. Czat, faktury, płatności, upload klienta i jego podpisany
odbiór są przyszłymi funkcjami, nie działającymi atrapami.

## Gdzie wejść jako właściciel

- `/os/clients` — historia udostępnień, publikacji, aktywności i decyzji klientów.
  Wpisz token właściciela, ten sam co w Centrum realizacji.
- `/os/client-preview` — **podgląd panelu klienta dla właściciela**, nie wymaga
  kodu klienta. Po tokenie właściciela wybierz publikację (30 najnowszych;
  starsze otwieraj z historii, link zawiera tylko ID `?share=...`, nigdy token).
- Przycisk **Pokaż przykład panelu klienta — bez logowania** pokazuje wyraźnie
  oznaczone demonstracyjne dane w przeglądarce. Nic nie tworzy w bazie.
- W Spatial oba skróty są pod górnym paskiem oraz w menu Właściciel.
  Historia zawiera też link do podglądu wybranej publikacji.

`/client` jest wejściem odbiorcy. „Kod od wykonawcy” oznacza osobny czasowy
kod wygenerowany przez właściciela podczas publikacji, nie token właściciela.
Podgląd właściciela nie zapisuje zdarzeń klienta i nie pozwala wysłać decyzji
w jego imieniu. Strona podglądu nie jest dostępna w osobnym `app.client_main`.

## Publikacja przez właściciela

1. W `/os` otwórz menu właściciela → **Udostępnienia dla klientów**.
2. Wpisz token właściciela, ID istniejącego projektu i treść dla klienta.
   Nazwa i opis nie są automatycznie kopiowane z wewnętrznego projektu.
3. Podaj postęp, status, następny krok i **Dodaj etap**. Formularz etapu:
   nazwa, co powstaje, udostępniony rezultat, kryteria odbioru oraz uwagi.
   Statusy: `planned`, `in_progress`, `review`, `completed`, `blocked`.
   Do 30 etapów; opisy do 2000 znaków, rezultat do 6000, maks. 12 kryteriów
   po 500 znaków. Klient widzi tylko te teksty, nie wewnętrzne artefakty.
4. Potwierdź treść i utwórz dostęp ważny od 1 do 30 dni (domyślnie 7).
   Kod pojawia się tylko w odpowiedzi na utworzenie. Zachowaj go bezpiecznie,
   nie w repozytorium ani adresie URL.
5. Klient wpisuje kod w `/client`. Aktualizacje są pobierane co 30 sekund
   na widocznej karcie i na żądanie.
6. W panelu właściciela wyświetl listę dostępów projektu. ID udostępnienia
   pozwala **Wczytać publikację do edycji**, opublikować zmianę albo cofnąć dostęp.
7. **Historia projektów i aktywność klientów** (`/os/clients`) pokazuje
   udostępnienia i wcześniejsze wersje oraz ograniczone zdarzenia nawigacji.

Aktualizacja zastępuje cały publiczny opis i listę etapów, ale nie odnawia
kodu ani daty wygaśnięcia. Pusta lista usuwa poprzednio opublikowane etapy.
Wcześniejsze wersje są odtąd zachowane. Dla publikacji sprzed wdrożenia historii
zapisujemy stan bazowy przy pierwszej zmianie, nie wymyślamy przeszłych zdarzeń.
Zamknięcie formularza czyści widoczny kod, lecz nie cofa wydanego dostępu.
Nowe udostępnienie nie cofa poprzednich — w razie rotacji cofnij poprzednie ID.

## API i zapis

- `POST /api/client-shares` — właściciel tworzy dostęp; zwraca jednorazowo kod.
- `GET /api/client-shares?project_id=...` — lista metadanych bez kodów i hashy.
- `PUT /api/client-shares/{id}` — właściciel publikuje aktualizację.
- `GET /api/client-shares/{id}` — właściciel odczytuje publikację do edycji, bez kodu.
- `GET /api/client-history?before=...` — właściciel: 30 udostępnień na stronę.
- `GET /api/client-shares/{id}/history?before_revision=...&before_activity=...`
  — właściciel: 30 wersji oraz 50 zdarzeń z osobnymi kursorami kolejnych stron.
- `POST /api/client-shares/{id}/revoke` — właściciel cofa dostęp.
- `GET /api/client/overview` — kod klienta w nagłówku Bearer, bez wybierania
  projektu lub klienta w parametrach. Zakres wynika z kodu, nie z żądania.
- `POST /api/client/activity` — kod klienta, zamknięta lista zdarzeń,
  indeks etapu oraz data wersji publikacji; żadnych swobodnych treści użytkownika.
- `POST /api/client/feedback` — świadoma decyzja o wersji etapu.
- `GET /api/client/feedback?before=...` — historia decyzji dla kodu, po 30 wpisów.
- `GET /api/client-shares/{id}/feedback?before=...` — ta historia dla właściciela.
- `POST /api/client-feedback/{id}/acknowledge` — odpowiedź właściciela.

## Decyzja klienta i odpowiedź wykonawcy

Klient wybiera etap ze statusem `review`, sprawdza materiał i wybiera
akceptację lub prośbę o poprawki. Wymagane są komentarz (3–4000 znaków)
i jawne potwierdzenie. Akceptacja wymaga niepustego opublikowanego rezultatu.
Posiadanie kodu nie potwierdza tożsamości osoby i nie jest podpisem elektronicznym.

Serwer wiąże decyzję z SHA-256 treści i czasu publikacji, indeksem etapu oraz
zachowanym snapshotem. Zmiana publikacji przed wysłaniem daje 409: trzeba
sprawdzić nową wersję. Jedna decyzja na etap/wydanie/kod; powtórzenie tego samego
UUID i treści nie tworzy duplikatu. Inna treść pod tym UUID jest odrzucana.
Wycofany lub wygasły kod nie może odczytywać ani wysyłać decyzji.

W historii właściciel może odpowiedzieć (3–2000 znaków). Odpowiedź i data
potwierdzenia są zachowane, nie nadpisywane. Klient widzi je przy etapie oraz
w historii swoich decyzji. Historyczne decyzje pozostają przy poprzedniej
wersji; nowa publikacja pozwala na nowy odbiór. Addytywna tabela
`client_stage_feedback` powstaje przez istniejące `Base.metadata.create_all`.

Żaden z tych kroków nie uruchamia agentów, nie zmienia Task, jego postępu,
zgody technicznej ani praw wykonawcy. Poprawki trzeba osobno zaplanować
i delegować. Komentarze są przechowywane w tabeli decyzji, nie w logach;
audyt zapisuje identyfikatory, wersję i rodzaj decyzji, bez kodów i komentarzy.

Nowa, addytywna tabela `client_portal_shares` jest rejestrowana w metadata
SQLAlchemy i tworzona przez istniejące `Base.metadata.create_all` podczas
startu aplikacji. Starych tabel ani ich rekordów nie modyfikuje.
Nie dodano zewnętrznych usług ani zależności instalowanych w tym etapie.
Dodano `client_publication_revisions` i `client_portal_activity` przez ten sam
mechanizm. Nowe/zmienione publikacje i ich wersje zapisują się transakcyjnie.

## Workflow i historia aktywności

Etapy mają opcjonalny stabilny `key`, żeby odświeżenie lub zmiana kolejności
nie przestawiały aktualnego wyboru. Puste klucze starych publikacji mają
fallback indeks/nazwa; ich brak nie uniemożliwia wyświetlenia. Stare snapshoty
bez opisów nadal działają, z jawnym komunikatem o nieopublikowanym materiale.

Karty są połączone w kolejności publikacji, bez automatycznego zgadywania
zależności wewnętrznych. Postęp jest osobnym procentem opublikowanym przez
właściciela; licznik ukończonych etapów nie zmienia go. Materiały to teksty
lub opisy rezultatów, nie zrzuty wykonania ani uruchamiana aplikacja. Nie ma
fikcyjnej animacji pracy agentów. Długie treści przewijają całą stronę,
nie ma małych, zagnieżdżonych okien przewijania. Jasny/ciemny i palety wspólne.

Klient przed otwarciem widzi informację o zgłaszaniu otwarcia projektu,
workflow, etapu, materiałów i odbiorów. Nie zapisujemy klawiszy, adresu IP,
user-agenta, hasła, tokena ani niewysłanych formularzy. Osobno zapisujemy
świadomie wysłane decyzje i komentarze, zgodnie z komunikatem formularza. Zdarzenie jest sygnałem
z przeglądarki, nie dowodem odczytania/akceptacji i nie tożsamością osoby.
Posiadacz kodu może wygenerować takie zdarzenie sam; nie jest to rozliczenie pracy.

Kod wiąże zdarzenie z publikacją; klient nie podaje ID klienta lub projektu.
Serwer sprawdza aktualną datę publikacji i bierze tytuł etapu z jej treści.
Cofnięcie lub wygaśnięcie kodu blokuje także zapis aktywności. Żądania
nie częściej niż raz na 2 sekundy; zachowujemy ostatnie 1000 zdarzeń na kod.
Starsze zdarzenia są usuwane z tego ograniczonego rejestru, nie z historii
wersji publikacji. Polling co 30 sekund nie tworzy zdarzenia aktywności.
Zgłoszenia są best-effort: połączenie, zamknięcie karty albo ograniczenie
częstotliwości mogą pominąć zdarzenie. Nie pokazujemy wskaźnika „klient online”.

W `/os/clients` właściciel podaje swój token, wybiera projekt/udostępnienie,
rozwija zapisane wersje i ogląda datowaną listę aktywności. Wygasłe/cofnięte
udostępnienia pozostają w historii właściciela. Odświeżanie tego widoku jest
ręczne; cała historia zleceń i wyników pozostaje też w `/os/work`.
Osobny klient ASGI nie rejestruje tej strony, skryptu ani endpointów historii.

Kod ma 32 losowe bajty. Baza przechowuje jego SHA-256, a nie kod jawny.
Wycofany lub wygasły kod nie umożliwia kolejnego odczytu. Odpowiedzi klienta
korzystają z jawnej listy pól `PublishedProject`, nigdy z serializacji
wewnętrznego `Project`, `Task` lub `Artifact`. Operacje właściciela podlegają
dotychczasowemu audytowi mutacji bez zapisywania kodów.

Przeglądarka nie przechowuje kodów w localStorage, sessionStorage ani cookie.
Wylogowanie i opuszczenie strony czyszczą dane. Revocation nie cofa danych,
które odbiorca wcześniej skopiował lub pobrał. Kod jest tokenem posiadacza,
nie pełnym kontem klienta z MFA i odzyskiwaniem hasła.

## Ważna granica wdrożenia

**Nie wystawiaj `app.main:app` publicznie jako panelu klienta.** Starszy serwer
wewnętrzny nadal ma endpointy odczytu przeznaczone do lokalnego użycia.
Sam nowy kod klienta nie zabezpiecza tych starych endpointów.

Przygotowano osobny moduł ASGI `app.client_main:app`, który udostępnia wyłącznie:
stronę klienta, jej dozwolone zasoby statyczne i chronione kodem endpointy klienta.
Nie rejestruje API zadań, struktury, właściciela, dokumentacji Swagger ani
skryptów administracyjnych. Ten moduł **nie został uruchomiony w nowej usłudze**.

Przed dostępem spoza hosta nadal trzeba uzgodnić i wdrożyć HTTPS, osobny
gateway/origin, ograniczenie liczby prób autoryzacji, monitoring, politykę
dostępu i kopie zapasowe. Nie zmieniamy portów, DNS, zapory ani usług Vast.ai
w ramach tworzenia tego panelu. Kod dostępu przekazujemy bezpiecznym kanałem,
a nie jako część URL.
