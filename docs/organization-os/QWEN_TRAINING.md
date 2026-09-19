# Dostrojenie Qwena dla AI Company

## Aktualizacja 19.09.2026

Właściciel ponownie polecił trening i usprawnianie modeli po domknięciu
odbioru/wydawania aplikacji. Ten etap aplikacji wielomodułowych jest już
wdrożony i sprawdzony. Rozpoczęto przygotowanie kolejnego eksperymentu,
**nie uruchomiono jeszcze treningu specjalizacji ani nie wdrożono adaptera**.

- Punkt odniesienia Qwen odtworzony: 4/4 napraw na zamrożonym, publicznym
  zestawie; 8 kontenerów przed/po, 19.677 s łącznie. Raport lokalny:
  `/home/marcin/ai-company-workspaces/qwen-training/repair-evaluation-u2pio8kc/report.json`.
  Nie zmieniono suite ani bazowego raportu. Wszystkie kontenery posprzątane.
  Ten mały zestaw jest regresją, nie prywatnym holdoutem pełnej realizacji.
- Przegląd źródeł: brak narzędzi, sieci, odczytu testów i stałych odpowiedzi
  podszywających się pod wykonanie. Dodatkowe przypadki, np. puste segmenty
  query string, nie są objęte bieżącą suite; wynik 4/4 nie dowodzi ich obsługi.
- Wcześniejszy przegląd bezpieczeństwa UI przez ten sam model miał cztery
  nietrafione zarzuty. Udane naprawy nie upoważniają modelu do samodzielnego
  zatwierdzania bezpieczeństwa, publikacji lub własnych danych treningowych.
- Wspólna kontrola dwóch odebranych partii: 12 train, 0 validation, 0 test.
  Wszystkie zatwierdzone; plan pilota wymaga nadal 200/25/50. To decyzja o
  reprezentatywności eksperymentu, nie techniczne minimum QLoRA.
  Nowa obsługa wielu partii sprawdza wyciek rodzin między plikami i zapisuje
  hashe wejścia. Nie obniżono bramki ani nie wyeksportowano niegotowego zbioru.

Najbliższe prace: rozdzielić nowe rodziny realizacji na train/validation/test,
przygotować i sprawdzić kompletne wielomodułowe realizacje oraz poprawki,
wykonać krótki trening **osobnego adaptera**, następnie porównać bazę i adapter
na nieużywanych do strojenia przypadkach. Model trafia do danej roli tylko
na podstawie wyników. Łączenie agentów nie jest automatycznie scalaniem wag
i nie gwarantuje poziomu asystenta prowadzącego. Oryginalne wagi pozostają.

## Stan wcześniejszych prac

Dobór wariantu do funkcji firmy: [protokół base / adapter / role](MODEL_ROLE_EVALUATION.md).
QLoRA nie zastępuje Qwena jako osobny model; porównujemy bazę z jej dostrojoną wersją.

Stan: 2026-09-13. Po zgodzie właściciela zainstalowano osobne biblioteki
treningowe oraz pomyślnie wykonano trzy kroki QLoRA z zapisem osobnego adaptera
testowego. Nie jest to model firmowy ani potwierdzenie poprawy jakości.
Działający model pozostaje bez zmian. [Instalacja i kontrola](QWEN_TRAINING_SETUP.md).

