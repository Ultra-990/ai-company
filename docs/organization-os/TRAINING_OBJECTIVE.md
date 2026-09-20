# Cel szkolenia: jakość realizacji porównywalna z asystentem prowadzącym

20.09.2026 właściciel polecił kontynuować trening z takim celem. Dotyczy on
pięciu typów usług opisanych w `config/upwork-learning-targets.json`, a nie
ogólnej deklaracji, że lokalny checkpoint dorównuje każdemu modelowi frontier.
Asystent przygotowuje infrastrukturę, wymagania i niezależne sprawdziany;
modele tworzą realizacje i poprawki. Nie zastępujemy brakującego wyniku
ręcznie napisanym produktem asystenta.

## Co uznamy za postęp

Rozdzielamy: lepszą instrukcję/pamięć, poprawkę jednego zadania, aktualizację
wag i poprawę na nowych zadaniach. Każdy raport podaje, co rzeczywiście
wykonano. Spadek loss, zmiana parametrów, zielony JSON lub liczba tokenów
nie oznaczają poprawy usługi. Samoocena modelu nie zatwierdza danych/wydania.

Dla każdego kierunku potrzebne są:

1. Rodziny ćwiczeń train oraz inne rodziny validation/test, przypisane przed
   tworzeniem wariantów. Parafrazy, poprawki i kadry jednego projektu pozostają
   w tym samym podzbiorze. Test ujawniony w nauce przestaje być holdoutem.
2. Zapis modelu, promptów, narzędzi, parametrów, materiałów i dokładnych wyników.
   Tylko sprawdzone przykłady mogą zasilać trening. Dane klientów nie trafiają
   tam automatycznie; syntetyczny materiał ma jawne pochodzenie.
3. Porównanie bazy i adaptera w tym samym runtime, kwantyzacji, kontekście
   i budżecie. Różnicy Ollama GGUF/HF bnb4 nie przypisujemy samemu adapterowi.
4. Ocena merytoryczna, funkcjonalna i wizualna stosowna do usługi, z pełną
   listą błędów. Oceny wersji anonimowe, gdzie jest to wykonalne. Własne
   rubryki asystenta są kryterium odbioru, nie dowodem statystycznej równości
   z asystentem ani niezależną opinią rynku.
5. Powtarzalne kompletne realizacje nowych briefów i brak krytycznej regresji.
   Końcowy odbiór właściciela dotyczy jakości realnego wyniku, nie etykiety modelu.

## Kierunki

| Usługa | Podstawowe sprawdziany | Czego obecne próby nie dowodzą |
| --- | --- | --- |
| Recenzja LLM | Trafne komentarze do linii, poprawne źródła, praktyczne poprawki, brak fałszywych alarmów | Research aktualnych platform, rozmowa techniczna, pełny artykuł klienta |
| Wnętrza i biblioteka | Spójność estetyki, geometria/materiały, selekcja, warianty, opisy i kompletny tracker | Obsługa konta Midjourney, dopasowanie do nieudostępnionej marki |
| Ulotka | Wierność oryginałowi, poprawne teksty, edytowalny wektor, PDF zgodny z drukarnią | Odtworzenie brakującego pliku, jakość druku bez specyfikacji |
| Infografiki produktu | Wierność produktowi i faktom, hierarchia, czytelność, komplet czterech grafik | Portfolio Amazon, wzrost konwersji, zgodność bez weryfikacji aktualnych reguł |
| Restauracja | Spójna identyfikacja, znak mały/mono, edytowalne pliki, wizytówka i księga stylu | Oryginalność/odbiór bez oceny konkretnej marki i projektu |

Trening tekstowego Qwena nie stroi automatycznie generatora obrazów.
Próby i ewentualne adaptery graficzne będą miały osobne dane, warunki i odbiór.
Menu i układ panelu pozostają poza bieżącym zakresem na życzenie właściciela.

20–21.09 wykonano [pierwszą szkołę wnętrz](INTERIOR_SCHOOL.md): modelowy plan,
trzy lokalne obrazy, sześć obserwacji wizualnych oraz paczki z trackerem.
Opisy 0/3 odebranych przed i po uwagach. To rozwój procesu i rozpoznanie
błędów; bez eksportu tej partii do SFT lub aktualizacji wag.

