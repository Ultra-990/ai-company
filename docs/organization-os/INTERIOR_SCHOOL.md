# Szkoła obrazów wnętrz i koordynacji redakcyjnej

Próba drugiego typu usług z `config/upwork-learning-targets.json`. Fikcyjne
Hearth & Linen, trzy różne kadry kuchni w ciepłej stylistyce klasycznej.
Lokalny Qwen pisze koncepcje, prompty, brief i metadane; lokalny Z-Image Turbo
generuje obrazy. Asystent przygotowuje kontrakt, infrastrukturę i ocenę.
Żaden opis, prompt ani obraz realizacji nie jest ręcznie poprawiany przez asystenta.

## Przebieg

`scripts/interior_school.py` ma osobne, jawne etapy:

1. `--plan --run`: trzy koncepcje i prompty 80–130 słów, tytuł, slug,
   meta description, brief autora, outline i lista kontroli publikacji.
2. `--render /prywatny/plan/report.json --run`: trzy natywne grafy ComfyUI,
   hero/detail 768×512, pin 512×768. Bez kodu lub węzłów od modelu.
3. `--inspect /prywatny/render/report.json --run`: Qwen otrzymuje rzeczywiste
   piksele PNG, bez promptu generowania, tytułu lub nazwy pliku. Pisze opisy,
   alt text, obserwacje, możliwe wady, uzasadnienie stylu i niepewność.
4. Opcjonalne `--feedback /prywatny/feedback.json` przy `--inspect`: nowa
   obserwacja tych samych obrazów z uwagami nauczyciela. Wcześniejsza odpowiedź,
   raport i powiązanie z renderem są sprawdzane hashami. Poprzednia paczka
   pozostaje bez zmian. Nie jest to egzamin ani aktualizacja wag.

Bez `--run` nie ma inferencji. Wyniki tylko w prywatnym
`/home/marcin/ai-company-workspaces/interior-school`; bez bazy zleceń i publikacji.
Paczkowanie mechanicznie przenosi dokładne teksty modelu do `image-tracker.csv`,
`writer-package.md`, `new-url-package.json` i kopiuje PNG bez zmiany bajtów.
CSV chroni początek komórki przed formułą; nazwy plików są ograniczone kontraktem.
Modelowa rekomendacja `candidate` nie jest odbiorem: paczka pozostaje
`packaged_pending_independent_review`, URL jest null, publikacja wyłączona.

