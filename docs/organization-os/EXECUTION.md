# Pliki projektów i bezpieczne wykonanie na Linuksie

## Aktualny stan zasobów — 2026-09-13

**Najnowsza decyzja: wynajem Vast.ai ponownie aktywny.** Zgody historyczne
poniżej nie obowiązują do potwierdzenia końca wynajmu. Nie uruchamiamy modeli,
treningu, generacji, kontenerów ani obciążających testów. Nie zatrzymujemy
usług i procesów wynajmujących. Aktualne reguły: `AGENTS.md`.
Dozwolone są lekkie prace i izolowane testy z atrapami.

Nowość niewymagająca GPU: [dokumenty przekazania klientowi](DELIVERY_HANDOFF.md)
dla już zatwierdzonych wydań — bez ponownego wykonania programu.

[Porównanie wersji źródeł](PACKAGE_COMPARISON.md) pozwala właścicielowi
skontrolować zmiany plików przed odbiorem, również bez uruchamiania paczki.

Aktualizacja dostępu: główne panele obsługują [wspólną sesję właściciela](OWNER_SESSION.md).
Opis Bearer poniżej pozostaje aktualny dla skryptów i jednorazowego trybu.
Nowy identyfikator sesji jest w HttpOnly cookie; sam token API nie jest tam zapisywany.

Właściciel potwierdził zakończenie wynajmu Vast.ai. CPU/GPU mogą obsługiwać
lokalną inferencję i prace projektowe. Uruchomiono ograniczony
[tekstowy wykonawca Qwen](LOCAL_INFERENCE.md); nie uruchamia kodu z odpowiedzi.
Nie ma potrzeby restartowania hosta, Docker ani zmiany usług wynajmu.

Uruchomiono też pierwszy [profil budowy i testów aplikacji](APPLICATION_FACTORY.md):
pliki Qwen → kontener Python → raport → odbiór → pobierane wydanie. Dalszy opis
planowanego runnera poniżej jest historyczny; aktualny zakres i limity są w tym linku.

## Historyczne ograniczenie Vast.ai (zniesione powyżej)

Aktualizacja 2026-09-12: właściciel dopuścił krótkie użycie GPU przy pracy nad
grafiką. Nie znosi to ochrony procesów wynajmujących ani nie uruchamia runnera,
modeli czy treningu. Dalsze zasady interpretujemy z aktualnym `AGENTS.md`.

Host równocześnie obsługuje wynajmujących GPU. Ich procesy mają pierwszeństwo.
Nie restartujemy komputera, Docker, usług ani kontenerów. Nie wykonujemy
`docker prune`, nie usuwamy obrazów, nie zmieniamy konfiguracji GPU, sieci,
zapory ani Vast.ai. Bez oddzielnego uzgodnienia nie uruchamiamy inferencji,
treningu, benchmarków, generowania multimediów ani nowych kontenerów.

Prace programistyczne i małe, sekwencyjne testy mogą używać CPU i lokalnych
plików tymczasowych. To również niewielkie obciążenie hosta, nie gwarancja
zerowego zużycia zasobów. Przy sygnałach pogorszenia obsługi wynajmu testy
należy przerwać. Nie włączamy równoległych obciążeń ani pełnych buildów.

## Działa: paczki źródeł bez uruchamiania

Paczka to nowy artefakt `SOURCE_CODE` istniejącego zadania. Zapis korzysta
z obecnej tabeli `artifacts`, więc nie wymaga nowej migracji.

- Właściciel zapisuje mapę względnych ścieżek i tekstowych zawartości plików.
- Każdy zapis tworzy osobny identyfikator: API nie udostępnia nadpisywania.
- Manifest zawiera zadanie, cel, posortowane pliki, ich rozmiary i SHA-256.
- Cały manifest ma osobną sumę kontrolną, a zapis ma zdarzenie audytu.
- Odczyt sprawdza sumy i zgodność manifestu z zadaniem.
- ZIP jest generowany w pamięci, bez kompresji, wypakowywania i wykonania kodu.
- API nie obsługuje dowolnych ścieżek hosta, URL, shell, procesów ani Dockera.
- Zapis nie zatwierdza zadania i nie zwiększa postępu. Odpowiedź jawnie
  deklaruje `not_executed` i `not_reviewed`.

Limity: 100 plików, 256 KiB UTF-8 na plik, 1 MiB łącznie, 8 MiB żądania JSON.
Ścieżki są przenośnymi względnymi nazwami ASCII, bez `..`, pustych segmentów,
ukrytych plików, backslash, dysków Windows i konfliktów plik/katalog.
Paczki nie służą do sekretów. Ograniczenia nazw nie wykrywają wszystkich
sekretów zapisanych w treści. Sumy SHA-256 wykrywają niespójność, nie zastępują
podpisu ani kontroli uprawnień administratora bazy.

## Korzystanie przez API

Wymagany token właściciela przez obecny mechanizm Bearer. W `/docs` wybierz
`workspace-packages`; nie wklejaj tokenów do dokumentacji ani repozytorium.

`POST /api/tasks/{task_id}/workspace-packages`:

