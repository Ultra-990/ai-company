# Trening z rzeczywistym obrazem i odpowiedzią lokalnego modelu

21.09.2026 sprawdzono wejście multimodalne i wykonano trzy rzeczywiste
aktualizacje osobnego adaptera. To próba mechanizmu na jednym odebranym
przykładzie ze [szkoły wnętrz](INTERIOR_SCHOOL.md), nie pomiar jakości usługi.
Tekst, obraz i poprawka pochodzą z lokalnych modeli. Asystent napisał
infrastrukturę, maskowanie danych, kontrole i ocenę — nie poprawiał realizacji.

## Kontrola wejścia

`scripts/check_vision_training_inputs.py BUNDLE --run` sprawdza źródłowe
oceny, odpowiedzi i PNG, następnie uruchamia procesor w istniejącym osobnym
środowisku ML. Bez wag modelu, CUDA i dostępu do sieci. Domyślnie bez `--run`
weryfikuje wyłącznie paczkę. Pełna rozmowa pozostaje powiązana z obrazem.

`VisionResponseCollator` obsługuje jeden przykład bez obcinania. Sprawdza
zgodność szablonu odpowiedzi, granicę tokenów promptu, obecność końca tury,
zgodność liczby tokenów obrazu z siatką i niezmienione piksele podczas
przetwarzania prefiksu. Wszystkie tokeny instrukcji i obrazu mają etykiety
`-100`; nadzorowana jest wyłącznie odpowiedź. Brak obrazu powoduje błąd.

Rzeczywiste raporty CPU `vision-input-audit-r_h02yvu` i po wydzieleniu
testowalnej funkcji maskowania `vision-input-audit-py_lvbr1`:

- procesor Qwen3VLProcessor z przypiętego snapshotu;
- 1552 tokeny, 1283 zamaskowane, 269 nadzorowanych;
- 384 tokeny obrazu, siatka `[1,32,48]`, piksele float32 `[1536,1536]`;
- dokładny sufiks odpowiedzi i odrzucenie brakującego obrazu potwierdzone;
- CUDA niezainicjalizowana, bez treningu na etapie tego audytu.

## Rzeczywiste aktualizacje adaptera

Protokół `config/vision-sft-input-pilot-001.json` przypina jeden zatwierdzony
rekord i trzy kroki. `scripts/train_vision_input_pilot.py --run` ponownie
sprawdza dane i zasoby. Zwykłe uruchomienie nie ładuje wag i nie trenuje.
Jest to jawny protokół integracyjny; nie zmienia bramki produkcyjnej 200/25/50
ani nie nadaje małej paczce statusu gotowego zbioru treningowego usługi.

Model: `unsloth/Qwen3.8-27B-unsloth-bnb-4bit`, rewizja
`8aa5f05d26b7205477066e1449e0af13f762a299`. Pełna ścieżka obraz–tekst,
zamrożony enkoder obrazu, QLoRA wyłącznie w części językowej, r4/alpha8,
batch 1, kontekst 4096, AdamW, lr 1e-5. Oryginalne wagi pozostają bez zmian.

Pierwszy przebieg `vision-input-sft-ow7veubi` zakończył się przed pierwszą
aktualizacją: 352 warstwy traciły stan kwantyzacji podczas ładowania pełnego
modelu. Błąd mnożenia `[1552,5120]` przez `[1,15728640]` zachowany w logu.
Nagłówek oryginalnego safetensors **zawiera** potrzebne metadane, więc nie
uznano pliku za pozbawiony danych na podstawie samego wyjątku.

W zainstalowanym Transformers 5.5.0 funkcja `get_model_conversion_mapping`
zbiera także konwersję podmodułu `qwen3_5_text`, skracając
`model.language_model` do `model` wewnątrz pełnego VLM. Proces ładowania
wyłącza tymczasowo tylko tę rozpoznaną regułę i przywraca rejestr w `finally`.
Bez edycji bibliotek lub checkpointu. Kontrola stanu wszystkich warstw
kwantyzowanych następuje przed treningiem. Obejście odrzuca inne wersje
Transformers i nierozpoznaną regułę; przyszła aktualizacja wymaga nowej oceny.
Podobny problem oraz wpływ wersji opisuje
[upstream PR 11016](https://github.com/unslothai/unsloth/pull/11016).
Tutejsze rozpoznanie oparto również na lokalnym kodzie, nagłówku i próbie.

Drugi przebieg `vision-input-sft-uiau78tj` ukończony:

- 352 warstwy ze stanem kwantyzacji, rejestr konwersji przywrócony;
- 29 181 952 trenowalne parametry LoRA; reszta modelu zamrożona;
- trzy kroki, loss na tym samym przykładzie 0.361193 → 0.359410 → 0.358137;
- trzy wywołania rzeczywistego modułu obrazu, maska 269 tokenów odpowiedzi;
- parametr LoRA_B zmieniony, adapter zapisany, całość 51.091 s;
- peak allocated VRAM 23 602 985 472 bajty;
- safetensors 116 876 728 bajtów, 992 tensory LoRA, hash ponownie sprawdzony:
  `1ead1a8413150f3b7d172d0db2e0e654b7ac56926fffff702c7c1ab5e44b5f52`.

Nie zmieniono routingu Ollamy ani nie wdrożono adaptera. Spadek błędu na
jednym przykładzie treningowym nie dowodzi poprawy na nowych obrazach.
Nie wykonano w tym protokole generacji przed/po ani niezależnego egzaminu.
Potrzebne są większy sprawdzony zbiór, inne rodziny walidacji/testu oraz
porównanie jakości bazy i adaptera w tym samym środowisku.

52 testy infrastruktury zaliczone, w tym maskowanie, brak cichego obcinania,
niepoprawna liczba tokenów obrazu, podmiana danych, ograniczenia protokołu
i przywracanie reguły konwersji po błędzie. Rzeczywisty trening powyżej
sprawdził dodatkowo obliczenia obrazu, gradienty i zapis zmienionych wag.
