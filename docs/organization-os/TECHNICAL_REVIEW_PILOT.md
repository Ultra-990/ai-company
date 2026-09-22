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
