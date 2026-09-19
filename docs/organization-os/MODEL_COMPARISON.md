# Porównanie lokalnych wykonawców: Qwen i Gemma

**Wstrzymane:** właściciel ponownie potwierdził aktywny wynajem GPU Vast.ai
2026-09-13. Pobieranie Gemmy przerwano; nie wykonano porównania ani treningu.
Poniższy protokół jest przygotowany, lecz nie wolno uruchamiać go podczas wynajmu.

## Cel i źródła (sprawdzono 2026-09-13)

Właściciel wskazał Gemma4 31B jako kandydata do programowania. Oficjalna
[karta Google](https://ai.google.dev/gemma/docs/core/model_card_4) opisuje
generowanie i naprawę kodu, role systemowe, wejście tekst/obraz oraz licencję
Apache2.0. To deklaracje producenta, nie wyniki na naszym sprzęcie.

[Lokalny wariant Ollama](https://ollama.com/library/gemma4:31b) ma tag
`gemma4:31b`, kwantyzację Q4_K_M i około20GB. Nie używać `:31b-cloud`.
Zalecane ustawienia producenta: temperature1,top_p0.95,top_k64. W teście
używamy profilu `gemma4-default.v1`, a dla dotychczasowego Qwena istniejącego
`bounded-default.v1` (temperature0.2). Porównujemy więc konfiguracje użytkowe,
nie izolowany wpływ samej architektury przy identycznym samplerze.

## Protokół

`scripts/compare_local_models.py --model MODEL --run` uruchamia kolejno:

- Cztery zamrożone przypadki naprawy kodu: najpierw rzeczywiście niezaliczone
  testy, potem propozycja modelu, niezależnie zachowane testy po poprawce.
  Kod jest uruchamiany wyłącznie przez istniejący ograniczony runner Docker.
- Dwanaście zamrożonych decyzji dla analityka, kierownika, kontrolera
  i przekazania projektu. Walidacja JSON i oczekiwanej decyzji/celu; uzasadnienia
  wymagają osobnego przeglądu, nie są automatycznie oceniane semantycznie.

Nie przekazujemy oczekiwanych odpowiedzi modelowi ani nie uczymy na przypadkach
ewaluacyjnych. To syntetyczny publiczny pilot, nie dowód wykonania dowolnego
zlecenia klienta lub audyt bezpieczeństwa. Jedna próba na przypadek.

Oba modele: kontekst8192, think:false, keep_alive:0,6wątków,
limit120s,1200tokenów dla napraw i600 dla decyzji. Przed każdym przypadkiem
sprawdzamy pustą Ollamę, pustą kolejkę ComfyUI i co najmniej24GiB wolnejVRAM.
Skrypt nie zatrzymuje procesów ani nie zwalnia modeli automatycznie.
Raport zawiera pełny digest modelu, checksumy zestawów i wyniki każdej próby.
Timeout/błąd infrastruktury przerywa serię bez automatycznego ponowienia.

Raporty: `/home/marcin/ai-company-workspaces/model-comparisons`.
Model przegrywający nie jest usuwany. Wagi Qwen i produkcyjne ustawienia
`config/local_inference.json` pozostają niezmienione w fazie oceny.
Trening dopiero po wskazaniu powtarzalnego błędu, przygotowaniu osobnych
danych i pomiarze względem bazowego modelu; instalacja nie jest fine-tuningiem.
