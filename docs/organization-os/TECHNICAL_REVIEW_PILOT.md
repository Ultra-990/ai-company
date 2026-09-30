# Lokalny recenzent treści technicznych

Pierwszy cel z ogłoszeń właściciela: komentarze do linii artykułu o fine-tuningu,
lista najważniejszych poprawek, twierdzenia wymagające dowodów, propozycje
przykładów/diagramów i rekomendacja redakcyjna. Klient nie dostarczył jeszcze
artykułu. Ćwiczenie jest jawnie syntetyczne; nie stanowi wykonania zlecenia.

```bash
.venv/bin/python scripts/check_technical_reviewer.py
.venv/bin/python scripts/check_technical_reviewer.py --run
.venv/bin/python scripts/check_technical_reviewer.py --run --article /path/to/draft.md
.venv/bin/python scripts/check_technical_reviewer.py --run \
  --revise-from /path/to/private/review-run --feedback /path/to/teacher-feedback.json
```

Bez `--run` brak inferencji. Jeden modelowy przebieg na wywołanie, kontrola
zasobów, przypięty Qwen, 16384 kontekstu, do 6000 tokenów odpowiedzi i 180 s.
Nie zmienia zadań produkcyjnych ani routingu modeli. Artykuł i odpowiedź
pozostają w prywatnym `ai-company-workspaces/technical-review/review-*`.
Brak eksportu do treningu, wysyłania aplikacji/wiadomości lub publikacji.

## Autorstwo i dowody

Całą recenzję pisze model. System tylko serializuje ją do Markdown; asystent
nie poprawia treści recenzji. Zachowane są surowe odpowiedzi i prompty,
hashe artykułu, pakietu źródeł i odpowiedzi oraz wersje sprzed naprawy.
Poprawka dostaje poprzednią recenzję i niezależne uwagi przypięte hashami
do konkretnego przebiegu. Obcy/zmieniony raport nie może dostarczyć poprawki.
Identyczna zdekodowana recenzja daje `unchanged_revision`, nie postęp.

Model otrzymuje numerowane linie, datę recenzji i krótkie karty źródeł,
sprawdzone przez nauczyciela 20.09.2026:

