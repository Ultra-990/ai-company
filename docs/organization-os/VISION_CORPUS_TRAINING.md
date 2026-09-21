# Trening zbioru obraz–tekst i wspólna walidacja

## Wynik pierwszego eksperymentu — 21.09.2026

**Brak wykazanej poprawy: baza 23/24 → adapter 23/24 w dokładnych naprawach;
pełne odtworzenie 0/1 → 0/1. Adapter nie został wdrożony.** Porównanie odbyło
się w tym samym środowisku HF, z identycznymi tokenami, pikselami i dekodowaniem.

Próba `vision-corpus-sft-cs6ptj9i` wykonała 18 aktualizacji na wszystkich 71
przykładach, bez powtórzeń. Potwierdzono 71 rzeczywistych wywołań modułu obrazu,
zmianę parametru adaptera i zapis wag. Trenowano 29 181 952 parametry LoRA,
szczytowa zajętość VRAM 22,27 GiB. Ładowanie, trening i 50 odpowiedzi walidacyjnych
łącznie 431,441 s; późniejsza ocena i audyt są poza tym czasem.

SHA-256 adaptera: `d8db240a091e2aadd4848ef047c353ccb67ba53ad2a5ba64a86945b43d1f8400`.
Niezależnie odtworzono 50 odpowiedzi i sprawdzono 50 rzeczywistych PDF.
`comparison.json` ma SHA-256
`e0742ef8260fef82a691f136232b8d95c7d9c8a471ffe2281dedc8752463a719`;
`independent-audit.json`:
`0e83a4857b3ee4f5db9f6ce59ce26eed7d66bcc82850f967ecfb77c76821ac5e`.
Wszystkie te artefakty pozostają w prywatnym katalogu próby.

W obu fazach nagłówek naprawiono do 45 zamiast 46. Pełne odtworzenia mają
identyczne bajty odpowiedzi i identyczne PNG: tekst 8/8 poprawny, lecz błąd
geometrii nagłówka 12,168 i podtytułu 28,906 przekracza limit 12. Obraz obejrzano
niezależnie. Nie poprawiano produktu ani progów. Dalsza praca wymaga danych
obejmujących pełne realizacje i trudniejsze błędy; powtarzanie podobnych
drobnych napraw nie wykazało przeniesienia umiejętności na ten egzamin.

`scripts/train_vision_corpus.py` rozszerza wcześniejszy test jednego przykładu
na ograniczony zbiór niezależnie sprawdzonych rozmów lokalnego modelu.
Protokół `config/vision-corpus-research-001.json` jest eksperymentem badawczym,
nie automatycznym treningiem produkcyjnym. Nie zmienia minimalnych wymagań
zbioru produkcyjnego, aktywnego routingu ani reguł zatwierdzania modelu.

## Dane i ograniczenia eksperymentu

Wejście pochodzi z zapisanego stanu learning-autopilot. Każdy pakiet jest
ponownie sprawdzany względem niezależnego odbioru, oryginalnych rozmów,
rzeczywistych obrazów oraz wcześniejszego audytu procesora i maski odpowiedzi.
Powtórzone identyfikatory, inne podziały niż train, brak aktualnego odbioru
i wspólne rodziny lub obrazy między nauką a walidacją są odrzucane.

Pierwsza przygotowana partia: 71 przykładów w dziewięciu pakietach,
cztery rodziny i tylko cztery różne obrazy. Większość danych dotyczy napraw atrybutów SVG; jeden przykład
dotyczy opisu wnętrza. To ograniczony i nierównomierny zbiór, który nie
reprezentuje wszystkich pięciu zamówionych usług ani całej pracy projektowej.

Protokół dopuszcza 2–128 sprawdzonych przykładów, jeden przebieg i kontekst
4096 bez ucinania danych. To granice jawnej próby badawczej, nie obniżenie
produkcyjnego minimum danych. Kolejność ustala seed 3407; każdy przykład
występuje dokładnie raz. Batch1 i akumulacja do czterech przykładów dają
18 aktualizacji dla 71 rozmów; ostatnia grupa zawiera trzy rozmowy i jest
normalizowana przez trzy. Model uczy się tylko tokenów odpowiedzi, a obrazy
są przetwarzane także podczas rzeczywistych wywołań treningowych.

Trenowane są wyłącznie językowe parametry LoRA (r4, alpha8, lr1e-5).
Enkoder obrazu i bazowe wagi pozostają zamrożone. Proces zapisuje liczbę
wywołań modułu obrazu, nadzorowane tokeny, hashe wejść/etykiet, straty,
liczbę aktualizacji i dowód zmiany parametru adaptera. Nie wykonuje kodu
modelu lub klienta. Korzysta z przypiętego lokalnego checkpointu HF i już
sprawdzonego środowiska, bez pobierania lub aktualizowania zależności.

## Porównanie wersji

Po zapisaniu adaptera ten sam proces wykonuje zamrożony egzamin walidacyjny:
25 odpowiedzi z wyłączonym adapterem i 25 z włączonym. Obie fazy otrzymują
identyczne prompty, tokeny i piksele, z wyłączonym losowaniem. Zgodność ich
hashy jest warunkiem oceny. Nie stosuje się feedbacku i ponownych prób ucznia.

Po zwolnieniu GPU oddzielny etap aplikacyjny renderuje odpowiedzi i sprawdza
je według istniejących progów egzaminu. Naprawy atrybutów i odtworzenie całej
ulotki mają osobne wyniki. Obniżenie straty treningowej lub zapis adaptera
nie oznacza poprawy jakości. Niezależna walidacja nie jest końcowym testem
ani kwalifikacją pięciu usług. Wyniku HF nie porównuje się bezpośrednio
z wcześniejszym Ollama, które wymuszało schemat JSON innym dekoderem.

```bash
.venv/bin/python scripts/train_vision_corpus.py --state /prywatny/state.json \
  --exam /prywatny/egzamin/report.json
```

Bez `--run` odbywa się wyłącznie kontrola danych. Jawne `--run` uruchamia
ograniczony proces w odrębnym środowisku ML i po jego udanym zakończeniu
automatycznie ocenia kompletne odpowiedzi. Samo `--assess KATALOG_PRÓBY`
służy do oceny wcześniejszego zakończonego procesu, który jeszcze nie ma
zapisanej oceny. Dostępność zasobów jest sprawdzana
przed startem; cudze procesy pozostają nienaruszone. Wagi mają nazwę
`adapter-RESEARCH-NOT-FOR-PRODUCTION` i nie trafiają do repozytorium.

Końcowe testy: `.venv/bin/pytest -q` — **1648 passed, 21 skipped**, 85,08 s.
