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