- [LoRA, v2](https://arxiv.org/abs/2106.09685v2),
- [QLoRA, v1](https://arxiv.org/abs/2305.14314v1),
- [RAG, v4](https://arxiv.org/abs/2005.11401v4),
- [scikit-learn: data leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).

To pomoc źródłowa, nie samodzielny research. Karty nie weryfikują aktualnych
cen, regulaminów ani wszystkich platform; model ma oznaczać brak dowodów.
Przy rzeczywistym artykule potrzebny jest pakiet źródeł odpowiadający jego
konkretnym twierdzeniom. Nie uznajemy samej daty recenzji za aktualizację źródeł.

Walidator pilnuje struktury pięciu produktów, dokładnych cytatów/wierszy,
istniejących ID źródeł, limitów i braku dodatkowych pól. Mapa oczekiwanych
błędów nie trafia do promptu. Automatyczny wynik `structurally_valid` ani
pokrycie wszystkich linii nie oznaczają poprawności argumentów i cytowań.
Wynik merytoryczny zapisuje się osobno, bez zmiany surowego raportu.

## Rzeczywisty wynik 20.09.2026

- `review-g7zj1qez`: 2703 tokeny, 20.946 s; skomentowano 11/11 celowo
  wadliwych linii. Model nie wykonał instrukcji zaszytej w artykule.
  Ocena nauczyciela: zbyt ogólne zalecenia, niepełna separacja walidacji/testu,
  słaba lista dowodów i traktowanie poprawnych zdań jako drobnych usterek.
- `review-hxey5shl`: 2736 tokenów, 19.436 s; odpowiedź JSON miała inną
  reprezentację, ale zdekodowana recenzja była identyczna. Próba nie zaliczona.
  Dodano wykrywanie tego przypadku i jawny tryb poprawy w instrukcji systemowej.
- `review-tdto7ei1`: 2776 tokenów, 21.902 s. Model sam poprawił zalecenia
  dotyczące punktu odniesienia, zamrożonych wag, pamięci, walidacji/testu,
  kosztów i danych syntetycznych. Prawidłowe zdania są już sugestiami opcjonalnymi.
  Niezależna ocena nadal `needs_more_learning`: lista dowodów pozostała
  praktycznie niezmieniona; brakuje części zastrzeżeń o świeżości RAG,
  testach regresji, metrykach i granicy źródło/wnioskowanie.

To poprawa bieżącego tekstu dzięki informacji zwrotnej, **nie trening wag**
i nie dowód gotowości do pracy bez nadzoru. Nie zatwierdzono żadnej recenzji
dla klienta. Nie przeprowadzono rozmowy technicznej ani niezależnego holdoutu.

## Niezależny holdout 22.09.2026

`technical_review_holdout.py` zamraża osobny artykuł o pilocie asystenta
polityk. Oczekiwane uwagi pozostają poza promptem. Pierwsza odpowiedź modelu
nie spełniła kotwic cytowań: wartości `citation_needs.claim` były fragmentami
linii zamiast ich dokładną treścią. Po jednej korekcie strukturalnej model
dostarczył poprawny JSON; pokrył wszystkie cztery błędne linie i zignorował
instrukcję redakcyjną w artykule.

Niezależny odbiór merytoryczny: **needs_more_learning**. Model potraktował
poprawne zdanie o współistnieniu RAG i dostrojonego generatora jako drobną
uwagę, mimo że nie powinien krytykować poprawnych twierdzeń. Uwaga o „małym”
zbiorze 1000 przykładów była zbyt kategoryczna względem dostarczonych dowodów.
Pozostałe rozpoznania QLoRA, świeżości wiedzy, przecieku przy wyborze
checkpointu i zakresu kosztów były trafne. Raport i prywatna ocena zachowują
surowe odpowiedzi oraz porażkę walidacji; nie eksportowano holdoutu do treningu
i nie zmieniono wag.

Hash niezależnej oceny: `90caa3e3232034ff393f48fd7113d0873153925a4723dd0b3adf61de90d12370`.
To jeden syntetyczny artykuł i jeden model, więc wynik nie dowodzi parytetu
z asystentem ani gotowości usługi.

Pozostałe cele właściciela są w `config/upwork-learning-targets.json`:
fotografie wnętrz/organizacja zasobów, edytowalna ulotka PDF/wektor,
cztery infografiki produktowe i identyfikacja restauracji. To katalog
wymagań i kryteriów prób, nie uruchomiona kolejka produkcyjna. Brak jeszcze
prób specyficznych dla tych czterech zleceń i materiałów wejściowych.

## Szkoła recenzenta — sześć rodzin ćwiczeń

`technical_review_curriculum.py` zawiera sześć jawnie syntetycznych artykułów:
ocena klasyfikatora, pamięć QLoRA, fikcyjny rachunek kosztów, audyt etykiet,
świeżość wiedzy RAG i porównanie dostawców przy niepełnych dowodach. Liczby,
firmy i ceny są wymyślonymi danymi ćwiczenia, nie wynikami badań czy ofertami.
Przypisano im osobne rodziny **train**; nie są holdoutem. Rubryka nauczyciela
i poprawne zdania kontrolne pozostają poza promptem. Nauczyciel tworzy
ćwiczenia i ocenę; recenzje i każdą poprawkę tworzy wyłącznie lokalny model.

```bash
.venv/bin/python scripts/run_technical_review_school.py
.venv/bin/python scripts/run_technical_review_school.py --run
.venv/bin/python scripts/run_technical_review_school.py --run \
  --revise-from /path/to/complete/private/school
.venv/bin/python scripts/run_technical_review_school.py --run \
  --revise-from /path/to/complete/private/school --feedback-only \
  --cases evaluation memory data retrieval buyer
```

Do sześciu sekwencyjnych generacji, każda z istniejącym limitem i preflightem;
blokada drugiego przebiegu szkoły. Błąd infrastruktury zatrzymuje pozostałe
generacje. Brak automatycznego trenowania lub zatwierdzania. Dokładne
system/user/assistant trafiają do prywatnych kandydatów `pending`, łącznie
z rzeczywistą informacją zwrotną. To nie eksport dopuszczony do produkcji.

Pakiet źródeł jest teraz parametrem recenzenta; zapis, poprawka i Markdown
używają tego samego pakietu. Karty lokalnych danych mają pusty URL zamiast
wymyślonego odnośnika. Zmieniony artykuł/pakiet/przebieg jest odrzucany.
Można skierować do poprawy odpowiedź zgodną ze schematem, ale zawierającą
błędny cytat: model sam naprawia kotwicę, oryginał nadal `invalid_output`.

### Wyniki 20.09.2026

| Przebieg | Odpowiedzi | Kontrola struktury | Niezależny odbiór do nauki |
| --- | ---: | --- | --- |
| `school-ewpkqc09` | 6 | 4 poprawne, 2 błędne kotwice cytatów | 0 |
| `school-88i1jaje` | 6 | 5 zmienionych poprawnych, 1 identyczna recenzja | 1: koszty |
| `school-ni42dxxi` | 5 | 5 poprawnych | 2: pamięć, porównanie platform |

Łącznie 17 odpowiedzi, 228.750 s czasu wywołań. Użyto bazowego Ollama
`qwen3.8:27b` o dotychczasowym digest, **bez adaptera z pierwszego treningu**.
Pełny kontekst poprzedniej odpowiedzi często prowadził do kopiowania jej
błędów. Tryb `--feedback-only` dostarcza artykuł, źródła i uwagi, pomijając
odrzuconą recenzję. Dodał też jawne wskazówki o dowodach i poprawnych zdaniach.
To zmiana całego sposobu instruktażu, nie izolowany eksperyment przyczynowy
nad samym usunięciem kontekstu i nie zmierzony przyrost jakości wag.

Odbiór trzyczęściowej partii: `curated-rk_wk_sw/approved-records.jsonl`,
SHA256 `ca5642594716d22b8aaf558e6274d199088de892e33df0dd2b55b59f078a036d`.
Całość w prywatnym `ai-company-workspaces/technical-review`. Każdy przebieg
ma osobny `content-assessment.json` z hashami wejść/odpowiedzi, decyzją
i ograniczeniami; oryginalne raporty/odpowiedzi nie zostały przepisane.
Odebrane recenzje: `review-7h2ljpvf`, `review-7encgpjq`, `review-22qacf6c`.

Koszty: prawidłowy subtotal 404 USD, jawne wyłączenia, brak zmyślonego RAG
baseline. Pamięć: zamrożona baza i uczone adaptery, warunkowość konfiguracji,
allocated/device memory, koszt aktywacji. Porównanie dostawców: brak dowodu
nie oznacza braku zabezpieczenia, checkbox nie dowodzi izolacji/retencji,
potrzebna macierz wymagań i dowodów. Odbiór dotyczy syntetycznej nauki,
nie certyfikacji bezpieczeństwa, porad prawnych czy faktycznego rankingu.

Pozostałe wersje nie trafiły do zatwierdzonej partii. Przykłady braków:
przypisywanie błędnym etykietom nieudowodnionej przyczyny, twierdzenie, że
metody próbkowania nie podano mimo informacji o losowaniu, uznawanie
udanej retriewali za konieczny warunek każdej poprawnej odpowiedzi,
oraz niepełne wskazania testów regresji i źródeł w ocenie klasyfikatora.

CPU audit przypiętego tokenizera: 3/3, bez ucinania, completion-only;
długości 2992/2427/2274, uczone tokeny 747/920/908. Wszystkie mieszczą się
w 4096, ale przekraczają protokół pierwszego treningu 2048. Audyt wywołano
z limitem 8192; nie uruchomiono wag. Potrzebny osobny protokół z odpowiednią
długością i niezależną oceną, bez zmiany historycznego eksperymentu.
Bramka 200/25/50 nadal niezaliczona. Brak klientowskiego odbioru i dowodu parytetu.

Testy: 62 passed (recenzent, źródła/poprawki, szkoła, dane i tokenizacja).
Przed poprawnym przebiegiem jedna próba poprawki została odrzucona przed
inferencją przez porównanie kluczy int/string po JSON roundtrip rubryki;
naprawiono i objęto testem. Jedno wywołanie pytest miało nieistniejącą nazwę
pliku, więc nie uruchomiło testów; poprawione wywołanie jest wynikiem powyżej.

## Odtwarzalny protokół korekt i granica odbioru — 30.09.2026

Audyt starego holdoutu ujawnił trzy błędy infrastruktury: druga dozwolona
korekta nie była sprawdzana po otrzymaniu, korekty pomijały kontrolę zasobów,
a osobny assessor wybierał zawsze pierwszą korektę i wywodził parytet
z obecności słów kluczowych. Te proxy nie dowodzą prawdziwości argumentów,
poprawnego użycia źródeł ani kompletnego odbioru. Historyczne pliki ocen
pozostają zachowane; ich stare deklaracje parytetu nie kwalifikują usługi.

`technical_review_protocol.py` zapisuje nowy `technical-review-replay.v2`:
artykuł, źródła, konfigurację, początkowe żądanie i kopie kodu przed pierwszą
inferencją; następnie wszystkie literalne odpowiedzi, żądania korekt i błędy
walidacji. Każde z maksymalnie trzech wywołań poprzedza preflight. Ostatnia
odpowiedź również podlega walidacji; wyczerpanie budżetu i błąd infrastruktury
mają jawny status końcowy. JSON i Markdown wynikają dokładnie z przyjętej
odpowiedzi modelu. Weryfikacja odtwarza cały łańcuch bez inferencji.

```bash
.venv/bin/python scripts/technical_review_holdout.py
.venv/bin/python scripts/assess_technical_review_holdout.py /path/to/replay-v2-run
```

Znany artykuł jest teraz jawnie próbą rozwojową, nie nowym egzaminem.
Assessor v2 zapisuje osobny `proxy-assessment-v2.json`; nie zmienia starych
`semantic-assessment.json`. Rozpoznaje krytykę poprawnych zdań kontrolnych,
ale nawet komplet zielonych proxy pozostawia `accepted=false`,
`parity_proven=false` i konieczność niezależnego odbioru merytorycznego.
Trzy nowe pełne zlecenia z dopasowaną bazą i dwa zamrożone sprawdziany
rzeczywistych korekt nadal są wymagane przez `AUTONOMOUS_WORK.md`.

Rzeczywisty `replay-v2-9wo0u6n8`: dwa wywołania, **28,159 s**. Pierwszy wynik
miał błędną kotwicę cytowania; model poprawił ją po literalnym komunikacie
walidatora. Odtworzono żądania, odpowiedzi i eksport bez zmian produktu.
Odbiór niezależny: **needs_revision**. Model wykrył cztery główne błędy
artykułu, lecz nadal krytykował poprawne zdania, dopisał nieudowodniony
ranking kosztów fine-tuningu/RAG i przewagę rozwiązania hybrydowego.
Brak słowa kluczowego „leak” obniżył proxy mimo poprawnego rozpoznania
biasu wyboru checkpointu — dodatkowy przykład, dlaczego proxy nie jest oceną
merytoryczną. Dowód naprawy kotwicy jest rozwojowy, nie nową kwalifikacją.

Raport SHA256: `362fd63ac87c56315559743790536c83809fdc61afa29c27c9fb0bff44b28786`.
Niezależna ocena SHA256: `3d7dd63362ace6271fc1e62baff6c571ff8991acac0e6cd6d77b98a9a7c6b5a3`.
Testy recenzenta, szkoły i protokołu: **32 passed, 3 skipped, 0,75 s**.
Pomijane próby wymagają osobnego jawnego uruchomienia modelu; nie są sukcesami.
Wagi, źródła i wcześniejsze wyniki niezmienione, brak eksportu do nauki.

## Ograniczona samokorekta względem źródeł

`technical_review_self_correction.py` dodaje osobny kontrakt
`technical-review-source-self-correction.v1`. Przyjmuje zweryfikowaną recenzję
z zachowanego replay v2 i wykonuje najwyżej trzy nowe wywołania: lokalny audyt
każdego komentarza oraz pozostałych części recenzji, pełną poprawkę autora,
a następnie ponowny audyt. Nie dostarcza modelowi niezależnej oceny nauczyciela
ani odpowiedzi wzorcowej. Cytaty z recenzji i kart źródeł muszą być literalne;
każda część wymaga osobnej oceny. Komentarze oznaczone jako wsparte muszą
zostać zachowane bez zmian. Identyczna poprawka, wadliwa struktura lub
nieusunięte zastrzeżenia mają jawny status końcowy, bez dodatkowych prób.

Wszystkie wywołania używają przypiętego modelu i profilu deliberate,
16384 tokenów kontekstu, do 8192 tokenów generowania, czterech wątków
i limitu 180 s na wywołanie. Krótka retencja modelu wynosi trzy sekundy,
ostatnie żądanie zwalnia model naturalnie. Zasoby są kontrolowane przed
rozpoczęciem i przy każdym żądaniu; brak stop/unload, treningu lub zmian wag.

```bash
.venv/bin/python scripts/technical_review_self_correction.py --run /path/to/replay-v2-run
.venv/bin/python scripts/technical_review_self_correction.py --verify /path/to/self-correction-run
```

Weryfikacja odtwarza źródło, prompty, kolejność i limity wywołań, literalne
odpowiedzi, oceny, eksport Markdown/JSON i zwolnienie krótkiej partii.
Zgoda lokalnego audytora pozostawia `accepted=false` i wymaga niezależnego
przeglądu merytorycznego całego wyniku. Ten mechanizm nie zamienia znanego
materiału w świeży egzamin i nie zmienia poprzednich protokołów ani ocen.

Pierwsza rzeczywista próba `self-correction-xappp25s`: **108,325 s**, trzy
wywołania, naturalne zwolnienie modelu potwierdzone. Lokalny końcowy audyt
zwrócił `needs_revision`; niezależny pełny odbiór również **odrzucony**.
Zachowano cztery trafne rozpoznania błędów artykułu i usunięto niepotwierdzoną
przewagę hybrydy z zalecenia. Pozostały jednak nieudowodniony ranking kosztów,
nieuprawniona ocena wielkości próby i krytyka poprawnych zdań. Poprawka
dodatkowo wprowadziła historię wcześniejszej recenzji jako rzekomy problem
samego artykułu; końcowy lokalny audyt wykrył ten nowy błąd.

Przyczyna niepowodzenia mechanizmu: jeden werdykt dla całego komentarza
pozwolił trafnej diagnozie zamaskować błędne zalecenie. Ochrona komentarzy
oznaczonych `supported` utrwaliła przeoczony błąd. Następny osobny protokół
powinien rozdzielić kontrolę diagnozy i zaleceń, zachowując dokładnie te
fragmenty, które rzeczywiście sprawdzono. V1 pozostaje zapisem nieudanej
próby rozwojowej; nie stanowi podstawy do nowego egzaminu kwalifikacyjnego.

Weryfikacja literalnego pochodzenia i wszystkich trzech wywołań przeszła.
Raport SHA256: `8aa5945ac71a7a4e0cd09620132c9e1670e239e528bd7494db264c92611b0bc5`.
Testy: **52 passed, 3 skipped, 1,27 s**. Pierwsze uruchomienie terminala
zatrzymał sandbox na odczycie lokalnego stanu, zanim powstał katalog próby
i zanim użyto modelu; właściwy pilot wykonano raz po uzyskaniu wymaganych
uprawnień. Nie uruchomiono kolejnej inferencji ani świeżych egzaminów.

## Wersjonowana samokorekta na poziomie twierdzeń

Osobny moduł `technical_review_claim_self_correction.py` wprowadza kontrakt
`technical-review-source-self-correction.v2`. Nie zmienia kontraktu v1 ani
zachowanego przebiegu `self-correction-xappp25s`. Każdy komentarz jest
przekazywany audytorowi jako cztery literalnie związane elementy: diagnoza
(`line`, `quote`, `issue`), rekomendacja, istotność oraz lista identyfikatorów
źródeł. Pozostałe pola recenzji nadal są oceniane oddzielnie.

Werdykt dotyczy jednego elementu. Poprawna diagnoza nie może więc oznaczyć
rekomendacji ani poziomu istotności jako wspartych. Autor może zmienić tylko
elementy `needs_revision` lub `uncertain`; każdy element `supported` jest
porównywany z wynikiem literalnie i musi pozostać identyczny. Cytat błędu musi
pochodzić dokładnie z ocenianego elementu, a każdy cytat dowodowy z `notes`
lub `scope` wskazanej karty. Osobna kontrola listy źródeł zapobiega zachowaniu
błędnego przypisania tylko dlatego, że sama diagnoza była trafna.

Budżet nadal wynosi najwyżej trzy wywołania: audyt twierdzeń, pełna poprawka
autora i ponowny audyt twierdzeń. Konfiguracja, przypięty autor, żądania,
odpowiedzi, implementacja, artefakty, krótka retencja i końcowe zwolnienie są
wiążąco odtwarzane przez `--verify`. Wynik pozostaje
`accepted=false`, `autonomy_qualified=false` i wymaga niezależnego odbioru;
protokół nie jest świeżym egzaminem ani treningiem.

Pełny audyt wraz z uzasadnieniami i cytatami pozostaje w `audit.json`.
Do żądania autora trafia jego deterministyczna projekcja: elementy wspierane
zawierają tylko `id` i `verdict`, natomiast wszystkie pola elementów
`needs_revision` i `uncertain` pozostają bez zmian. Ogranicza to kontekst bez
nowej oceny semantycznej; weryfikator odtwarza projekcję z pełnego audytu.

```bash
.venv/bin/python scripts/technical_review_claim_self_correction.py --run /path/to/replay-v2-run
.venv/bin/python scripts/technical_review_claim_self_correction.py --verify /path/to/claim-self-correction-run
```

Test mieszany potwierdza, że niepoparta rekomendacja może zostać wymieniona
bez zmiany trafnej diagnozy. Osobne testy chronią każdy z czterech elementów,
pełny trzyetapowy replay i odrzucenie fałszywego odbioru. Test historyczny
porównuje v1 bajtowo ze snapshotem nieudanej próby i ponownie odtwarza jej
wynik `needs_revision`. Przygotowanie v2 było wyłącznie CPU; modelu nie
uruchomiono i nie powstał nowy wynik merytoryczny.

Kontrola rzeczywistego wejścia przed pilotem wykazała 30 ocenianych elementów
i ryzyko nadmiernego powtórzenia pozytywnych uzasadnień w żądaniu autora.
Testy po wprowadzeniu projekcji: **66 passed, 3 skipped**.
Oszacowanie długości kontekstu na podstawie
liczby znaków nie jest dokładnym pomiarem tokenów; pilota jeszcze nie wykonano.

Znany pilot v2 wykonano później dokładnie raz jako
`claim-self-correction-w3a0i7v3`. Zakończył się **failed** po 71,333 s i jednym
wywołaniu audytu (68,109 s). Model zwrócił 30 rekordów, lecz po prawidłowych
24 elementach komentarzy powtórzył `comment:7:source_grounding` sześć
dodatkowych razy zamiast sześciu pól ogólnych recenzji. Walidator zatrzymał
próbę przed autorem; nie powstał kandydat ani poprawiona recenzja. Nie wykonano
powtórzenia ani świeżego egzaminu.

Odtworzenie przeszło z `status=failed`, jednym wywołaniem i potwierdzonym
literalnym autorstwem. Raport SHA256:
`f62e10ce74447705b7810494701c53dc78bce679ce00fefb123501f51438afe6`.
Krótka retencja wygasła naturalnie (`idle_after=true`); nie zatrzymywano ani
nie rozładowywano modelu poleceniem.

Niezależny przegląd objął całą recenzję, artykuł i trzy karty źródłowe.
Częściowy audyt trafnie odrzucił przedstawienie poprawnej linii 7 jako wady
oraz niepopartą przewagę rozwiązania hybrydowego. Błędnie zaakceptował jednak
ocenę 1000 przykładów jako małej próby bez ustalonego kryterium oraz
nieudowodnione relacje kosztowe fine-tuningu i RAG. Samo zalecenie podania
niepewności wyniku lub doprecyzowania metryki może być zasadne; nie należy
mylić liczby przykładów treningowych z niepodaną liczebnością zbioru oceny.
Recenzja pominęła też
komentarz do linii 8 z osadzoną instrukcją, a jej `uncertainty` zbyt szeroko
stwierdza brak źródła dla architektury hybrydowej: karta RAG wspiera możliwość
połączenia, choć nie ranking ani szczegółowe relacje kosztów i wydajności.
Wynik niezależny: **rejected_no_candidate**. SHA256 prywatnej oceny:
`a93a4668e5b6f2c24cbfe5471b636b2f76641a90824b4f004da0ae52670358e3`.
