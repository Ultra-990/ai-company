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

Pozostałe cele właściciela są w `config/upwork-learning-targets.json`:
fotografie wnętrz/organizacja zasobów, edytowalna ulotka PDF/wektor,
cztery infografiki produktowe i identyfikacja restauracji. To katalog
wymagań i kryteriów prób, nie uruchomiona kolejka produkcyjna. Brak jeszcze
prób specyficznych dla tych czterech zleceń i materiałów wejściowych.