## Pierwszy trening na odebranych danych

`config/qwen-sft-pilot-001.json` zamraża osobny eksperyment integracyjny:
14 historycznych odebranych przykładów, kontekst 2048, rank8/alpha16,
batch1/akumulacja2, 14 kroków, learning rate5e-5, seed3407. To nie nowy
zbiór pięciu usług. Część historycznych przykładów miała korekty/autorstwo
asystenta, opisane w ich dokumentach odbioru; nie przypisujemy ich Qwenowi.

Eksperyment używa zatwierdzonych danych bez zmiany istniejącej bramki
200 train / 25 validation / 50 test. Nie eksportuje produkcyjnego zbioru,
nie dobiera parametrów na teście i nie wdraża adaptera. Brak pełnej walidacji
ogranicza wniosek do wykonalności oraz opisanej regresji, niezależnie od wyniku.
Ten mały, jawnie wydzielony krok badawczy pozwala sprawdzić rzeczywisty loss
tylko odpowiedzi, zasoby, zapis adaptera i porównanie z tą samą bazą.

Runtime: przypięty lokalny snapshot, offline, oddzielny venv. Model i źródła
danych nie są wykonywane jako kod klienta. Są tylko bezpiecznie ładowane
wagi i tokenizowane treści; skrypty napraw ze zbioru nie są uruchamiane.
Osobny adapter, brak zmian oryginalnych wag i routingu Ollamy.