Przygotowano pierwszy moduł danych: [format, walidator i eksport](../../datasets/qwen/README.md).
Sześć syntetycznych przykładów jest nieodebranych; ich eksport do treningu
pozostaje zablokowany. Nie jest to jeszcze zbiór do wykonania eksperymentu.
Dodatkowo powstała osobna pierwsza partia specjalizacji: dziewięć przykładów
train po przeglądzie, pięć bez korekty treści Qwena i cztery poprawione przez
asystenta. Nie wykorzystano ich do treningu ani jako holdoutu. Zbiory
walidacyjne i testowe oraz większa reprezentatywna partia pozostają do przygotowania.
Dodano też trzy przykłady napraw kodu: Qwen → niezależne testy przed/po
w kontenerze → przegląd źródeł i dowodów. Łącznie 12 odebranych przykładów train.
Jedną lukę testów odkryto w przeglądzie i usunięto przed odbiorem partii.
[Szczegóły eksperymentu](../../datasets/qwen/reviews/repair-batch-001.md).
To nadal przygotowanie danych, nie kolejny trening ani wdrożenie adaptera.
Zapisano także [oddzielny punkt odniesienia napraw](../../datasets/qwen/evaluation/README.md):
obecny Qwen zaliczył4/4 nowych przypadków,24 metody testowe. Rodziny zastrzeżono
przed użyciem w train/validation. Potrzebne są trudniejsze próby realizacji;
ten wynik nie potwierdza jeszcze korzyści z planowanego dostrojenia.
Następnie wykonano trudniejszy [pilot aplikacji wieloplikowej](APPLICATION_FACTORY.md#syntetyczny-pilot-wieloplikowy-i-przeglądarka).
Ujawnił ucięcie odpowiedzi, luki niewykrywane przez testy autora i zmianę
testów podczas naprawy. Dodano schemat plików, blokadę testów w dekoderze,
niezależne próby HTTP/HTML oraz audyt kliknięć w izolowanej przeglądarce.
To rozwój procesu i diagnoza słabości, nie dowód poprawy wag modelu.
Prób nie dodano automatycznie do treningu ani do odłożonego zbioru oceny.

## Cel pierwszej wersji

Wytrenować osobny adapter do powtarzalnej realizacji ograniczonych zleceń:
rozpoznanie zakresu, pytania o braki, plan pracy, kompletne pliki zgodne
z profilem aplikacji oraz naprawa na podstawie prawdziwego raportu testów.
Nie próbujemy jednym treningiem nauczyć modelu wszystkich 12 działów,
budowy dowolnego produktu, aktualnych trendów i całej wiedzy programistycznej.
Aktualna dokumentacja i stan projektu nadal pochodzą z narzędzi i kontekstu.

Preferowana próba: SFT z QLoRA — uczenie dodatkowych parametrów przy
kwantyzowanej bazie, zamiast treningu od zera lub aktualizacji wszystkich wag.
Mechanizm opisuje [dokumentacja PEFT](https://huggingface.co/docs/peft/developer_guides/quantization).
Potrzeba treningu i jego skuteczność są hipotezą do sprawdzenia, nie gwarancją.

## Wykonalność i izolacja

Dotychczasowy odczyt sprzętu: RTX 5090, 32607 MiB VRAM, około 30 GiB RAM.
[Przepis Unsloth dla Qwen3.8](https://unsloth.ai/docs/models/qwen3.8/train)
deklaruje QLoRA od 24 GB VRAM. To uzasadnia próbę na naszym sprzęcie,
ale nie zastępuje lokalnego pomiaru pamięci i zgodności kerneli.
Instrukcja wskazuje Transformers v5 i zachowanie szablonu rozmowy przy eksporcie.

Obecna `.venv` aplikacji nie zawiera bibliotek treningowych.
Trening ma odrębne środowisko i katalog na dysku Linuksa:
`/home/marcin/ai-company-workspaces/qwen-training/`.
Nie instalujemy bibliotek treningowych do środowiska backendu.
Obecny model Ollamy Q4_K_M zachowujemy. Potrzebny będzie zgodny checkpoint
treningowy i tokenizer; nie traktujemy pliku GGUF jako gotowego wejścia PEFT.
Przed pobraniem sprawdzamy rewizję, licencję, rozmiary i wolne miejsce,
również na cache, checkpointy i ewentualny eksport scalonych wag.

## Kolejność prac i kryteria przejścia

1. **Zamrozić punkt odniesienia.** Zapisać digest modelu, prompty, schematy,
   parametry i testy. Obecne 9/9 dotyczy trzech powtarzanych przypadków;
   to zbyt mało do oceny fine-tuningu. Dodać niezależne zadania kodowania,
   granice danych wejściowych, brak informacji, odmowę pracy poza profilem
   i naprawy błędów, których rozwiązania nie będą w zbiorze treningowym.
2. **Zbudować sprawdzony zbiór.** Początkowy cel roboczy: 200–500 przykładów
   treningowych, osobna walidacja i co najmniej 50 odłożonych przypadków
   testowych. Liczby są planem pilota, nie progiem gwarantującym jakość.
   Podział po projekcie/rodzinie problemu przed tworzeniem wariantów;
   parafrazy tego samego zadania nie mogą trafić do różnych podzbiorów.
3. **Odbierać dane.** Qwen może proponować przykłady, ale nie zatwierdza sam
   swojej poprawności. Kod sprawdzamy niezależnymi testami w izolowanym
   runnerze. Pozostałe odpowiedzi wymagają przeglądu merytorycznego.
   Każdy rekord: ID, źródło/prawa, rodzina, wiadomości, oczekiwany wynik,
   dowody, osoba lub procedura weryfikacji i wersja. Nie eksportujemy
   automatycznie rozmów klientów, sekretów, produkcyjnej bazy ani wszystkich
   odpowiedzi z logów. Sam status COMPLETED nie jest dowodem jakości.
4. **Próba techniczna.** Najpierw załadowanie bazy i kilka kroków treningu,
   pomiar szczytowego VRAM/RAM, temperatury, czasu i zapisu adaptera.
   Ostrożny punkt startowy: tekst, kontekst 2048, batch 1, adapter rank 16;
   hiperparametry dobieramy na walidacji. Brak równoległej inferencji GPU
   podczas próby. Bez restartów hosta, zmian sterowników czy cudzych usług.
   OOM/niestabilność oznacza przerwanie własnej próby i analizę zasobów.
5. **Krótki trening porównawczy.** Zapis konfiguracji, seed, rewizji bazy,
   skrótu danych i adaptera. Obserwacja walidacji i wczesne zatrzymanie;
   spadek training loss sam w sobie nie dowodzi lepszego wykonywania zleceń.
6. **Odbiór kandydata.** Bazowy model i adapter wykonują te same odłożone
   zadania przy porównywalnych ustawieniach. Mierzymy poprawność funkcjonalną,
   przestrzeganie zakresu, nieuzasadnione twierdzenia o wykonaniu, skuteczność
   naprawy, czas, pamięć oraz regresję ogólnego rozumowania i polskiego języka.
   Wyniki szczegółowe i nieudane przypadki zachowujemy. Zbiór testowy nie służy
   do kolejnego strojenia; po ujawnieniu przykładów potrzebny nowy holdout.
7. **Wdrożenie dopiero po poprawie.** Osobna nazwa/digest kandydata, test
   zgodności eksportu, tokenizer/EOS i istniejących kontraktów API. Próbne
   użycie dla jednej roli; prosty powrót do zachowanej bazy. Brak poprawy
   lub regresja bezpieczeństwa: adapter pozostaje eksperymentem.

Niezależnie od wyniku treningu pozostają limity, testy izolacji, weryfikacja
plików, maksymalna liczba automatycznych napraw i oddzielna zgoda na wydanie.
Nie uczymy modelu fałszywych deklaracji „testy przeszły” bez raportu wykonania.
Nie wyłączamy kontroli tylko dlatego, że odpowiedź brzmi pewniej.

## Najbliższy rezultat

Wersjonowany format zbioru, walidator danych, sprawdzone przykłady i niezależny
zestaw oceny — następnie trening specjalizacji QLoRA. Przygotowano plan
i narzędzie osobnej próby technicznej, nie wytrenowany model firmowy. Czas pełnej próby
oszacujemy dopiero z pomiaru kroków i rzeczywistej liczby tokenów.
