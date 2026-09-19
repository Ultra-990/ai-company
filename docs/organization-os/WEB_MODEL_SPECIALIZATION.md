# Specjalizacja modeli: strony premium i realizacja aplikacji

Decyzja właściciela, 19.09.2026: najpierw dostrojenie i ocena modeli, potem
strona demonstracyjna. Celem jest oryginalna jakość wizualna i funkcjonalna,
nie tylko poprawny kod. Nie obiecujemy miejsca na Awwwards ani poziomu
modelu frontier na podstawie jednego treningu.

## Ustalenia ze źródeł

- [Unsloth: Qwen3.8 training](https://unsloth.ai/docs/models/qwen3.8/train):
  QLoRA od 24 GB, osobny adapter, ten sam tokenizer i EOS przy eksporcie.
  To deklaracja upstream; długi kontekst i kod wymagają lokalnego pomiaru.
  Rodzina używa architektury `qwen3_5` — taka nazwa w lokalnym config.json
  nie jest sama w sobie dowodem pomylenia checkpointów.
- [TRL 0.24 SFT](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer):
  loss tylko odpowiedzi wymaga poprawnego maskowania; `assistant_only_loss`
  wymaga odpowiednio oznaczonego szablonu. Lokalny szablon nie ma bloków
  generation. Nie włączamy tej flagi na ślepo. Nowy audyt sprawdza jawny
  prefiks, granicę tokenów, treść odpowiedzi i zakończenie tury.
- [Awwwards](https://www.awwwards.com/about-us/) opisuje ocenę przez jury
  projektantów, developerów i agencji. Ocena estetyczna nie wynika z pytest.
  Strona szczegółowych kryteriów nie została pobrana (timeout); nie
  traktujemy wtórnych opisów wag jako zweryfikowanej bieżącej specyfikacji.
- Referencje właściciela: [Otsuka](https://otsuka-air.jp/),
  [Cipher](https://cipher.tv/), [Sharplink](https://www.sharplink.com/).
  Dostęp do tekstu stron nie jest pełną kontrolą animacji/przeglądarki.
  To inspiracje, nie licencjonowany zbiór treningowy. Nie pobrano ich
  zasobów do treningu ani nie skopiowano kodu lub identyfikacji wizualnej.

## Co stroimy

Pierwszy kandydat: projektowanie i realizacja webowa Qwena. Oddzielne role
projektanta, implementatora i recenzenta mogą używać tej samej bazy; nie
oznacza to potrzeby trzech pełnych kopii wag ani niezależności ich błędów.
Zewnętrzne testy i odbiór wizualny pozostają konieczne.

Roboczy skład 200 przykładów train (cel kuracji, nie automatyczny licznik):

| Zakres | Liczba | Warunek odbioru |
| --- | ---: | --- |
| Brief, brakujące informacje, zakres | 20 | Przegląd zgodności z wymaganiami |
| Art direction, typografia, layout, interakcje | 40 | Konkretna specyfikacja i krytyka projektu |
| Frontend: responsywność, stany, dostępność | 60 | Kod + niezależne testy + kontrola w przeglądarce |
| Backend, kontrakty i integracja w dopuszczonym profilu | 30 | Testy API i negatywne przypadki |
| Naprawy na zamrożonych testach | 30 | Ten sam test przed i po poprawce |
| Dowody, przekazanie i ograniczenia | 20 | Zgodność z rzeczywistymi raportami |

25 validation i 50 test tworzymy z innych rodzin projektów, nie jako
parafrazy train. Najpierw przypisanie rodzin, potem przykłady. Obecne publiczne
próby napraw są regresją, a nie prywatnym końcowym testem. Nie sumujemy
wielokrotnie wygenerowanych wersji tego samego przypadku.

Aktualne 12 przykładów dotyczy scope/evidence/repair, nie stanowi takiego
zbioru. Nowe propozycje projektowania muszą przejść przegląd. Poprawny JSON
nie oznacza dobrego projektu. Wadliwe propozycje zachowujemy z przyczyną
odrzucenia; nie uczymy na nich jako na odpowiedziach wzorcowych.

## Kolejność eksperymentów

1. Zamrozić rodziny i kryteria oceny przed doborem parametrów.
2. Uzupełnić i odebrać dane; używać własnych lub jawnie dozwolonych treści.
3. Sprawdzić tokenizer, EOS, maskę i długości wszystkich przykładów. Długie
   przykłady dzielić semantycznie lub zwiększać kontekst po pomiarze VRAM,
   nigdy cicho nie ucinać końca odpowiedzi/kodu.
4. Zmierzyć bazę na walidacji. Parametry generacji, kontekst, tryb myślenia
   i narzędzia są częścią punktu odniesienia, nie domyślną stałą jakości.
5. Przeprowadzić ograniczony trening osobnego adaptera. Rank 8/16 i learning
   rate 5e-5/1e-4 to kandydaci do sekwencyjnych prób, nie wybrany optimum.
   Batch 1, akumulacja gradientu i czas/kontekst dobrane po pomiarze pamięci.
   Żadnych automatycznych aktualizacji sterowników ani bazowych wag.
6. Wybrać na walidacji, następnie raz ocenić na odłożonym teście. Porównać
   bazę, bazę z lepszymi ustawieniami i adapter na tych samych warunkach.
7. Wdrożyć tylko przy rzeczywistej poprawie bez regresji krytycznych funkcji.
   Zachować bazę i możliwość powrotu; przetestować ponownie eksport GGUF.
8. Dopiero potem przygotować stronę pokazową i aplikację demonstracyjną.

Pierwszy audyt i propozycje są tekstowe/non-thinking. Nie dowodzą poprawy
rozumowania ani widzenia. Zachowanie tych zdolności wymaga osobnych prób;
nie generujemy fikcyjnych uzasadnień ani nie zgadujemy łańcucha myśli.
Dostrajanie oceny screenshotów wymaga własnego/licencjonowanego materiału
wizualnego, a nie samego zbioru JSON z opisami.

## Odbiór stron

- Hierarchia, typografia, spójność, oryginalność i cel marki: porównanie
  anonimowych wersji na tych samych briefach, z uzasadnieniem oceny.
- Desktop, telefon, klawiatura, dotyk, reduced motion, jasny/ciemny motyw:
  zrzuty i rzeczywiste ścieżki użytkownika, nie sam odczyt HTML.
- Żaden efekt nie zasłania nawigacji; brak WebGL nie usuwa treści.
- Nieaktywne funkcje są jawnie opisane; brak pozornych płatności, wysyłek
  formularza czy wymyślonego postępu generowania.
- Wydajność oceniana na ustalonym urządzeniu/sieci oraz w profilowaniu;
  wynik laboratoryjny nie jest gwarancją danych terenowych.
- Naprawy nie mogą osłabiać kryteriów/testów ani ukrywać błędów.

Generatory mediów później wykorzystają osobne modele i workflow; dostrojenie
LLM do planowania stron nie trenuje automatycznie syntezy muzyki lub wideo.

## Narzędzia przygotowane teraz

```bash
/home/marcin/ai-company-workspaces/qwen-training/venv/bin/python scripts/check_sft_tokenization.py datasets/qwen/specialization-batch-001.jsonl datasets/qwen/repair-batch-001.jsonl
.venv/bin/python scripts/draft_web_design_training.py
```

Audyt działa offline/CPU i nie importuje wag. Druga komenda bez flagi pokazuje
tylko liczbę przypadków. `--generate` przygotowuje maksymalnie sześć propozycji
na lokalnym Qwenie (train/pending), sekwencyjnie, bez kodu wykonywanego na hoście.
To przygotowanie materiału, **nie uruchomienie treningu**. `training_ready`
w audycie pozostaje false: tokenizacja sama nie zatwierdza trenera ani danych.
