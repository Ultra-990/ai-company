# Zbiór do dostrojenia Qwena — wersja 1

## Aktualizacja: projektowanie stron, 19.09.2026

`web-design-batch-001.jsonl` dodaje **dwie** specyfikacje planning po korekcie
asystenta prowadzącego. Qwen zaproponował sześć odpowiedzi; przegląd wykrył
sprzeczności z briefami, język angielski i pozorny sukces formularza.
Nie odebrano surowych propozycji. [Raport](reviews/web-design-batch-001.md).
To odbiór tekstowych specyfikacji, nie wykonanych stron ani estetyki.
Łącznie trzy zatwierdzone partie: **14/200 train, 0/25 validation, 0/50 test**.
Poniższe sekcje o 12 przykładach opisują wcześniejsze dwie partie.

`scripts/draft_web_design_training.py --generate` proponuje maksymalnie sześć
przykładów train/pending lokalnie. Nigdy sam ich nie zatwierdza.
`scripts/check_sft_tokenization.py` w środowisku treningowym sprawdza offline
długość, niezmienność odpowiedzi, EOS i maskę prefiksu. Nie trenuje ani nie
udowadnia poprawności danych; nie trzeba ładować wag do tej kontroli.

## Stan po pierwszej kuracji danych

`specialization-batch-001.jsonl`: dziewięć odebranych przykładów **train**,
przygotowanych z pomocą lokalnego Qwena i przejrzanych przez asystenta prowadzącego.
Cztery odpowiedzi poprawiono, pięć zachowano treściowo. Szczegóły i hash źródeł:
[raport przeglądu](reviews/specialization-batch-001.md). Nie jest to odbiór klienta
ani właściciela; w rekordach jawnie wskazano recenzenta będącego asystentem.
`repair-batch-001.jsonl` dodaje trzy naprawy napisane przez Qwena, odebrane po
rzeczywistych testach w kontenerze i przeglądzie kodu. [Dowody i ograniczenia](reviews/repair-batch-001.md).
Łącznie obie partie: **12/200 train, 0/25 validation, 0/50 test** — niegotowe
do eksportu/treningu specjalizacji.

Osobno istnieje [zestaw oceny napraw](evaluation/README.md): cztery nowe rodziny,
punkt odniesienia obecnego Qwena4/4, bez dopisania odpowiedzi do treningu.
Walidator blokuje te rodziny i dokładne briefy w train/validation; kontrola
parafraz pozostaje zadaniem recenzenta. To jawny test regresyjny, nie końcowy
prywatny holdout i nie dowód poprawy po dostrojeniu.

Laboratorium napraw (bez flagi tylko opis; z flagą do trzech inferencji i sześciu
kontenerów sekwencyjnie, 1 CPU/512 MiB na kontener, bez sieci):

```bash
.venv/bin/python scripts/draft_repair_examples.py
.venv/bin/python scripts/draft_repair_examples.py --generate
```

Model zmienia wyłącznie treść solution.py. Najpierw testuje się wadliwy
przykład, następnie poprawkę na tych samych niezależnych testach. Kod jest
wykonywany tylko w gościu, nigdy importowany na hoście. Wyniki w
qwen-training/repair-drafts-* pozostają pending aż do niezależnego odbioru.
Pierwsza seria wykazała lukę w teście i walidacji wejścia; uzupełniono test,
ponowiono próbę i zachowano oba raporty. Sam zielony wynik nie zatwierdza kodu.
Kontrole HTTP dotyczą zaufanej atrapy pomocniczej, nie aplikacji klienta.

Nie łączymy go z demonstracyjnymi seedami jako rzekomo niezależnym testem:
oba zestawy są jawne, a niektóre motywy (np. dowody wersji) się pokrywają.

Generator propozycji:

```bash
.venv/bin/python scripts/draft_training_examples.py
.venv/bin/python scripts/draft_training_examples.py --generate
```

Bez `--generate` nie wykonuje inferencji. Z flagą generuje maksymalnie dziewięć
lokalnych odpowiedzi sekwencyjnie; sprawdza bezczynność Ollamy i przypięty digest.
Nie czyta bazy klientów, nie wykonuje kodu i nie uruchamia treningu.
W katalogu `qwen-training/drafts-*` zapisuje surowe wyniki (również błędne)
oraz kandydatów **pending**. Oczekiwane klasyfikacje określono przed generowaniem;
Qwen nie dostaje osobnego pola oczekiwanej decyzji. Schema/etykieta nie wystarczają
do odbioru języka i treści. Pierwsza seria wykazała właśnie takie problemy.
Powtórne uruchomienie tworzy nowy katalog; te same ID/rodziny nie są nowymi
niezależnymi przykładami i nie należy ich bezmyślnie sumować.

Instrukcja w drugiej serii jest zapisana w wiadomościach przykładów; dotyczy
przygotowania zbioru, nie została automatycznie wdrożona do agentów produkcyjnych.

## Próbki demonstracyjne

`seed-candidates.jsonl` zawiera sześć ręcznie przygotowanych, syntetycznych
kandydatów. Wszystkie mają `review.status=pending`. Nie są zatwierdzonym
materiałem treningowym ani niezależnym benchmarkiem: przykłady są jawne.
Po wykorzystaniu ich przy tworzeniu promptów nie należy liczyć ich jako
nieznanego modelowi zestawu końcowego. Podział 2/2/2 demonstruje format.

