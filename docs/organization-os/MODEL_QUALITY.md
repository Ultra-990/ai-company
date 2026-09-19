# Jakość lokalnego modelu — 2026-09-13

## Decyzja

Na tym etapie pozostaje lokalny `qwen3.8:27b`, przypięty digestem w konfiguracji.
Nie pobrano nowego modelu, nie przeprowadzono treningu ani nie zmieniono wag.
Wdrożono poprawkę integracji: analiza Upwork używa schematu JSON przy generowaniu,
po czym przechodzi istniejącą walidację i nadal wymaga odbioru. Jest to ograniczenie
klasy błędów formatu, nie gwarancja prawdziwości odpowiedzi.

Sprzęt odczytany lokalnie: RTX 5090, 32607 MiB VRAM; około 30 GiB RAM.
Model zajmuje około 17.74 GB na dysku (Q4_K_M), ma 27.3B parametrów.
Metadane identyfikują Qwen3.8, wersję 0814, architekturę qwen35. Sama nazwa
architektury nie oznacza, że zainstalowano model Qwen3.5. Model korzysta
z renderera Ollamy; sam `TEMPLATE {{ .Prompt }}` nie dowodzi wadliwego szablonu.

## Co wykryto

- Sprzeczny format raportu i krótkiego zadania: poprawiony w profilach działów.
- Samo polecenie „najwyżej N elementów” bywa ignorowane.
- Niska temperatura nie zapewnia przestrzegania wszystkich wymagań.
- Naiwny test słowa „waluta” odrzucał poprawną formę „walucie”. Ocena została
  poprawiona i przetestowana, również dla znaków Unicode zapisanych jako escape JSON.
- Reguły eksperckie, liczba pytań i fakty wymagają kontroli niezależnej od deklaracji LLM.

## Próby porównawcze

`scripts/check_model_quality.py` uruchamia wyłącznie syntetyczne pytania:
lista braków budżetu, 8 × 322 bez zgadywania podatku, nieobsługiwany CRM
z instrukcją próbującą wymusić fałszywe SUPPORTED. Bez wykonywania kodu,
danych klientów, produkcyjnej bazy, trenowania czy automatycznego odbioru.

Pierwsza seria: 3 warianty × 3 przypadki. Po poprawieniu błędu oceny:

| Wariant | Zaliczone próby |
| --- | --- |
| Dotychczasowe 0.2 + JSON bez schematu | 2/3 |
| Próbne ustawienia ogólne Qwen + JSON | 3/3 |
| Dotychczasowe 0.2 + schemat JSON | 3/3 |

Dwie kolejne powtórki wariantu schematu: 6/6, razem 9/9 na tych samych
trzech przypadkach. Raport: `ai-company-workspaces/model-quality-s7cwkpwn/report.json`.
Przeczytano odpowiedzi, nie tylko liczniki testów. Osobno rzeczywista ścieżka
API z testową bazą zaliczyła analizę CRM: `upwork-scope-pilot-ot6lzslq/report.json`,
14.104 s generowania, poprawne UNSUPPORTED, bez udawania implementacji.
Wynik pozostał awaiting_review; zadanie nie zostało odebrane.

Wariant podstawowy poprawnie odrzucił CRM, ale przekroczył limit pięciu wyłączeń.
Schemat ogranicza format już podczas generowania; walidator nadal sprawdza
spójność SUPPORTED/UNSUPPORTED, duplikaty i limity. Schemat nie dowodzi,
że np. sensowne sześć pytań zawiera wszystkie ważne kwestie.

Raport pierwszej serii: `ai-company-workspaces/model-quality-lxh14xd7/report.json`.
Zawiera pierwotną, częściowo błędną ocenę: zachowano go bez nadpisywania.
Aktualny wynik można odtworzyć bez modelu:

```bash
.venv/bin/python scripts/check_model_quality.py --recheck /home/marcin/ai-company-workspaces/model-quality-lxh14xd7/report.json
```

To małe testy diagnostyczne na jawnych przykładach, nie niezależny benchmark
zdolności modelu, wszystkich 12 działów ani kompletnej realizacji aplikacji.
Nie należy na ich podstawie obiecywać bezbłędnego wykonania płatnych zleceń.
Lista pytań ma schemat w próbie porównawczej; ogólny tekst agentów nie został
automatycznie zamieniony w ten format. W produkcji schemat wdrożono dla analizy Upwork.

## Ustawienia i rozwój

Adapter obsługuje nazwane ustawienia serwerowe oraz ograniczony schemat JSON;
nie przyjmuje narzędzi, hostów ani ustawień z poleceń w treści zlecenia.
Profil `qwen-general-trial.v1` testuje 0.7/top_p 0.8/top_k 20/min_p 0,
presence_penalty 1.5/repeat_penalty 1.0. Pozostaje eksperymentalny:
**nie przełączono globalnie aplikacji**, zwłaszcza generowania kodu.
Domyślnie nadal 0.2, think=false, jeden model, timeout, limit kontekstu i odpowiedzi.

Przed zmianą modelu: próbka zadań programistycznych z testami w runnerze,
analiza zakresu SUPPORTED/CLARIFY/UNSUPPORTED, brak danych, odporność na instrukcje
z zewnątrz, czas i VRAM. Dopiero potem kontrolowane przypisanie modelu do roli,
z digestem i możliwością powrotu. Sam ranking lub większy rozmiar nie wystarczy.

Przed ewentualnym LoRA/fine-tuningiem: zatwierdzone przykłady, prawa do danych,
usunięcie danych klientów/sekretów, oddzielny zestaw kontrolny niewykorzystany
do strojenia, pomiar przed/po i test regresji. Nie uczymy automatycznie modelu
na jego własnych niezweryfikowanych odpowiedziach. Trening nie zastępuje
walidacji, dokumentacji projektu i narzędzi testowych.

## Źródła sprawdzone podczas pracy

- [Qwen3.8-27B — instrukcje i parametry producenta](https://huggingface.co/Qwen/Qwen3.8-27B).
  Ustawienia zależą od trybu; dokumentacja nie jest dowodem jakości naszej kwantyzacji.
- [Ollama — schematy danych przy generowaniu](https://docs.ollama.com/capabilities/structured-outputs).
  Schemat z Pydantic i walidacja wyniku są odrębnymi etapami.
- [Qwen3-Coder 30B w Ollama](https://ollama.com/library/qwen3-coder:30b):
  sprawdzony jako potencjalny kandydat do testów kodowania, nie jako potwierdzony
  lepszy zamiennik. Nie pobrano go ani nie przełączono aplikacji.
