# Niezależne ćwiczenia walidacyjne SVG

## Wynik pierwszej rzeczywistej próby — 21.09.2026

Przypięty lokalny Qwen zaliczył **23/24 dokładnych napraw** i **0/1 pełnego
odtworzenia** na rodzinie science-evening-validation-v1. Wszystkie 25
odpowiedzi zapisano, a wyniki niezależnie przeliczono z oryginalnych operacji,
SVG, PNG i PDF. To wynik obecnej bazy Ollama, bez nowego treningu i bez
porównania z adapterem. Zestaw treningowy pozostał oddzielony od egzaminu.

Niezaliczona naprawa przywróciła font-size 45 zamiast 46; obraz był bliski,
ale nie spełnił wymogu identycznego źródła. W pełnym odtworzeniu 8/8 tekstów
było poprawnych, geometria mieściła się w tolerancji, lecz średni błąd RGB
0,0468693 przekroczył zamrożony próg 0,045. Nie obniżono progów i nie poprawiano
grafiki za model. Niezależnie obejrzany wynik zachowuje kompozycję, ale różni
się paletą, krawędziami panelu, położeniem tekstu i geometrią dekoracji.

Przygotowanie: 24 wywołania modelu usterek; egzamin: 25 odpowiedzi ucznia.
Łączny zapisany czas tych inferencji: 210,065 s. Jeden błąd sprzątania profilu
Chrome przerwał pierwszą próbę po zapisaniu piątej odpowiedzi. Po naprawie
obsługi własnych procesów wznowiono ocenianie tej samej odpowiedzi, bez nowej
inferencji. Kopię przerwanego raportu i plików oraz identyczność odpowiedzi
ponownie sprawdzono. Żadne wejście tej partii nie wymagało wyjątku PDF.

Prywatne artefakty: `exam-arn1vaw6`, `exam-answer-nncqflxg` oraz
`reserved-exam-001-assessment.json` w vector-school. Ostatnia dozwolona
poprawka wzorca travel-club nadal nie spełniła briefu; pozostaje odrzucona.
Nie ma jeszcze gotowego pełnego egzaminu testowego ani dowodu poprawy wag.
Testy kierunkowe: 121 passed. Pełne `.venv/bin/pytest -q`:
1635 passed,21 skipped w84,13s.

## Mechanizm

`scripts/vector_exam.py` oddziela przygotowanie wejść od odpowiedzi ocenianego
modelu. Wymaga wzorca ze z góry ustalonej rodziny validation/test, jego
autentykacji oraz niezależnego, związanego hashem odbioru obrazu. Rodziny
train/development, samoocena modelu i nieodebrane źródła są odrzucane.

Egzamin ma stałe 25 zadań: po jednej zmianie font-size, x i y dla każdej
z ośmiu linii oraz pełne odtworzenie źródła z samego obrazu. Usterki wybiera
lokalny model w osobnych wywołaniach. Narzędzie stosuje wyłącznie jego
dosłowne operacje i sprawdza ich zgodność z planem. Nieudane przygotowanie
przerywa zamrażanie egzaminu; wadliwy przypadek nie znika z zestawu.

Uczeń dostaje obraz źródła, katalog uszkodzonych elementów i pomiary błędu.
Nie dostaje oryginalnego SVG ani odpowiedzi twórcy usterki. Przy odtwarzaniu
całej ulotki widzi wyłącznie obraz i wymagania. Wszystkie zadania są zapisane
przed pierwszą odpowiedzią ucznia. Odpowiedzi nie mają trybu poprawiania
na podstawie wyniku, doświadczeń SFT ani eksportu do zbioru treningowego.

```bash
.venv/bin/python scripts/vector_exam.py --prepare /prywatny/wzorzec/report.json --run
.venv/bin/python scripts/vector_exam.py --evaluate /prywatny/egzamin/report.json --run
.venv/bin/python scripts/vector_exam.py --verify /prywatne/odpowiedzi/report.json
.venv/bin/python scripts/vector_exam.py --resume /prywatne/odpowiedzi/report.json --run
```

Ścieżki muszą należeć do prywatnego katalogu vector-school. Bez `--run`
polecenia przygotowania i oceniania nie uruchamiają modelu. Weryfikacja
jest odczytem: ponawia odtworzenie operacji, porównanie obrazów i kontrolę
rzeczywistego PDF, bez inferencji lub treningu.

Wznowienie dotyczy wyłącznie zakończonego przerwania infrastrukturalnego,
przy niezmienionym egzaminie i konfiguracji modelu. Przed kontynuacją
ponownie sprawdza wcześniejsze wyniki, zapisuje kopię przerwanego raportu
i artefaktów ostatniego przypadku. Jeśli odpowiedź została już zapisana,
wykorzystuje te same bajty zamiast prosić model o nową. Nie służy ponawianiu
błędnych rozwiązań. Chrome działa w osobnej grupie procesów; sprzątanie
zamyka wyłącznie tę grupę i ponawia usuwanie własnego tymczasowego profilu
w razie krótkiego wyścigu zapisu plików.

## Ocena i ograniczenia

Naprawa wymaga odtworzenia każdego bajtu zaakceptowanego źródła, zaliczenia
porównania PNG i geometrii tekstu oraz eksportu PDF. Odtworzenie całej
ulotki ma osobny wynik według dotychczasowych progów obrazu i tekstu.
Wyniki obu umiejętności nie są sumowane w jedną ocenę gotowości usługi.
Metryki, hashe żądań, odpowiedzi, scen, obrazów, PDF i tożsamość modelu są
ponownie sprawdzane; zmiana sum punktów lub ręczna poprawka SVG nie przechodzi.

Renderer zachowuje ścisłą kontrolę wyników domyślnie. Jedyny dodatkowy cel
`controlled_fault_input` zapisuje błąd sprawdzenia PDF jako informację
o wadliwym wejściu. Nie zmienia wymagań wobec odpowiedzi ucznia ani wzorca.
Kontrola zasobów poprzedza każde wywołanie modelu i renderowanie; obce
procesy nie są zatrzymywane. Procesy Chrome używają własnych profili headless.

To egzamin jednej ograniczonej umiejętności na jednej rodzinie, nie pełna
kwalifikacja usługi drukarskiej, porównanie wszystkich pięciu usług ani
dowód ogólnej autonomii. Wersja wykonawcza korzysta obecnie z przypiętego
modelu Ollama. Porównanie bazy i nowego adaptera w identycznym środowisku
treningowym pozostaje następnym etapem. Osobne, nieużywane do doboru wersji
zadania testowe nadal są wymagane przed dopuszczeniem nowego modelu.
