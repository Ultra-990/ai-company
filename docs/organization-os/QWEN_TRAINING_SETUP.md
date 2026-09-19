# Środowisko QLoRA na lokalnym Linuksie

2026-09-13: właściciel wyraził zgodę na instalację i trening. Instalacja jest
oddzielona od aplikacji; nie zmieniono backendowej `.venv`, tagu Ollamy,
sterowników, konfiguracji hosta ani usług. Nie wymagała restartu.

## Zainstalowane środowisko

Katalog: `/home/marcin/ai-company-workspaces/qwen-training/venv`.
Python 3.12.3; Unsloth 2026.9.4, PyTorch 2.12.1+cu130, Transformers 5.5.0,
PEFT 0.20.0, TRL 0.24.0 i bitsandbytes 0.50.2.
Pełne rozwiązanie zależności: `config/qwen-training.lock.txt`.
Raport pip z adresami pakietów i hashami pobrań:
`/home/marcin/ai-company-workspaces/qwen-training/install-report.json`.
`pip check` nie wykazał konfliktów. Importy Unsloth, TRL, PEFT i bitsandbytes
przeszły; wystąpiły ostrzeżenia o przestarzałych wewnętrznych ustawieniach PyTorch.
Nie jest to jeszcze potwierdzenie działania pełnego treningu.

Lokalna kontrola CUDA: RTX 5090, compute capability 12.0, sterownik 595.84,
około 29.8 GiB wolnej pamięci GPU przy pomiarze. Pierwszą próbę ograniczyła
piaskownica (CUDA unavailable); kontrola poza nią zakończyła się powodzeniem.

Źródło checkpointu: [Unsloth Qwen3.8 27B 4-bit](https://huggingface.co/unsloth/Qwen3.8-27B-unsloth-bnb-4bit),
rewizja `8aa5f05d26b7205477066e1449e0af13f762a299`, metadane licencji Apache-2.0.
To osobne wagi do treningu, nie nadpisanie istniejącego modelu GGUF w Ollamie.
Pobierane są wyłącznie safetensors, konfiguracja i tokenizer, bez kodu Python
repozytorium modelu. Cache znajduje się w `qwen-training/hf-cache`.

## Narzędzie kontrolne

### Wynik pierwszej próby

Pobranie ukończone. Próba `smoke-bui0t39x` zakończyła się powodzeniem:
3 kroki, 19 922 944 parametrów adaptera, potwierdzona zmiana wag,
adapter zapisany. 73.532 s łącznie, 51.2587 s treningu; szczytowa alokacja
PyTorch około 20.5 GiB. Raport w katalogu próby ma jawne
`production_ready=false` i `quality_improvement_measured=false`.
To pomiar krótkich sekwencji 33–35 tokenów, nie estymacja wydajności na
długich plikach kodu. Trening korzystał z wolniejszej implementacji PyTorch
przy braku opcjonalnych bibliotek przyspieszających uwagę.

Pierwsza próba `smoke-xwpm_lql` zatrzymała się na kontroli kompletności
snapshotu; skrypt poprawiono i zachowano oba raporty. Szczegóły w dzienniku.

### Wywołania

`scripts/qwen_qlora_smoke.py` wymaga interpretera z powyższego środowiska.
Uruchomienie przez `.venv` aplikacji zostaje odrzucone. Polecenia z katalogu
repozytorium, każde osobno i sekwencyjnie:

```bash
/home/marcin/ai-company-workspaces/qwen-training/venv/bin/python scripts/qwen_qlora_smoke.py preflight
/home/marcin/ai-company-workspaces/qwen-training/venv/bin/python scripts/qwen_qlora_smoke.py download
/home/marcin/ai-company-workspaces/qwen-training/venv/bin/python scripts/qwen_qlora_smoke.py tokenize
/home/marcin/ai-company-workspaces/qwen-training/venv/bin/python scripts/qwen_qlora_smoke.py smoke
```

Każde wywołanie tworzy osobny katalog z raportem, również przy błędzie.
Download ma przypiętą rewizję, dwa wątki pobierania i kontrolę wolnego dysku.
Trening czyta lokalny snapshot w trybie offline, bez `trust_remote_code`.
Przed ładowaniem wymaga 26 GiB wolnego VRAM i 10 GiB dostępnego RAM.
Nie zatrzymuje sam cudzych procesów i nie wyładowuje modeli innych zadań.

Próba `smoke`: trzy kroki, tekst, batch 1, kontekst 256, rank 4,
learning rate 1e-5, checkpointing, cztery wątki CPU. Ma limit czasu 20 minut;
pierwsze kompilacje kerneli mogą go przekroczyć. Cztery własne przykłady
dodawania liczb służą wyłącznie sprawdzeniu mechanizmu aktualizacji wag.
Nie wykorzystują sześciu nieodebranych kandydatów firmowych ani zbioru testowego.
Sprawdzane są długości tokenizacji, skończona wartość loss, liczba kroków,
zmiana próbki parametrów LoRA oraz zapis adaptera.

Wynik trafia do `adapter-NOT-FOR-PRODUCTION`. Nie jest automatycznie scalany,
eksportowany do Ollamy ani przypisywany agentom. Nawet wynik `passed` oznacza
tylko techniczną próbę, **nie poprawę jakości modelu w realizacji zleceń**.
Kontrola danych do właściwego treningu pozostaje niezależna:
[format i bramka danych](../../datasets/qwen/README.md).

## Odtwarzanie instalacji

Nie wykonywać poniższej instalacji w środowisku aplikacji. Dla nowego,
oddzielnego Python 3.12 na zgodnym Linuksie można zainstalować wersje z lockfile.
Dokładne pobrane koła i ich hashe są w install-report.json; lockfile jest
zapisem wersji, nie kompletną gwarancją odtwarzalności różnych sterowników.
W przypadku błędu zgodności najpierw analizujemy środowisko treningowe;
nie aktualizujemy automatycznie sterowników lub bibliotek backendu.

Aktualne wyniki prób i ewentualne błędy są zapisywane w [dzienniku](../WORK_LOG.md).
