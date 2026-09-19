# Porównanie lokalnych wykonawców i przydział ról

## Wynik rzeczywistego pilota — 19.09.2026

| Zamrożona próba | Qwen3.8:27b | gpt-oss:20b |
| --- | --- | --- |
| Naprawa kodu, testy w izolacji | 4/4 | 3/4 |
| Analityk zakresu | 3/3 | 3/3 |
| Kierownik zadań | 3/3 | 2/3 |
| Kontroler dowodów | 2/3 | 1/3 |
| Przygotowanie przekazania | 3/3 | 3/3 |
| Razem decyzje | 11/12 | 9/12 |

To wynik jednej kompletnej serii na konfigurację, nie ranking ogólnej
inteligencji. Publiczny zestaw jest mały, bez świeżego prywatnego holdoutu;
nie mierzy wyglądu stron, obrazów, wideo, muzyki ani pełnego projektu.
Cały przebieg trwał 65.699 s dla Qwena i 60.822 s dla gpt-oss, ale obejmuje
ładowanie, preflight i kontenery — nie jest miarą szybkości generowania.

Pierwsza seria Qwena została przerwana po 4/4 naprawach i 6/6 rozpoczętych
decyzjach przez ValueError kontroli zasobów. Ówczesny raport nie identyfikował
konkretnej przyczyny; nie przypisujemy jej modelowi ani najemcy. Dodano stałe,
bezpieczne kody przyczyn preflight. Po osobnym potwierdzeniu wolnych zasobów
wykonano nową pełną serię; tabeli nie złożono z najlepszych odpowiedzi.
Oba raporty Qwena pozostają zachowane. Nie było ponawiania błędnych odpowiedzi
wewnątrz serii ani podpowiadania oczekiwanego wyniku.

Przegląd głównego agenta objął kod czterech napraw i wszystkie 12 uzasadnień
obu pełnych serii. Uwagi:

- gpt-oss połączył rozłączne przedziały przez warunek `end + 1`; niezależne
  testy ujawniły błąd. Nie poprawiano jego odpowiedzi przed punktacją.
- Oba modele wybrały oczekiwanie na dowody zamiast zlecenia ponownych testów
  dla innej wersji aplikacji. Rozpoznały nieaktualny raport, ale nie wybrały
  wymaganej czynności. To nie było zaakceptowanie wadliwego wydania.
- gpt-oss dodatkowo nie eskalował cyklu zależności i wybrał ponowny test
  zamiast odrzucenia wyniku z rzeczywiście niezaliczonym testem.
- Dwa uzasadnienia gpt-oss były angielskie mimo polskiej instrukcji;
  punktacja decyzji tego nie wykrywa. Qwen odpowiedział po polsku.
- Zaliczona implementacja średniej kroczącej Qwena ma złożoność O(n·window).
  Próba potwierdza poprawność dla danych testowych, nie wydajność dużych danych.

Surowe raporty mają `reason_reviewed=false`, ponieważ evaluator nie wykonuje
oceny semantycznej. Niniejsza notatka dokumentuje późniejszy przegląd głównego
agenta, bez zmiany oryginalnych raportów i ich hashy.

### Decyzja dotycząca podziału pracy

| Funkcja | Wybór po tym pilocie | Warunek |
| --- | --- | --- |
| Kod i naprawy | Pozostawić Qwen jako dotychczasowego wykonawcę | Niezależne testy, ograniczony zakres |
| Analiza i planowanie | Qwen jako kandydat bazowy; gpt-oss wariant porównawczy | Rozszerzyć próby przed zmianą routingu |
| Kontrola jakości i wydanie | Reguły systemu + testy + niezależny odbiór | Żaden model nie zatwierdza sam swojej pracy |
| Projekt wizualny stron | Osobny profil projektanta i frontendowca | Jeszcze brak wizualnego benchmarku porównawczego |
| Grafika, wideo i muzyka | Specjalistyczne modele i workflow mediów | Ten pilot ich nie oceniał; gpt-oss nie przyjmuje obrazów |

Rola agenta nie wymaga osobnych wag. Jeden Qwen może pracować kolejno z
różnymi profilami, pamięcią zadania i uprawnieniami; drugi model dodajemy,
gdy pomiar potwierdzi korzyść. Oddzielna sesja tego samego modelu nie zapewnia
niezależności błędów, dlatego same wzajemne opinie agentów nie zastępują testów.
Na jednej karcie modele uruchamiamy kolejno. Nie zmieniono routingu produkcji,
uprawnień, konfiguracji właściciela ani wag. Nie rozpoczęto fine-tuningu.