```json
{
  "purpose": "Pierwsza wersja strony do późniejszego odbioru",
  "files": {
    "index.html": "<!doctype html><html lang=\"pl\"><title>Projekt</title><h1>Wersja robocza</h1></html>",
    "README.md": "Projekt nie był jeszcze uruchomiony ani przetestowany."
  }
}
```

Odpowiedź 201 zawiera `artifact_id`, `checksum` i listę plików bez ich treści.
`GET /api/tasks/{task_id}/workspace-packages/{artifact_id}` zwraca manifest.
`GET /api/tasks/{task_id}/workspace-packages/{artifact_id}/download` pobiera ZIP.
404 oznacza brak paczki dla tego zadania, 409 naruszenie integralności,
413 za duży JSON, 422 nieprawidłowy zakres plików. Worker nie ma dostępu.

`GET /api/tasks/{task_id}/workspace-packages` zwraca do 20 najnowszych paczek
bez treści źródeł. Parametry `limit` (1–50) i `before` pozwalają pobierać
starsze wersje. `next_cursor: null` oznacza koniec listy.

## Panel właściciela w `/os`

1. Kliknij złotą kulę właściciela, następnie **Paczki projektów i odbiór wyników**.
2. Wpisz token właściciela i ID istniejącego zadania. Kliknij **Wczytaj zadanie**.
3. Po lewej znajdują się wersje, manifesty, pobieranie ZIP i zapis nowej paczki.
   Przygotuj plik JSON z polem `files` jak w przykładzie powyżej; cel wpisz
   w formularzu. Nie przesyłaj ZIP ani sekretów. Paczki są przechowywane w SQLite.
4. Po prawej wyświetlana jest bieżąca próba agenta oczekująca na odbiór,
   jej wykonawca, pełna treść i suma SHA-256. Treść jest zwykłym tekstem,
   nie uruchamianym HTML ani poleceniem dla panelu.
5. Sprawdź rezultat, podaj uzasadnienie i dowody (osobne wiersze), zaznacz
   potwierdzenie i wybierz zatwierdzenie lub odrzucenie.

Decyzja dotyczy konkretnego `attempt_id` i jego `result_checksum`, nie paczki
wyświetlanej obok. Odrzucenie blokuje zadanie; nie uruchamia kolejnej próby.
Nie można odebrać zadania bez oczekującego wyniku. Konflikt lub niepewna
odpowiedź przy decyzji wymaga ponownego wczytania zadania.

Panel nie zapisuje tokena w localStorage, sessionStorage, adresie URL ani
cookie. Używa nagłówka Bearer tylko dla żądań do lokalnego API; nie podąża za
przekierowaniami. Zamknięcie, Escape i opuszczenie strony czyszczą formularze
oraz przerywają oczekujące odczyty. To nie cofa zapisu, który serwer zdążył już
wykonać. Po utracie połączenia sprawdź stan przed ponownym zapisem.

Dane tego formularza odświeżane są na żądanie, aby nie nadpisywać wpisywanej
decyzji. Po udanym odbiorze główny pulpit ponownie pobiera swój stan; jego
dotychczasowy cykl odświeżania co 30 sekund pozostaje niezależny.

Testy interakcji: `node tests/test_delivery_center.cjs` (symulowane DOM i API,
bez przeglądarki/GPU). Nie zastępują wizualnego odbioru w przeglądarce.

Nie otwieraj niezweryfikowanego HTML w kontekście zalogowanego panelu firmy.
W `/os/work` dostępny jest [ograniczony statyczny podgląd](PREVIEW.md)
w ramce sandbox bez uprawnień skryptów i same-origin, bez dostępu do tokena.
Nie jest to uruchomienie pełnego projektu.

## Historyczny plan izolowanego runnera (zrealizowany częściowo przez python-web-v1)

Dostępny już krok pośredni: [statyczna kontrola paczek](PACKAGE_CHECKS.md).
Zapisuje rzeczywisty raport ograniczonych kontroli plików, ale nie wykonuje
programu ani testów dostarczonych w paczce. Nie należy utożsamiać go z runnerem.

Docelowo właściciel zatwierdzi konkretną paczkę i profil testowy. Worker
wykona tę wersję w osobnym środowisku i zapisze `TEST_RESULT`, po czym wynik
trafi do istniejącego odbioru. Sama odpowiedź modelu nie dowodzi wykonania testów.

Plan izolacji: lokalny obraz przypięty identyfikatorem, brak pobierania przy
wykonaniu, brak GPU i sieci, nieuprzywilejowany użytkownik, read-only root,
osobny katalog paczki, bez sekretów i docker.sock, ograniczenia CPU/RAM/PID,
timeout i ograniczone logi. Kontenery współdzielą kernel; do kodu faktycznie
wrogiego potrzebne będzie silniejsze odseparowanie lub osobny host.
Nie testujemy tego na aktywnych zasobach wynajmujących.

Parametry izolacji opisuje [oficjalna referencja Docker run](https://docs.docker.com/reference/cli/docker/container/run/)
i [dokumentacja uruchamiania kontenerów](https://docs.docker.com/engine/containers/run/).
Na tym etapie nie dodano wywołania Docker ani endpointu uruchamiającego.