## Kontrola bez GPU i bez bazy aplikacji

Od 19.09 walidator przyjmuje też kilka jawnie wskazanych partii naraz (maks. 32,
łącznie 16 MiB). Sprawdza wspólnie duplikaty, rodziny i rozdzielenie splitów,
nie tylko każdą partię osobno. Raport pokazuje hashe partii, approved_counts,
missing_approved i rozkład umiejętności. Nie uruchamia modelu ani treningu.

```bash
.venv/bin/python scripts/prepare_training_data.py datasets/qwen/specialization-batch-001.jsonl datasets/qwen/repair-batch-001.jsonl --require-ready
```

Obecnie wynik `export_ready: false` i kod 2 są oczekiwane: brakuje 188
zatwierdzonych przykładów train, 25 validation i 50 test względem planu pilota.
Nie uzupełniamy liczb duplikatami, parafrazami z innych splitów ani fałszywymi
odbiorami. Hashe wejściowych partii są zachowywane w przyszłym manifeście eksportu.

Z katalogu repozytorium:

```bash
.venv/bin/python scripts/prepare_training_data.py datasets/qwen/seed-candidates.jsonl
.venv/bin/python scripts/prepare_training_data.py datasets/qwen/seed-candidates.jsonl --require-ready
```

Pierwsza komenda sprawdza strukturę i drukuje raport bez treści przykładów.
Druga dodatkowo zwraca kod 2, jeśli brak odbiorów lub minimalnej liczebności.
Dla obecnego zbioru jest to oczekiwany wynik, nie awaria systemu.

## Format JSONL

Jeden obiekt w każdym wierszu; wzory znajdują się w pliku kandydatów.

- `version`: `company-sft.v1`.
- `id`: unikalny identyfikator; `family`: wspólny identyfikator problemu
  dla wszystkich jego wariantów i parafraz. Rodzina należy tylko do jednego splitu.
- `split`: `train`, `validation` lub `test`.
- `skill`: `scope`, `planning`, `coding`, `repair`, `evidence`.
- `source`: rodzaj `synthetic/owned/licensed`, opis pochodzenia, podstawa
  wykorzystania i jawne potwierdzenie kontroli prywatności.
- `messages`: dokładnie trzy wiadomości tekstowe `system`, `user`, `assistant`.
  To świadomie ograniczony format pierwszej wersji, bez wywołań narzędzi.
- `review`: `pending/approved/rejected`, recenzent, data ISO, uwaga i dowody.
  Dowód ma rodzaj `content_review/independent_test`, referencję i SHA-256.
  Kod i naprawy wymagają dowodu niezależnych testów.

Zatwierdzenie jest osobną czynnością po rzeczywistym przeglądzie. Nie kopiować
fikcyjnych hashy z fixture testów ani nie zamieniać hurtowo pending na approved.
Recenzent musi sprawdzić dowody, ich sumy, prawa do danych i brak sekretów.
Walidator wymaga metadanych, ale nie otwiera wskazanych plików, nie uwierzytelnia
recenzenta i nie potwierdza prawdziwości raportu. Nie jest zamiennikiem odbioru.

## Ochrona podziału i eksport

Kontrole obejmują powtórzone ID, powtórzone klucze JSON, rodziny w różnych
splitach, identyczne prompty po normalizacji Unicode/wielkości liter/spacji
oraz powtórzone pary pytanie–odpowiedź. Nie wykrywają wszystkich parafraz;
przegląd rodzin i podobieństwa semantycznego pozostaje obowiązkowy.

Eksport wymaga wszystkich rekordów approved i co najmniej 200 train,
25 validation, 50 test. To bramka organizacyjna pilota, nie gwarancja jakości
ani reprezentatywności. Rozkład umiejętności wymaga osobnego odbioru.

Po przygotowaniu prawdziwego zbioru można dodać `--export-root` wskazujące
istniejącą przestrzeń `/home/marcin/ai-company-workspaces` lub jej podkatalog.
Powstaje nowy losowy katalog bez nadpisywania poprzednich wydań:

- `train.jsonl` — wyłącznie wiadomości do uczenia;
- `validation.jsonl` — osobne wiadomości do doboru ustawień;
- `test.jsonl` — osobne przypadki oceny końcowej;
- `reviewed-records.jsonl` — archiwum metadanych wszystkich rekordów;
- `manifest.json` — hashe wejścia i plików, liczniki i wersja.

**Trainer ma czytać wyłącznie train.jsonl do aktualizacji wag.** Nie należy
używać globu wszystkich JSONL ani archiwum reviewed-records jako treningu.
Eksport nie uruchamia treningu i nie zmienia modelu. Nie renderuje jeszcze
szablonu konkretnego tokenizera i nie sprawdza limitu tokenów; to następny etap.
Kontrola sekretów oraz praw do treści jest ręczna, bez gwarancji wykrycia
wszystkich danych prywatnych. Do repozytorium trafiają tylko syntetyczne próbki.

Testy: `.venv/bin/pytest -q tests/test_training_data.py`.