`app/services/local_vision.py` obsługuje jeden lokalny PNG ≤4 MiB, ≤1 Mpix,
przez stały adres loopback. Sprawdza model/digest i limity, uruchamia własny
ograniczony czasowo proces transportu; nie wysyła URL ani ścieżek do API.
Korzysta z udokumentowanego pola `messages[].images` z danymi base64:
[Ollama vision](https://docs.ollama.com/capabilities/vision).
Tekstowy adapter i routing produkcyjny pozostają bez zmian.

Każdy etap zaczyna się kontrolą zasobów. ComfyUI jest własnym procesem na
8189, bez połączenia z pulpitem, custom nodes, cloud nodes i pobierania modeli.
Przypięty commit `19e1058f4c445ef74047e77a23f9ca7684c1e4b6`.
Po renderze proces jest kończony przed inferencją Qwena; obce usługi nietknięte.
Użyto istniejących autoryzowanych wag na Windows podłączonym tylko do odczytu;
pełnej autentyczności plików wag nie zweryfikowano, co zaznacza raport.

## Rzeczywista próba 20–21.09.2026

- Qwen `qwen3.8:27b`, digest
  `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`.
  Baza Ollama, bez eksperymentalnych adapterów QLoRA.
- `plan-kzsdwkxm`: plan poprawny strukturalnie, 33.758 s.
- `render-s51xuqeg`: 3/3 PNG, 159.692 s, własny Comfy zakończony.
  Z-Image Turbo, 8 kroków, CFG 1, stałe seedy 20260920–20260922.
- `inspect-179k_n_w`: trzy rzeczywiste obserwacje, 30.212 s, paczka zapisana.
- `inspect-kmgzp4m3`: trzy ponowne obserwacje po uwagach, 20.173 s.
  Zachowano wszystkie sześć odpowiedzi i obie wersje paczki.

Asystent obejrzał trzy PNG. Nadają się jako kandydaty do syntetycznego ćwiczenia:
ciepła paleta, czytelne obiekty, pasująca kompozycja. To nie jest odbiór klienta,
pełnej rozdzielczości ani zgodności z jego materiałami marki.

**Opisy niezaliczone: 0/3 przed i 0/3 po uwagach.** Pierwsza wersja między
innymi podawała gatunek drewna bez podstaw, źle lokalizowała ręcznik i urywała
alt text. Poprawka usunęła gatunek i poprawiła ręcznik, ale dodała niewidoczne
kosze na podłodze. Nadal diagnozowała wady na podstawie zwykłego rozmycia,
światła lub faktury; jeden alt text ponownie urwany, jedno uzasadnienie również.
Poprawny JSON i `done_reason=stop` nie wykrywają niekompletnych zdań wewnątrz
pól ograniczonych długością. Nie przycięto ani nie dopisano tekstu ręcznie.

Osobna prywatna `assessment-001.json` wiąże obrazy, odpowiedzi, raporty oraz
pliki paczek hashami. SHA256 oceny:
`d7c8780cb02c15fd3c24e9281254b4f577f7d76d7da1a41eddcfb2f54a2520ff`.
Ocena nauczycielska, jawne fazy, bez zaślepienia; żadna próba nie jest holdoutem.
Nie eksportowano tych opisów do SFT i nie trenowano na nich wag.

Następne lekcje: opisywanie wyłącznie widocznych szczegółów, odróżnianie
preferencji estetycznej od konkretnej wady, krótkie kompletne alt texty,
uzasadniona niepewność i dopasowanie do marki. Tytuł planowanej koncepcji
zawierający „oak” nie może być użyty jako potwierdzona obserwacja gatunku drewna.

Nadal nie przetestowano konta Midjourney klienta, jego materiałów marki,
produkcji w docelowej rozdzielczości, cotygodniowej koordynacji ani publikacji.
Szkoła działa przez CLI; nie jest jeszcze podłączona do panelu/kolejki.
Nie oznacza gotowości tej usługi ani jakości porównywalnej z asystentem.

## Weryfikacja infrastruktury

34 testy `test_interior_school.py`, `test_local_ollama.py`,
`test_studio_media.py` zaliczone. Sprawdzają m.in. granice PNG, ścieżki,
podmianę źródła/odpowiedzi, brak inferencji bez `--run`, wysyłanie pikseli bez
promptu generowania, dokładne kopiowanie tekstów i obrazów oraz pozostawienie
paczki bez odbioru i publikacji. Testy jednostkowe nie mierzą smaku ani trafności
opisu; te ograniczenia wykazała rzeczywista próba powyżej.

## 21.09 — jawny schemat, lekcja i pierwszy odebrany zapis obraz–tekst

Dodano jawne profile `--vision-profile schema-visible-v1` oraz
`grounded-concise-v1`; domyślny `legacy` zachowuje starą instrukcję.
Pierwszy pokazuje modelowi ten sam schemat, który API wymusza przy generacji.
[Dokumentacja Ollamy](https://docs.ollama.com/capabilities/structured-outputs)
zaleca również podawanie schematu w treści instrukcji. Drugi dodaje lekcję
krótkich kompletnych zdań, widocznych szczegółów i uzasadnionej krytyki obrazu.
Sam schemat walidacji, obrazy, model i budżet generacji pozostały takie same.

Próby na tych samych trzech obrazach, bez aktualizacji wag:

| Próba prywatna | Instrukcja | Czas | Pełne obserwacje odebrane |
| --- | --- | --- | --- |
| inspect-dm1mo8dj | Jawny schemat | 20.122 s | 0/3 |
| inspect-8orm_8o6 | Schemat i lekcja | 18.709 s | 0/3 |
| inspect-izdxjllv | Schemat, lekcja i uwagi do obrazów | 17.792 s | 1/3 |

Jawny schemat współwystąpił z kompletnymi zdaniami we wszystkich trzech
odpowiedziach tej próby. To pojedyncze próbki sekwencyjne, bez zaślepienia,
nie dowód przyczynowy ani przeniesienia umiejętności na inne zadania.
Ocena i źródła są powiązane w prywatnej `assessment-002.json`.

Odebrano dokładny wynik modelu dla hero: poprawione położenie ręcznika
i baterii, zwięzły alt text, brak wymyślonych wad, uzasadnienie stylu
i niepewność materiałowa. Pin nadal zbyt pewnie identyfikuje materiał
częściowo uciętego uchwytu naczynia. Detail ma kompletny alt text, ale
17 słów przy jawnym limicie 16 w uwagach. Nie zmieniano odpowiedzi ręcznie.
Tytuły koncepcji w nowych paczkach są oznaczone `planned_concept_title`
i `Planned concept`, aby nie mylić intencji generowania z obserwacją.

`scripts/interior_learning_records.py REPORT JUDGMENTS --export` odkłada
wyłącznie obserwacje zatwierdzone przez osobną ocenę nauczycielską. Sprawdza
raport, wejście, dokładną odpowiedź i obraz po hashach; nie ufa rekomendacji
`candidate` modelu. Zapisuje rzeczywisty PNG, dokładny tekst system/user/assistant
(łącznie z uwagami), konfigurację i pochodzenie. Wszystkie warianty tego renderu
mają tę samą rodzinę i pozostają w `train`; nie można eksportować ich jako test.

Rzeczywisty zapis `vision-candidates-fyodznnk` zawiera jeden zatwierdzony
syntetyczny rekord `company-vision-candidate.v1`. SHA `records.jsonl`:
`5533273410e47ca63d78dcef8375d59536ca8f4f13cbdc2f2f82407325176be3`.
Format jest celowo odrębny od tekstowego SFT — nie wolno zgubić obrazu,
zostawiając sam opis. Wagi nadal nie zostały na nim wytrenowane. Manifest
ma `ready_for_trainer=false`: potrzebny audyt procesora i masek multimodalnych,
szersze dane oraz odrębne rodziny walidacji/testu. Przykładowy mechanizm
przetwarzania opisuje [Unsloth vision fine-tuning](https://unsloth.ai/docs/basics/vision-fine-tuning).
Nie potwierdzono gotowości całej paczki, komercyjnych praw ani usługi klienta.

Końcowo 41 testów infrastruktury: dodatkowo odtworzenie dokładnego wejścia
obraz–tekst, wykrywanie podmiany obrazu/promptu/odpowiedzi/renderu, brak eksportu
po samej samoocenie modelu i odrzucenie rekordu przez tekstowy loader SFT.

Kolejny etap 21.09: [audyt wejścia i trzy rzeczywiste aktualizacje adaptera
obraz–tekst](VISION_TRAINING_INPUTS.md). Wcześniejszy manifest paczki zachowuje
stan z chwili eksportu; osobny raport dokumentuje wykonany później trening
integracyjny. Nie oznacza to spełnienia warunków treningu produkcyjnego.
