# Zapis projektu na GitHub i nadzorowana praca modeli

Cel: `git@github.com:Ultra-990/ai-company.git`. Odczyt 19.09.2026 potwierdził
repozytorium publiczne i dostęp SSH. Nie zmieniamy widoczności ani nie scalmy
automatycznie do main. Commit kontrolny utrwala zastany kod wielu etapów;
nie oznacza, że wszystkie funkcje są gotowe do produkcji.

## Co wysyłamy

Kod, testy, dokumentację, lockfile zależności, licencje dołączonych bibliotek,
przykładowe wyłączone konfiguracje i jawnie syntetyczne zbiory. Wyniki testów
podajemy wraz z ograniczeniami. Dane publicznych benchmarków nie są prywatnym
holdoutem. Zapis lokalny i potwierdzenie push to oddzielne wyniki.

Nie wysyłamy `.env`, kluczy, tokenów, baz i kopii SQLite (również w podfolderach),
WAL/SHM, logów operacyjnych, historii klientów, swapów edytora, wag modeli
ani aktywnych profili wykonania. Niczego z tych danych nie usuwamy z dysku.
Kod przykładowych konfiguracji jest w `config/*.example.json` i
`config/comfyui-model-paths.example.yaml`. Konfiguracja lokalna wymaga osobnego
przypięcia modelu/obrazu i sprawdzenia izolacji; klon nie włącza GPU/runnera.

## Przed każdym checkpointem

1. Sprawdź `git status`, remote i istniejący index; zachowaj pracę innych.
2. Wybierz jawnie pliki do staged. Sprawdź brak binarnych baz, sekretów,
   kopii, symlinków do prywatnych danych i niezamierzonych dużych plików.
3. Przejrzyj zmiany, uruchom testy odpowiednie do zakresu i `git diff --cached --check`.
4. Przeskanuj dokładny snapshot indexu oraz historię commitów skanerem
   sekretów. Raport trzymaj prywatnie, z redakcją wartości. Wynik skanera
   nie zastępuje przeglądu danych osobowych i praw do materiału.
5. Commit z uczciwym opisem etapu. Push bez force na gałąź roboczą.
6. Porównaj lokalne HEAD ze zdalnym SHA. Nie zgłaszaj „zapisano na GitHub”,
   jeżeli push lub sprawdzenie nie powiodły się.

Do kontroli wybrano upstream Gitleaks 8.30.1. Archiwum Linux x64 zweryfikowano
względem digestu oficjalnego wydania:
`551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`.
Narzędzie lokalne poza repozytorium; bez demona, uploadu źródeł i zmian usług.
[Upstream](https://github.com/gitleaks/gitleaks),
[wydanie](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1).

## Delegowanie do lokalnych modeli

Każde podzadanie ma zakres, ograniczenia, wymagany format i kryteria kontroli.
Model proponuje zmianę, nie otrzymuje klucza SSH, sekretów ani dostępu do
produkcji. Główny agent przegląda diff, porównuje wynik z wymaganiami,
uruchamia niezależne testy i dopiero wtedy włącza zmianę. Ograniczone próby,
zachowanie porażek, niezmienne testy regresji, brak samodzielnego odbioru.
Do mechanicznego skanowania sekretów używamy narzędzia, nie opinii Qwena.
