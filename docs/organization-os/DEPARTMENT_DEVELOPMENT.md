# Dalsza rozbudowa funkcji działów

Wymaganie właściciela z 21.09.2026: równolegle automatyzować naukę modeli
i doprowadzić wszystkie działy do użytecznego działania. Wygląd menu pozostaje
osobnym, późniejszym zadaniem. Lokalny model tworzy realizacje; asystent
rozwija infrastrukturę i sprawdza rezultaty.

Właściciel doprecyzował, że docelowy system ma kontynuować naukę i rozwój
bez kontroli asystenta prowadzącego. Oznacza to więcej niż harmonogram:
wybór nowych ćwiczeń na podstawie niepowodzeń, sprawdzone dane, trening,
oddzielny sprawdzian, zatrzymanie regresji i przywrócenie poprzedniej wersji.
Automatyczna deklaracja sukcesu modelu nie spełnia tego wymagania.
Deterministycznie sprawdzane umiejętności można odbierać przez testy;
wiarygodna samodzielna ocena stylu i treści pozostaje otwartą częścią prac.

Odczyt obecnego kodu potwierdza dwanaście profili działów, przydział ról
i cztery etapy zlecenia. Obsługa lokalnej inferencji istnieje osobno od
kolejki symulacyjnej. Przydział roli lub przycisk w panelu nie dowodzi
samodzielnego wykonania. Przejścia wymagają konkretnych wyników i odbioru.

Poniższe wymagania są zakresem dalszej realizacji, nie listą funkcji odebranych.

| Dział | Użyteczna praca do uruchomienia z działu | Dowód zakończenia |
| --- | --- | --- |
| Strategia | Zamiana celu na priorytety, zależności i plan | Wersjonowany plan powiązany z zadaniami i kryteriami |
| Platforma | Implementacja funkcji lub naprawa zgłoszenia | Źródła modelu, izolowane wykonanie, raport testów |
| AI i automatyzacja | Przygotowanie danych, trening i ocena modeli | Zapis cyklu, nowe wagi oraz niezależne porównanie |
| Aplikacje webowe | Budowa i poprawianie aplikacji z briefu | Uruchamialna paczka, podgląd i sprawdzian wymagań |
| Doświadczenia cyfrowe | Strony i materiały graficzne | Modelowe źródła, podglądy i ocena użyteczności |
| Systemy i badania | Izolowany prototyp i eksperyment | Powtarzalna próba, logi i wnioski z rzeczywistych pomiarów |
| Obsługa klienta | Brief, zmiany zakresu, odbiór i przekazanie | Historia wersji, uzgodnienia i komplet wydania |
| Jakość i bezpieczeństwo | Sprawdzenie konkretnego wyniku | Powiązane z wersją testy, usterki i decyzja |
| Operacje | Diagnostyka, kopie i próby odtworzenia | Faktyczne pomiary oraz kontrolowana próba odtworzenia |
| Biznes i marketing | Oferta oparta na sprawdzonych możliwościach | Materiały zgodne z briefem i bez zmyślonych osiągnięć |
| Finanse i formalności | Zestawienia kosztów i zobowiązań | Sprawdzalne wyliczenia, źródła oraz wskazane braki |
| Wiedza i społeczność | Instrukcje i ponowne użycie doświadczeń | Wersjonowane materiały z pochodzeniem i oceną |

Dla każdego działu wymagany jest pełny przebieg: wejście użytkownika →
zadanie → wykonanie lokalnego modelu/narzędzia → artefakt → niezależna
weryfikacja → czytelny status i pobranie wyniku. Testy na izolowanej bazie
sprawdzają mechanizm; rzeczywista próba modelu musi potwierdzić jakość.
Nie należy tworzyć sztucznych sukcesów w bazie produkcyjnej.

Pierwszy wdrażany element wspólny opisuje [automatyczne przygotowanie danych](LEARNING_AUTOPILOT.md).
Następny zakres: trwała koordynacja rzeczywistych wykonań i przekazywanie
zaakceptowanego wyniku między etapami, a następnie narzędzia specyficzne
dla każdego działu. Nie zastępuje to celu jakości pięciu usług Upwork.
