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
Te trzy recenzje **nie zostały jeszcze użyte do aktualizacji wag**. Brak
nowej generacji obrazów, klientowskich realizacji i deklaracji osiągnięcia celu.
