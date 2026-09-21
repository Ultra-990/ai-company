# Przygotowanie wzorców do niezależnego egzaminu

Stan 21.09.2026: **jeden odebrany wzorzec validation, zero odebranych test**.
Nie wygenerowano odpowiedzi ucznia na egzaminie, nie uruchomiono treningu
wag i nie zmieniono aktywnego modelu. To przygotowanie danych wejściowych
do późniejszego porównania bazy i adaptera, nie wynik takiego porównania.

`scripts/vector_structured_source.py` przekazuje lokalnemu modelowi zamrożony
brief oraz schemat sceny: 3–18 kształtów i dokładnie osiem tekstów. Model
wybiera wszystkie słowa, współrzędne, kształty, kolory i parametry pisma.
Kompilator `literal-scene-svg.v2` zapisuje te wartości dosłownie jako XML,
z ustalonym kontenerem SVG i kolejnością kształty–teksty. Nie poprawia treści
ani nie dobiera brakujących parametrów. To scena autorstwa modelu zapisana
przez narzędzie, a nie surowy SVG napisany przez model lub grafika asystenta.

Wymagane są pełne atrybuty geometrii. Dekoder używa ograniczeń długości
zamiast wyrażeń regularnych: pierwotny schemat powodował HTTP 400 lokalnego
serwera (`failed to parse grammar`). Po serializacji dotychczasowy niezależny
walidator nadal sprawdza dokładną składnię liczb, zakresy, kolory, fonty,
osiem różnych tekstów i bezpieczny podzbiór SVG. Następnie oddzielna
przeglądarka headless tworzy rzeczywisty PNG i PDF A5 z osadzonymi fontami.
Kontrole widoczności tekstu nie zastępują sprawdzenia zgodności z briefem.

Użycie wymaga jawnego `--run`, np.:

```bash
.venv/bin/python scripts/vector_structured_source.py \
  --curriculum science-evening-validation-v1 --run
```

`--feedback` przyjmuje prywatny plik `vector-scene-reference-feedback.v1`.
Wiąże uwagi z hashami raportu, żądania i surowej odpowiedzi poprzednika.
Do trzech poprawek źródła zachowuje rodzinę, wersję kompilatora i kompletny
łańcuch żądań. Model poprawia całą scenę; oryginalne odpowiedzi pozostają.
Role odtworzenia/ucznia nie są dopuszczone do tej ścieżki. Surowa ścieżka
SVG ma analogiczne jawne `vector-evaluation-reference-feedback.v1` tylko
dla przygotowania źródeł validation/test. Kolektory nauki nadal blokują
obie zarezerwowane rodziny; nie wolno przenosić tych odpowiedzi do SFT.

Autentykacja sprawdza sześć plików, zamrożony brief, model/digest i ponowną
kompilację oryginalnej odpowiedzi do identycznych bajtów SVG. Pozytywna
niezależna ocena wzorca pozostaje osobnym warunkiem. `reference_ready`
oznacza zaliczenie kontroli technicznych, nie odbiór całego briefu.

## Rzeczywiste próby i ograniczenia

- Sześć prób surowego SVG nie dało wzorca: nadmiarowe teksty lub ucięta
  odpowiedź. Dwie poprawki modelu powtórzyły problem z liczbą tekstów.
- Osiem prób sceny: pierwsza odrzucona przez parser schematu; kolejne
  ujawniły puste kształty, niewidoczne nagłówki i brak tekstów w bocznej
  kolumnie. Prototypy kompilatora v1 pozostają zapisane, nie są wzorcami v2.
- Model poprawił własny wzorzec astronomiczny po uwagach o tle nagłówka.
  Niezależnie obejrzany PNG ma osiem czytelnych linii, dwie kolumny i prostą
  ilustrację; odebrano go wyłącznie jako syntetyczne wejście walidacyjne.
- Wzorzec podróżniczy po dwóch poprawkach nadal nie ma dwóch wymaganych
  tekstów w sidebarze. Odrzucony mimo pozytywnych kontroli technicznych.
- Uwagi nauczyciela omyłkowo zarzuciły tytułowi `The Illustrated Line`
  przekroczenie limitu. Ma dokładnie 20 znaków; zarzut jawnie wycofano
  w ocenach. Zachowano historyczny feedback, bez eksportu do treningu.

Prywatna ocena: `vector-school/reserved-reference-preparation-001-assessment.json`.
Pełny egzamin i automatyczna pętla aktualizacji wag nadal wymagają wykonania.
Testy infrastruktury: **106 passed** kierunkowo; pełne
`.venv/bin/pytest -q`: **1620 passed, 21 skipped**, 80,01 s.