Następny etap: osobne, nowe zadania frontend/design z testami interakcji,
responsywności, dostępności i przeglądem screenshotów. Przykładów tego pilota
nie wolno kopiować do treningu. Korekty treningowe muszą korzystać z innych
rodzin zadań; dane validation/test muszą pozostać odseparowane.

### Identyfikacja dowodów

Raporty lokalne w `/home/marcin/ai-company-workspaces/model-comparisons/`:

- `gpt-oss-54e_23dk/report.json`, SHA-256
  `2ffa11921b843e869a14e0f25d3c616c860738458c2d4a15036f2a98257ee449`.
- `qwen3.8-iqqqw0dh/report.json` (niepełny), SHA-256
  `4a444d2a68db16a4ad14b0cc058c6981200d1bf055228d9f79438b55045fd18e`.
- `qwen3.8-kgjfa8cj/report.json` (pełny), SHA-256
  `7554b32805547876cf63976a793753f7f670f8b7e327865c12699ae40d463a55`.

Digest Qwena: `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`.
Digest gpt-oss: `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7`.
Zestaw napraw: `fb5f375568d738d238d8f5a9cc5a33923b82cea1150780d884835bab7a7ce41d`.
Zestaw ról: `611d1d2fbaaae6071b81f4b7e108fcc3f45e353622e1e12c86f6d053e03d5578`.

## Aktualizacja 19.09.2026: Qwen i lokalny gpt-oss

Właściciel potwierdził koniec wynajmu (AGENTS.md). Poniższy dawny zakaz
dotyczy historii z 13.09, nie aktualnej zgody. Przed każdą próbą nadal
sprawdzamy puste kontenery, Ollamę, kolejkę ComfyUI i dostępną pamięć GPU.
Brak nasłuchu ComfyUI jest dopuszczalny; timeout, brak uprawnień lub
nieznana odpowiedź blokują pracę. Nie uruchamiamy ani nie zatrzymujemy usług.

Lokalny inwentarz zawiera Qwen oraz `gpt-oss:20b` i zmodyfikowany alias
`gpt-oss-20b-local:latest`. Porównujemy canonical `gpt-oss:20b`, nie alias
o niezweryfikowanym szablonie. Gemma nie jest zainstalowana; nie ogłaszamy
wyniku jej porównania. W tej serii niczego nie pobierano i nie trenowano.

Protokół v2: 4 naprawy, 12 decyzji, po jednej próbie. Oba modele mają
kontekst 8192, 6 wątków, 120 s, maks. 2400 tokenów naprawy / 1200 decyzji,
sampling bounded-default.v1 (temperature 0.2), keep_alive 0 i przypięty
digest. gpt-oss ma `think=low`, Qwen dotychczasowe `think=false`.
To porównanie konfiguracji użytkowych, nie izolacja samej architektury.
Budżet gpt-oss obejmuje również rozumowanie; końcowa odpowiedź jest
oddzielona od pola thinking. Nie zapisujemy śladu rozumowania w raportach.

[Oficjalna karta gpt-oss](https://developers.openai.com/api/docs/models/gpt-oss-20b)
opisuje poziomy low/medium/high i brak wejścia obrazowego.
[Ollama](https://docs.ollama.com/capabilities/thinking) wymaga poziomów
zamiast boolean dla tej rodziny. Wskazania OpenAI Docs wpłynęły na jawny
parametr porównania; nie jest to płatne OpenAI API ani model GPT-6.
gpt-oss nie oceni screenshotów jako model wizualny.

Porównanie nie zmienia `config/local_inference.json`, nie przyznaje agentom
nowych uprawnień ani samodzielnego odbioru. Sam wynik decyzji nie potwierdza
polskiego języka, dobrego uzasadnienia lub bezpiecznej realizacji projektu.
Przypadki pozostają zastrzeżone do ewaluacji i nie trafiają do treningu.

```bash
.venv/bin/python scripts/compare_local_models.py --model gpt-oss:20b --run
.venv/bin/python scripts/compare_local_models.py --model qwen3.8:27b --run
```

Te polecenia wykonujemy kolejno, nigdy równolegle. Szczegóły v1 poniżej
(1200/600 tokenów) pozostają zapisem starszego protokołu.

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
