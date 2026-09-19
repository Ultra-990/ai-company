# Miejsce na przestrzenie robocze

Stan odczytu i przygotowania: 2026-09-12. Właściciel zezwolił na wykorzystanie
partycji poza danymi kontenerów. Nie jest to zgoda na zmianę partycji,
formatowanie, nowe kontenery lub uruchomienie modeli podczas wynajmu.

## Wybrany katalog

`/home/marcin/ai-company-workspaces`

| Przeznaczenie | Partycja | System plików | Wolne przy sprawdzeniu |
| --- | --- | --- | --- |
| Nowe katalogi w `/home` | `/dev/nvme1n1p4` | ext4 | około 335 GiB |
| Docker `/var/lib/docker` | `/dev/nvme1n1p3` | XFS | około 748 GiB |

Docker info potwierdził root `/var/lib/docker`. Odczyt punktów montowania
obu istniejących kontenerów nie wykazał bind mountów `/home`: jeden kontener
był zatrzymany bez montowań, drugi miał wolumen pod `/var/lib/docker/volumes`.
To kontrola punktowa; przyszłe kontenery i inne procesy mogą zmienić stan.
Nie odczytywano zmiennych środowiskowych ani danych wewnątrz kontenerów.

Partycje leżą na **tym samym urządzeniu `nvme1n1`**. Pliki są rozdzielone
od katalogu Dockera, ale przepustowość I/O i obciążenie sprzętu pozostają wspólne.
Nie użyto drugiego dysku z niezamontowanymi partycjami NTFS — nie sprawdzano
ich zawartości, nie montowano ich ani nie zmieniano.

## Przygotowana struktura

```text
ai-company-workspaces/       0700, właściciel marcin
├── README.md
├── packages/               kontrolowane eksporty źródeł
├── runs/                   przyszłe osobne katalogi prób
└── reports/                przyszłe eksporty raportów
```

Nie alokowano dużych plików, nie zakładano kwot ani nowych systemów plików.
Nie zmieniano fstab, mountów, uprawnień cudzych katalogów, konfiguracji
Dockera, Vast.ai ani sterowników. Nie usuwano istniejących danych.

## Co pozostaje przed uruchomieniem wykonawcy

- Magazyn paczek i baza aplikacji nadal są w dotychczasowym miejscu.
  Dodano jawny eksport zweryfikowanej paczki do `packages/`, opisany poniżej.
- Zapis odbywa się do osobnego katalogu wersji, bez nadpisywania dawnych
  źródeł. Nie wprowadzono automatycznego tworzenia środowiska wykonania.
- Kontrola miejsca zostawia rezerwę 10 GiB i limit 500 wpisów magazynu.
  Jest kontrolą aplikacyjną, nie twardą kwotą ani rezerwacją bloków na dysku.
- CPU, RAM, GPU, procesy i dostęp do sieci wymagają odrębnej izolacji oraz
  uzgodnienia obciążenia. Sam `chmod 700` ani osobna partycja tego nie zapewnia.
- Nie wolno podłączać docker.sock, urządzeń GPU ani całego `/home` do
  przyszłego środowiska wykonania. Ochrona wynajmu pozostaje obowiązująca.

Nie aktywowano żadnego runnera ani nowego kontenera. Kontrakt próby wykonania,
izolacja procesów i uzgodnienie obciążenia pozostają kolejnym etapem.

## Działa: eksport konkretnej wersji paczki

W `/os/work`, w szczegółach zlecenia, przy paczce źródeł:

- **Zapisz na dysku Linux** tworzy osobny katalog i pokazuje jego pełną ścieżkę.
- **Sprawdź zapis na dysku** weryfikuje istniejące pliki, niczego nie tworząc.

Format nazwy: `packages/task-{id}-package-{id}-{pełne SHA-256 źródła}/`.
Pliki mają 0600, katalogi 0700. Marker `.export.json` zapisany na końcu
zawiera identyfikatory i manifest bez treści źródeł. Pliki nie dostają bitu
wykonywalnego. Nie jest to jednak sandbox: użytkownik marcin nadal może
uruchomić je ręcznie. Nie uruchamiaj obcego kodu na hoście wynajmu.

Eksporter:

- nie przyjmuje docelowej ścieżki przez API, nie rozpakowuje ZIP;
- korzysta wyłącznie z wcześniej zweryfikowanej paczki tekstowej;
- otwiera przodków katalogu bez dowiązań symbolicznych i sprawdza zgodność
  urządzenia z `/home`, właściciela i prywatne uprawnienia katalogu magazynu;
- używa deskryptorów katalogów i wyłącznego tworzenia plików, nie nadpisuje ich;
- przy weryfikacji odrzuca dowiązania, pliki specjalne, zmianę sumy, dodatkowe
  pliki, brak markera oraz niekompletne drzewo;
- sprawdza limit 500 wpisów, rezerwę 10 GiB, rozmiar źródeł oraz zapas 64 MiB
  na metadane. Blokada katalogu serializuje współpracujące operacje eksportu;
  nie blokuje innych aplikacji przed zajęciem miejsca na tej samej partycji;
- synchronizuje zapisy i zapisuje potwierdzenie w istniejącym `Artifact`
  oraz zdarzenie audytu. Nie zmienia postępu i nie uruchamia kodu.

Powtórny eksport tej samej paczki weryfikuje i wykorzystuje istniejący zapis.
**Nie edytuj katalogu wersji w miejscu.** Do zmian użyj odrębnego katalogu
projektu; poprawione pliki zapisz jako nową paczkę przez API/panel źródeł.
Edycja eksportu spowoduje konflikt przy późniejszej weryfikacji.

Filesystem i SQLite nie mają wspólnej transakcji. Awaria zapisu plików może
pozostawić niekompletny katalog; eksporter go nie usuwa ani nie nadpisuje.
Wymaga to jawnej decyzji o archiwizacji/naprawie. Gdy pliki są kompletne,
ale zapis potwierdzenia w bazie nie powiódł się, ponowienie weryfikuje pliki
i może uzupełnić brakujące potwierdzenie. Zapis potwierdzenia nie jest
globalną gwarancją exactly-once przy równoczesnych żądaniach do bazy.

### API (Owner)

- `GET /api/workspace-storage` — stan katalogu, wolne miejsce i limity.
- `POST /api/tasks/{task_id}/workspace-packages/{package_id}/disk-export`
  — eksport/weryfikacja i zapis potwierdzenia; 200.
- `GET /api/tasks/{task_id}/workspace-packages/{package_id}/disk-export`
  — ponowna kontrola plików; 200, bez zapisu.

404: brak paczki dla zadania lub brak eksportu; 409: niepełny/zmieniony zapis
albo naruszona integralność; 503: zajęty/niewłaściwy/niedostępny magazyn,
brak miejsca/limit lub błąd bazy. Dane szczegółowe magazynu nie są publiczne.
Operacje nie przyjmują poleceń uruchomienia ani ścieżek hosta od użytkownika.

### Weryfikacja implementacji

`pytest -q tests/test_workspace_exports.py` korzysta wyłącznie z testowej
bazy oraz katalogów tymczasowych. Sprawdza prywatne uprawnienia, bajty i hash,
RBAC, brak nadpisania, symlinki/hardlinki/FIFO, błędne urządzenie, rezerwę,
limit liczby wpisów, przerwany zapis i odzyskanie potwierdzenia po błędzie bazy.
`scripts/check_work_browser.py` symuluje API zapisu dyskowego; nie eksportuje
niczego do prawdziwego magazynu podczas kontroli UI.
