# Organization OS

Nowy panel operacyjny firmy.

Aktualny priorytet: [zlecenia Upwork → analiza zakresu Qwen → realizacja](UPWORK.md).

Zapis i nadzór: [GitHub oraz kontrola pracy modeli](GITHUB_WORKFLOW.md).
Gotowe komponenty: [ocena projektów open source](OPEN_SOURCE_REUSE.md).
Najnowszy etap wykonawczy: [generowanie, testowanie i wydanie aplikacji
z wieloma modułami](MULTIFILE_RUNNER.md). Poniższe historyczne opisy prototypu
nie zastępują aktualnych dokumentów poszczególnych funkcji.

Zespoły i zadania: [trwała hierarchia agentów oraz delegacje](AGENT_TEAMS.md).
Przydzielanie dostępne w [centrum realizacji](WORKBENCH.md), bez uruchamiania modeli.

## Status

Aktualny ekran `/os` jest bezpiecznym prototypem integracyjnym, nie finalnym
interfejsem systemu operacyjnego. Pokazuje dane z API i służy do weryfikacji
modelu drzewa, postępu, alertów oraz „Następnego ruchu”. Obecne kule i okna
korzystają z CSS/SVG; scena z geometrią, kamerą i oświetleniem 3D pozostaje
do zbudowania. Docelowy zakres firmy, sieć agentów i wymagania interfejsu
opisuje [architektura](../ARCHITECTURE.md).

Założenia:
- stara roadmapa pozostaje dostępna historycznie;
- źródłem aktualnego postępu staje się drzewo organizacyjne;
- kula AI otwiera Centrum Właściciela;
- osobna kula BRAIN reprezentuje orkiestratora i relacje z działami;
- 12 okien reprezentuje działy firmy;
- dane panelu pochodzą wyłącznie z API;
- panel pokazuje postęp, blokady, następny ruch i powiadomienia systemowe.

## Odbiór wyników wykonawców

Wykonanie przez `/api/tasks/execute-next` lub orkiestrator zapisuje wynik
do odbioru. `success: true` oznacza zakończenie operacji wykonawcy,
`awaiting_review: true` oznacza wymagany odbiór. Zadanie pozostaje
`in_progress` i nie otrzymuje automatycznie 100%.

Właściciel korzysta z operacji widocznych w `/docs` (token roli owner):

1. `GET /api/tasks/{task_id}/review` — odczytuje `id` próby,
   `result_checksum` i `result_content`.
2. Sprawdza rezultat względem wymagań i zbiera dowody kontroli.
3. `POST /api/tasks/{task_id}/review` — przekazuje odczytane `attempt_id`
   (pole `id` z GET), `result_checksum`, `accepted`, `reason` i listę `evidence`.
4. Akceptacja ustawia `completed` i 100%; odrzucenie ustawia `blocked`.
5. `POST /api/tasks/{task_id}/review/retry` — po odrzuceniu zleca poprawki
   przez ponowne kolejkowanie. Następne wykonanie otrzyma nową próbę.

Przy nieaktualnej wersji wyniku lub powtórzonej decyzji API zwraca 409.
Worker nie może odbierać własnego wyniku przez te endpointy.
Raport odbioru i audyt zachowują decyzję oraz powiązanie z konkretną próbą.
To ręczny odbiór merytoryczny; automatyczne uruchamianie testów produktu
i wygodny formularz odbioru w pulpicie wymagają dalszej implementacji.
# Pomiar budowy działów

Od 2026-09-13 szczegóły każdego działu zawierają inwentarz istniejących
materiałów, następny krok i kryteria gotowości. Opis źródeł i ograniczeń:
[Pomiar i fundamenty działów](DEPARTMENT_MEASUREMENT.md).