Weryfikacja bibliotek: [TRL 0.24 SFT](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer)
opisuje loss odpowiedzi/prompt-completion; lokalnie sprawdzamy jawne maski
także po przetworzeniu przez rzeczywisty trainer i collator.
[PEFT quantization](https://huggingface.co/docs/peft/developer_guides/quantization)
opisuje dostrajanie dodatkowych parametrów przy kwantyzowanej bazie.
Wersje lokalnego środowiska pozostają przypięte; brak automatycznego upgrade.

### Wynik pierwszego eksperymentu

`reviewed-sft-bsoy9jvr`: trening ukończony 20.09.2026, 14 kroków / 2 epoki,
39 845 888 parametrów LoRA, maski promptu/odpowiedzi sprawdzone również
w rzeczywistym trenerze. Czas uczenia 49.273 s, całego przebiegu 183.183 s,
szczyt przydzielonego VRAM 22 904 749 568 B (około 21.33 GiB). Potwierdzono
zmianę parametru adaptera, skończony loss i zapis safetensors wraz z hashami.

Porównanie decyzji: **11/12 przed i 11/12 po**, ten sam niezaliczony przypadek,
brak poprawy lub regresji tej metryki. Uśredniony train loss 0.7964 nie jest
miarą gotowości usług. To realny trening wag adaptera i poprawnie wykonana
próba infrastruktury; **nie dowód lepszego modelu ani osiągnięcia celu**.
Adapter pozostaje badawczy, domyślny model Ollamy nie został zastąpiony.

Przed sukcesem zachowano nieudane przebiegi: zależność SQLAlchemy z aplikacji
w osobnym venv, pusta metadata architectures po text_only oraz zmiana strony
paddingu przez konstruktor trenera. Wyodrębniono czysty kontrakt oceny ról,
preflight wykonuje się w venv aplikacji; metadane uzupełnia rzeczywista klasa
załadowanego dekodera, a po konstruktorze jawnie przywracany jest tryb treningu.
Kontrola masek zatrzymała próbę przed wykonaniem błędnego kroku uczenia.
Nie zmieniano zainstalowanych bibliotek ani plików bazowego checkpointu.

## Następna partia: recenzje techniczne

[Szkoła recenzenta](TECHNICAL_REVIEW_PILOT.md) przygotowała sześć rodzin train
i 17 dokładnych odpowiedzi modelu. Niezależny odbiór dopuścił trzy do nauki
(koszty, pamięć, dowody dostawców); reszta nadal wymaga poprawy. Prompt,
informacja zwrotna i autorstwo modelu zachowane. Nie trening na deklarowanej
przez model samoocenie ani ręczne zastępowanie jego tekstu.

Rekordy mają 2274–2992 tokeny i przeszły audyt completion-only. Nie mieszczą
się w historycznym kontekście 2048: przed kolejnym treningiem trzeba zamrozić
osobny protokół, połączyć wyłącznie odebrane dane i ustalić odrębne rodziny
oceny. Nie wolno uciąć odpowiedzi ani potraktować znanych poprawek jako testu.
W kolejnym opisanym poniżej eksperymencie te trzy recenzje zostały użyte
do aktualizacji wag. Brak nowej generacji obrazów, klientowskich realizacji
i deklaracji osiągnięcia celu.

## Drugi, odrębny eksperyment — specjalizacja recenzenta

`config/qwen-sft-pilot-002.json` i `scripts/train_reviewer_pilot.py` zamrażają
17 rekordów: 14 historycznych oraz trzy dokładne odebrane recenzje modelu.
Prywatne źródła/uwagi/odpowiedzi pozostają poza publicznym repo. Loader
sprawdza hashe partii, oryginalnych request/response/article/sources i osobnej
oceny, a także równość szkolonej odpowiedzi z surową odpowiedzią modelu.
Nie wystarczy przestawić metadata na approved. Historyczny protokół001
jest bez zmian i nadal ma 14 rekordów/2048 kontekstu.

Protokół002: świeży adapter z tej samej bazy, kontekst4096, r8/alpha16,
batch1/akumulacja2, 18 kroków/2epoki, lr5e-5 liniowo malejący, seed3407.
To stały eksperyment, bez przeszukiwania parametrów na egzaminie, promocji,
podmiany pierwotnego adaptera czy aktywnego modelu. Bramka200/25/50 bez zmian.

`datasets/qwen/evaluation/reviewer-suite-001.json` rezerwuje przed treningiem
trzy nowe artykuły: interpretacja latency/throughput, audyt ekstrakcji
i dowody testu konkretnego adaptera/template. Różne rodziny evaluation_only,
przypięty checksum. Katalog danych odrzuca te rodziny i dokładne briefy
w train/validation. Rubryki i poprawne kontrole nie wchodzą do promptu.
To publiczny, mały sprawdzian syntetyczny; nie reprezentatywny test usług
ani statystyczny dowód równoważności z asystentem. Rodziny pozostają
wyłączone z dalszej nauki również po obejrzeniu błędów.

Przed i po: te same prompty, tokenizer/HFbnb4, greedy, bez thinking,
do1700 nowych tokenów/150s na artykuł. Adapter wyłączony przed i włączony
po uczeniu; żadnego porównania Ollama z HF przypisywanego treningowi.
Pomiar ról12 przypadków pozostaje oddzielną regresją. Cały run ma limit1800s.

`reviewer_exam_assessment.py` tworzy losowo oznaczone odpowiedzi bez nazw
before/after. Nauczyciel punktuje przed odczytem mapowania: dwie konkretne
usterki, zachowanie poprawnych zdań, zakres dowodów/niepewność oraz komplet
praktycznych produktów recenzji — po1 punkcie. Zaliczenie wymaga5/5 oraz
pełnej generacji i dokładnych kotwic. Format nie zastępuje oceny treści.
Oceny są jawnie oceną nauczyciela, nie automatycznym certyfikatem jakości.
Skrypt wiąże oceny z hashami odpowiedzi i rzeczywistymi fazami; nie eksportuje
odpowiedzi egzaminacyjnych do treningu.

```bash
.venv/bin/python scripts/train_reviewer_pilot.py
/home/marcin/ai-company-workspaces/qwen-training/venv/bin/python \
  scripts/train_reviewer_pilot.py --run
.venv/bin/python scripts/reviewer_exam_assessment.py --prepare /path/to/completed/run
# Niezależna ocena blind-packet.json do judgments.json, przed ujawnieniem mapowania.
.venv/bin/python scripts/reviewer_exam_assessment.py --finalize /path/to/assessment
```

Audyt CPU przed GPU: 17/17 mieści się bez ucinania; maksimum2992tokeny.
Prompty egzaminu1189/1194/1151 plus1700 odpowiedzi mieszczą się w4096.
Dokładne maski odpowiedzi są ponownie sprawdzane w rzeczywistym trainerze.

### Wynik002 — adapter badawczy odrzucony do wdrożenia

`reviewer-sft-3q8l0dpn` ukończył18kroków/2epoki. Czas treningu55.7758s,
całości488.719s, loss0.695493, peak allocated23 528 112 128B. Potwierdzono
maski w trenerze, zmianę LoRA_B i zapis osobnego adaptera; hash safetensors
`38a7d1da6fe6ae365eec71a1ed3f6a5a0e2aa34d845b9d742d6694fd039505a3`.
Pierwotny adapter i model/routing Ollamy bez zmian. Po zakończeniu procesu
GPU używało769MiB; nie pozostał proces treningu ani automatyczne ponawianie.

Ocena ról **11/12 → 11/12**, ten sam niezaliczony przypadek. Ocena treści
trzech recenzji, po ukryciu etykiet faz i zapisaniu ocen przed mapowaniem:

| Nowy artykuł | Baza /5 | Adapter /5 |
| --- | ---: | ---: |
| Latency/throughput | 3 | 5 |
| Audyt ekstrakcji | 3 | 2 |
| Dowody testu adaptera | 5 | 2 |
| Łącznie | 11 | 9 |

Pięć z sześciu odpowiedzi zawierało znaczniki Markdown wokół JSON; odpowiedź
adaptera o ekstrakcji miała poprawny format. Wszystkie zakończyły generację
EOS, bez limitowego ucięcia. Zaliczenie pełnego kontraktu **0/3 → 0/3**.
Nie usuwano znaczników ani nie poprawiano kotwic po fakcie. To wynik HF
z instrukcją schematu, bez wymuszania gramatyki API; nie należy przypisywać
go automatycznie transportowi Ollama, który wymusza schemat. Ocena treści
została celowo policzona oddzielnie od formatu.

Istotne błędy: pewne przypisanie średniego throughput każdemu użytkownikowi
w bazie; po uczeniu nadinterpretacja mianownika exact-match, zbędna krytyka
poprawnych zdań i prośba o dowód obalonej tezy o nazwach plików. Odpowiedź
o wydajności po uczeniu lepiej warunkuje średnią i prosi o pomiary per-request.
Nie daje to spójnej poprawy całej małej próby, tym bardziej gotowości usługi.

Ograniczenia: tylko3 artykuły i ocena autora rubryki, bez mocy statystycznej
lub zewnętrznego porównania z asystentem. Etykiety before/after były ukryte
podczas punktowania, ale nauczyciel wcześniej widział długości odpowiedzi
w logach postępu; nie twierdzimy, że ocena była w pełni zaślepiona.
Kontrola line2 w artykule o adapterze ma niedopowiedzianą niezależność
ewaluatora w karcie źródeł; porażka kontroli tej odpowiedzi opiera się też
na niezależnym fałszywym alarmie w line3, nie wyłącznie na line2.

Pełne prywatne dowody w `exam-assessment-8n2rlwpg`: blind-packet,
judgments, mapowanie, metoda i comparison. Oryginalny raport generacji
zachowuje status pending_semantic_review; ocena jest osobnym artefaktem,
nie przepisaniem surowego raportu. Adapter pozostaje wyłącznie badawczy.
Odrzucono promocję; egzamin nie wraca do treningu ani do wyboru hiperparametrów.
Następny etap wymaga bogatszych niezależnych rodzin train i validation oraz
osobnych prób pozostałych czterech usług, nie kolejnych epok na tym egzaminie.

Regresja infrastruktury:107testów passed/2.27s. Po dodatkowym sprawdzeniu
niezmienności mapowania faz test oceny passed/0.04s. Brak nowych zależności,
ingerencji w cudze procesy, pulpit, Windows czy produkcyjne zlecenia.
