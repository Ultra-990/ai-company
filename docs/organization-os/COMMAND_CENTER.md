# Centrum dowodzenia — wrzesień 2026

## Gdzie wejść

- `/os` — nowy pulpit: przegląd, działy, realizacja, decyzje.
- `/os#departments` — 12 działów i ich odpowiedzialność.
- `/os#department/finance-legal` — przykład karty działu.
- `/os/work` — zapis zlecenia, przydziały, instrukcje, wyniki i odbiór.
- `/os/review` — kontrola zadania i plików, także dla starszych zadań.
- `/os/publishing` — świadome publikowanie materiałów i kodów klienta.
- `/os/clients` — historia publikacji, decyzje klientów i odpowiedzi.
- `/os/client-preview` — podgląd klienta dla właściciela.
- `/os/legacy` — poprzedni pulpit, zachowany do powrotu.
- `/os/spatial` — dotychczasowa scena przestrzenna.

Przy działającym Uvicornie otwórz `http://127.0.0.1:8000/os`.
Po zmianie plików użyj Ctrl+Shift+R. Nie trzeba restartować hosta ani Dockera.

## Logika obsługi

1. Wybierz dział odpowiadający rezultatowi, który chcesz uzyskać.
2. Karta działu pokazuje misję, wymagane dane, rezultat, fundamenty i kryteria.
3. Główny przycisk otwiera Centrum realizacji z parametrem `unit`.
   Po autoryzacji wybierana jest wyłącznie istniejąca opcja z API.
   Samo wejście nie tworzy projektu, nie przydziela ról i niczego nie uruchamia.
4. Wpisz zakres, ograniczenia i kryteria. Jawne wysłanie formularza tworzy
   projekt, plan oraz cztery zadania dopasowane do działu.
5. Przygotuj zespół i przydziel odpowiedzialność. Kontroler jest osobny od
   wykonawcy. Instrukcja następnego etapu wymaga odbioru poprzednika.
6. Dostarcz wynik z pochodzeniem i dowodami. Odbierz konkretną wersję.
7. Osobno opublikuj wybrane informacje w panelu klienta. Publikacja nie
   jest płatnością ani otwarciem serwera dla Internetu.

Właściciel i Brain pozostają rozdzieleni. Obie kule otwierają natywne menu
dialogowe ponad resztą interfejsu; Escape zamyka menu, fokus wraca do przycisku.
Księżyce korzystają ze wspólnego mechanizmu orbity i przesłaniania za kulą.

## Co rzeczywiście robią działy

`department_operations.py` rozszerza istniejące klucze drzewa; nie tworzy
drugiej roadmapy. Każdy dział ma kontrakt wejście–wynik i szablon planu:

| Dział | Rezultat etapu wykonawczego |
| --- | --- |
| Strategia | Decyzja i plan |
| Platforma | Funkcja wspólnej platformy |
| AI i automatyzacja | Projekt automatyzacji i ewaluacji |
| Aplikacje | Wersja aplikacji |
| Doświadczenie cyfrowe | Projekt i wykonanie strony |
| Systemy i R&D | Prototyp oraz raport badawczy |
| Usługi klientów | Plan obsługi i przekazania |
| Jakość i bezpieczeństwo | Kontrola oraz raport |
| Operacje | Procedura i plan próby odtworzenia |
| Biznes i marketing | Oferta i materiały |
| Finanse i prawo | Zestawienie kosztów i wymagań |
| Wiedza | Instrukcja i szablon |

To **planowane rezultaty**, nie automatycznie wykonana praca. Tworzenie
zlecenia nadal wymaga uprawnienia właściciela. Wszystkie cztery zadania
pozostają pending, bez kolejki wykonania i bez zaakceptowanego wyniku.
Kryterium jest zapisane w opisie zadania, a następnie w delegacji, więc
zmiana katalogu nie przepisuje historycznych kryteriów.
Istniejące projekty, delegacje, statusy, wagi i dowody nie zostały migrowane.

## Dane i wydajność

- Rzeczywiste GET-y tree, overview, next-move i alerts; odświeżanie co 30 s
  tylko przy widocznej karcie. Ręczne odświeżenie, limit 8 s, brak nakładania.
- Niepowodzenie jednego źródła nie blokuje menu. Błąd i ostatnio odczytana
  struktura są oznaczone, nieudane odczyty metryk nie stają się fikcyjnym 0.
- Dział bez pomiaru pokazuje „Nie zmierzono”. Procent planu nie jest
  deklaracją gotowości firmy ani ukończenia wszystkich jej zdolności.
- Natywny HTML/CSS, niewielki JavaScript, wspólny system palet. Bez nowego
  bundlera, frameworka, WebGL, fontów CDN, modeli ani pełnoekranowej pętli 3D.
- Responsywne sekcje zamiast małych przewijanych okien. Stałe miejsca funkcji,
  historia sekcji w URL, obsługa klawiatury, minimalne przyciski 44 px.
- Menu i treść API są budowane przez textContent, nie dynamiczny innerHTML.
- Tokeny pozostają w pamięci formularzy istniejących narzędzi; nie są
  przekazywane w linkach, localStorage ani parametrach `unit`.
- Osobna aplikacja klienta nadal odrzuca `/os`, `/os/review`, `/os/publishing`,
  `/os/legacy` i zasoby nowego pulpitu. Nie wystawiać `app.main` publicznie.

## Późniejsze tła

`.future-media[data-media-slot="command-hero"]` jest pustym, dekoracyjnym
miejscem na przyszły obraz/film. Ma warstwę zapewniającą czytelność, nie
przechwytuje kliknięć. Obecnie nie pobiera żadnych mediów.
Przyszłe wdrożenie powinno uwzględnić licencję, poster, limit rozmiaru,
lazy loading, zatrzymywanie filmu poza ekranem i prefers-reduced-motion.
Wgrywanie oraz zarządzanie mediami nie są jeszcze zaimplementowane.

## Zachowanie wcześniejszego wyglądu

Aktualna wersja poprzedniego pulpitu jest pod `/os/legacy`. Niezależna kopia
źródeł sprzed przebudowy znajduje się w
`docs/ui-archives/before-command-gAFYLo/interface.tar.gz`.
Zawiera wyłącznie szablony i statyczne zasoby UI, bez bazy i konfiguracji.
Instrukcja bezpiecznego porównania jest obok archiwum. Przywrócenie samych
assetów nie cofa modelu danych ani historii projektów.

## Granice aktualnego etapu

Nie uruchomiono autonomicznych kierowników, Qwen, kodu klienta, płatności
ani wysyłania ofert. Lokalna kolejka nadal jest symulacją. Pełne wykonanie
wymaga adaptera modelu, limitów, kontroli zatrzymania i izolowanego runnera.
Właściciel dopuścił warunkowe wstrzymanie Vast.ai, ale do tej przebudowy
nie było to konieczne: żadnych zmian wynajmu, CPU/GPU usług ani kontenerów.
