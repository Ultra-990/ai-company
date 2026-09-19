# AI Company — architektura docelowa

Stan specyfikacji: 2026-09-12. Dokument zapisuje zakres uzgodniony z właścicielem
i proponowany sposób jego realizacji. Zdolności docelowe opisane poniżej nie
oznaczają działających integracji, uruchomionych agentów ani odebranych produktów.
Dokument nie aktywuje usług, wydatków ani działań wobec klientów.

Aktualizacja wykonania 2026-09-13: po potwierdzeniu końca wynajmu uruchomiono
[lokalnego tekstowego wykonawcę Qwen](organization-os/LOCAL_INFERENCE.md).
Generuje odpowiedź dla istniejącej delegacji; nie wykonuje kodu ani nie
akceptuje własnej pracy. To pierwszy działający odcinek, nie całość docelowa.

Kolejny odcinek 2026-09-13: [fabryka aplikacji Python](organization-os/APPLICATION_FACTORY.md)
z generowaniem źródeł, izolowanym wykonaniem i bramką wydania po odbiorze.
Nie obejmuje jeszcze dowolnych zależności, wdrożeń i wszystkich kategorii produktów.

## Cel produktu

AI Company ma być firmą technologiczną sterowaną przez właściciela, obsługiwaną
przez sieć agentów oraz zdolną do realizacji zleceń i budowy własnych produktów.
Zakres obejmuje strony premium, aplikacje, portale społecznościowe, platformy
branżowe, agentów i automatyzacje, generatory grafiki, wideo i muzyki, a także
własne modele językowe oraz systemy i środowiska Linux.

Upwork jest jednym z kanałów sprzedaży. System ma obsługiwać również klientów
bezpośrednich, abonamenty produktowe, płatne API, licencjonowanie komponentów,
utrzymanie, wdrożenia oraz partnerstwa. Rentowność i jakość podlegają pomiarowi;
nie zakłada się gwarantowanego przychodu ani automatycznej przewagi nad rynkiem.

## Fundament i sposób dostarczenia

Linux jest docelową bazą środowisk wykonawczych. Orkiestracja, reguły biznesowe,
pamięć i pulpit działają w przestrzeni użytkownika. Nie ma obecnie wymagania,
które uzasadniałoby zmianę jądra Linux.

Pulpit może działać w przeglądarce i później jako aplikacja pełnoekranowa.
Dedykowany obraz Linux uruchamiający AI Company po starcie komputera jest
osobnym produktem w gałęzi `systems-rnd`, korzystającym z tych samych usług.

Warstwy:

1. Pulpit przestrzenny: właściciel, orkiestrator, działy, projekty i wykonawcy.
2. Domena firmy: klienci, oferta, zakres, terminy, koszty, odbiory i przychody.
3. Orkiestracja: delegacje, zależności, kolejki, limity, wznowienia i eskalacje.
4. Wykonanie: repozytoria, terminal, przeglądarka, kompilacja, testy i artefakty.
5. Infrastruktura Linux: środowiska izolowane, CPU/GPU, dyski, sieć i diagnostyka.

## Jedno drzewo zdolności, wiele widoków

Trwałą strukturą pozostaje `OrganizationUnit`. Istniejące identyfikatory
z `app/organization_os/taxonomy.py` są zachowane. Poniższy katalog precyzuje,
jakie zdolności należy rozwinąć pod obecnymi gałęziami; nowe liście i zmiany wag
wymagają wersjonowanego rozszerzenia katalogu oraz migracji, a nie drugiej roadmapy.
Ta wersja dokumentu nie wstawia nowych rekordów do bazy.

| Obecna gałąź | Zakres docelowego rozwinięcia | Dowód gotowości |
| --- | --- | --- |
| `digital-experience.websites`, `digital-experience.design` | Strony premium, art direction, interakcje, 3D, motion design i indywidualna identyfikacja | Działająca realizacja, niezależny przegląd wizualny, testy użytkowe i porównanie z wybranymi wzorcami |
| `digital-experience.accessibility`, `digital-experience.performance` | Czytelność, dostępność, responsywność i wydajność efektownych stron | Wyniki testów na zadeklarowanych urządzeniach, obsługa klawiatury i ograniczonych animacji |
| `ai-automation.agents` | Orkiestrator, kierownicy, wykonawcy, kontrolerzy i automatyzacje procesów | Delegacja zakończona odebranym artefaktem oraz poprawne zatrzymanie i wznowienie wykonania |
| `web-platforms.saas`, `web-platforms.business`, `web-platforms.verticals` | Aplikacje webowe, mobilne i desktopowe, systemy biznesowe i platformy branżowe | Odbiór konkretnego scenariusza użytkownika na wspieranej platformie |
| `web-platforms.social`, `web-platforms.marketplaces` | Społeczności, komunikacja, marketplace, narzędzia twórców i subskrypcje | Zweryfikowane konta, publikowanie, moderacja, uprawnienia i rozliczenie testowej transakcji |
| `web-platforms.content` | Portale i platformy treściowe, w tym osobny profil produktów dla dorosłych | Działające mechanizmy dostępu, prywatności, zgłoszeń i moderacji; określony rynek i zasady płatności |
| `ai-automation.generators` | Oddzielne zdolności generowania grafiki, wideo oraz muzyki i audio | Odtwarzalny rezultat, pomiar jakości, czasu i kosztu oraz udokumentowane pochodzenie zasobów |
| `ai-automation.rag`, `ai-automation.evaluation` | Laboratorium modeli językowych: dane, adaptacja, trening, ewaluacja i eksperymenty | Wersja danych i modelu, odtwarzalny eksperyment, wyniki niezależnego zestawu testowego |
| `ai-automation.costs`, `operations.environments` | Serwowanie modeli, zadania GPU, pomiar kosztów i obsługa obciążenia | Pomiar kosztu użycia, opóźnienia, przepustowości i zachowania przy awarii |
| `client-services` | Zlecenia z platform i bezpośrednie: kwalifikacja, oferta, wykonanie, poprawki i przekazanie | Odebrany projekt ze spójnym zakresem, dowodami i rozliczeniem |
| `business-marketing`, `finance-legal` | Pozyskiwanie klientów, modele przychodów, pricing, licencje, retencja i rentowność | Zweryfikowany popyt, koszt pozyskania i dostarczenia, rzeczywista marża |
| `systems-rnd` | Dystrybucje i obrazy Linux, środowiska graficzne, narzędzia systemowe | Uruchamialny obraz lub pakiet, testy zgodności, aktualizacji i odtworzenia |

Produkty dla dorosłych otrzymują osobny profil wymagań dotyczący pełnoletności,
zgody osób przedstawionych w materiałach, prywatności, moderacji i zgodności
z warunkami wybranych dostawców. Zakres ten dotyczy infrastruktury produktu;
nie wymaga generowania treści seksualnych. Szczegółowe wymagania ustala się
dla konkretnego produktu i rynku.

Każdy rezultat ma jedno miejsce rozliczania postępu. Inne działy wskazują go
jako zależność lub dowód, bez ponownego naliczania tej samej pracy.
Postęp budowy zdolności, realizacja zleceń i bieżące wskaźniki biznesowe są
odrębnymi widokami: ukończenie zlecenia nie oznacza ukończenia całego działu.

## Struktura odpowiedzialności agentów

Właściciel jest człowiekiem podejmującym decyzje strategiczne. Rekord
`owner-core` reprezentuje go w interfejsie i nie oznacza autonomicznego LLM.

```text
Właściciel
└── Mózg / orkiestrator
    ├── Kierownicy 12 działów
    │   └── Kierownicy aktywnych produktów i projektów
    │       └── Wykonawcy („mrówki”) uruchamiani do konkretnych zadań
    └── Kontrolerzy jakości, bezpieczeństwa, kosztów i dowodów
        └── Niezależny odbiór rezultatów oraz raport do właściciela
```

Kierownicy odpowiadają za wynik swojego działu i dostępne kompetencje:

| Dział | Przykładowe role wykonawcze |
| --- | --- |
| Strategia | Analityk portfolio, planista, analityk ryzyka i zależności |
| Platforma | Architekt, programista backendu, frontendowiec, inżynier danych |
| AI i automatyzacja | Inżynier agentów, autor workflow, inżynier ML, badacz modeli, ewaluator |
| Aplikacje i platformy | Kierownik produktu, programista aplikacji, specjalista społeczności i integracji |
| Doświadczenie cyfrowe | Art director, projektant UX/UI, creative developer, motion designer, specjalista dostępności |
| Systemy i R&D | Inżynier Linux, programista systemowy, autor środowiska desktopowego |
| Usługi klientów | Analityk wymagań, kierownik realizacji, specjalista przekazania i wsparcia |
| Jakość i bezpieczeństwo | Tester, recenzent kodu, audytor bezpieczeństwa, kontroler dowodów |
| Operacje | Inżynier środowisk wykonawczych, DevOps, operator GPU i diagnostyki |
| Biznes i marketing | Badacz rynku, analityk ofert, autor materiałów, specjalista sprzedaży i retencji |
| Finanse i prawo | Analityk kosztów i rentowności, koordynator rozliczeń i dokumentów |
| Wiedza i społeczność | Redaktor dokumentacji, opiekun pamięci, autor szablonów i szkoleń |

Rola, tożsamość agenta i uruchomienie zadania są oddzielnymi bytami. Pełna
struktura nie wymaga utrzymywania wszystkich agentów jako stale aktywnych
procesów. Kierownik dobiera wykonawcę do kompetencji, modelu, narzędzi,
dostępności i budżetu, a orkiestrator ogranicza równoległość.

Specjalista AI wspiera decyzje finansowe lub prawne; samo przypisanie roli
nie jest potwierdzeniem kwalifikacji ani uprawnieniem do zaciągania zobowiązań.

## Kontrakt wykonania i odbioru

Każde zlecenie dla agenta zawiera cel, węzeł struktury, projekt, dane wejściowe,
zakres plików i narzędzi, limit czasu i kosztu, kryteria odbioru, odbiorcę
oraz wymagane dowody. Delegacja nie rozszerza uprawnień delegującego.

Docelowe wykonanie obsługuje trwały identyfikator próby, przejęcie zadania,
heartbeat, anulowanie, limit ponowień i odtworzenie po restarcie. Powtórzenie
żądania nie może niejawnie ponawiać płatności lub publikacji. Równoległe zmiany
kodu trafiają do odrębnych przestrzeni roboczych i podlegają integracji.

Przepływ: wymagania → plan → wykonanie → kontrola → poprawki → odbiór → przekazanie.
Niepusta odpowiedź modelu oznacza dostarczenie odpowiedzi, nie dowód ukończenia
aplikacji. Odbiorca sprawdza artefakty, wyniki testów i scenariusz użytkownika.
Autor nie jest jedynym kontrolerem własnego rezultatu.

Środowisko projektu obejmuje repozytorium, ograniczony terminal, zależności,
testy, przeglądarkę, podgląd aplikacji i magazyn wyników. Linux jest bazą;
kontenery i maszyny wirtualne dobiera się do potrzeb izolacji danego zadania.

## Laboratorium modeli i multimediów

Rozróżniamy trzy niezależnie mierzone zdolności:

1. Produkt korzystający z istniejącego modelu: aplikacja, workflow i serwowanie.
2. Adaptacja modelu: fine-tuning, wersjonowanie danych i porównanie z bazą.
3. Model trenowany od podstaw: dane, architektura, infrastruktura treningowa,
   eksperymenty, ewaluacja i utrzymanie wydania.

Każdy z tych poziomów ma osobny zakres dla grafiki, wideo, muzyki i języka.
Dodanie API generatora nie oznacza wytrenowania własnego modelu.
Fine-tuning kontynuuje trening modelu wstępnie wytrenowanego; opis procesu:
[Hugging Face](https://huggingface.co/docs/transformers/training).

Ambicja tworzenia najnowocześniejszych modeli językowych wymaga programu
badawczego z określonymi zadaniami porównawczymi, dostępem do danych i zasobów,
budżetem oraz wynikami eksperymentów. Przewaga musi wynikać z pomiarów jakości,
kosztu i szybkości na niewykorzystanych w treningu danych. Sieć agentów pomaga
w badaniach, ale sama liczba agentów nie zapewnia przewagi modelu.

## Jakość wizualna i pulpit 3D

Cel „strony lepsze niż Awwwards” przekładamy na niezależne porównanie realizacji:
oryginalność, spójność wizualna, jakość interakcji, użyteczność, treść,
dostępność i wydajność na wskazanych urządzeniach. Nagroda ani przewaga nad
wszystkimi przykładami nie jest gwarantowanym rezultatem procesu.
Punkt odniesienia: [Awwwards — evaluation](https://www.awwwards.com/about-evaluation/).

Pulpit docelowy łączy scenę 3D z czytelnymi kontrolkami aplikacji. Ma geometrię
kul, materiały, światło i kamerę. Kula właściciela otwiera centrum decyzji
i powiadomień, osobny mózg prowadzi do kierowników, wykonawców i projektów.
Połączenia rozróżniają podległość, zależność wykonawczą i przepływ informacji.
Ogólna współpraca działów nie może automatycznie blokować wszystkich ich zadań.

Okna mają kolorowe ikony i dzwonek, zmianę rozmiaru, przeciąganie, minimalizację,
maksymalizację, zamykanie i przywracanie. Aktualizacja danych zachowuje pozycję,
stan i fokus. Podgląd pracy pokazuje rzeczywiste zmiany, testy i wyniki,
a wyświetlenie agenta nie jest dowodem, że jego proces jest uruchomiony.

## Telefon właściciela i polecenia głosowe

Wymaganie właściciela: urządzeniem docelowym jest iPhone 14 Pro. System ma
umożliwiać zdalne sterowanie firmą także poza domem, swobodną rozmowę głosową
z odpowiedziami mówionymi oraz wymianę wiadomości tekstowych.
Telefon i pulpit korzystają z tego samego stanu projektów, rozmów,
zadań i decyzji. Zakres należy do `platform.frontend`,
`platform.organization-os`, `platform.data-identity` i `ai-automation.agents`.

Podstawowy przepływ: nagranie po świadomym włączeniu mikrofonu → transkrypcja
→ interpretacja celu przez orkiestrator → odpowiedź lub zadanie → postęp
i powiadomienie na telefonie. Właściciel może zobaczyć i poprawić transkrypcję.
Założeniem startowym jest język polski. Głosowe odpowiedzi są wymagane.
Docelowa rozmowa obejmuje wykrywanie końca wypowiedzi, odpowiedź strumieniową,
możliwość przerwania odpowiedzi i zachowanie kontekstu przy przełączeniu na tekst.
Dyktowanie pojedynczej wiadomości jest etapem integracji, a nie pełnym odbiorem
wymagania swobodnej rozmowy. Działanie po zablokowaniu ekranu lub przejściu
aplikacji w tło wymaga osobnej weryfikacji na docelowej wersji iOS.

Mobilny panel pokazuje polecenia, decyzje, wyniki i podgląd pracy, zachowując
tożsamość wizualną pulpitu. Połączenie z urządzeniem wymaga uwierzytelnienia
i szyfrowanego transportu. Dostęp poza domową siecią jest osobnym elementem
wdrożenia; lokalny adres `127.0.0.1` na telefonie wskazuje sam telefon.
Sposób przechowywania nagrań i przetwarzania mowy musi być jawny w ustawieniach.

Polecenie głosowe podlega tym samym uprawnieniom i limitom co tekstowe.
Niepewna interpretacja istotnego działania wymaga doprecyzowania. Ponowne
połączenie lub wysłanie nagrania nie może utworzyć podwójnego zlecenia.
Interfejs odróżnia wiadomość oczekującą na wysłanie od przyjętej przez serwer.

Odbiór: na docelowym telefonie właściciel dyktuje polecenie, widzi właściwą
transkrypcję i jedno utworzone zadanie na pulpicie, otrzymuje wynik, a utrata
i przywrócenie połączenia nie powodują duplikacji. Rozmowa głosowa musi przejść
test poza domową siecią, wraz z przerwaniem odpowiedzi i powrotem do tekstu.
Komputer domowy wykonujący pracę musi być uruchomiony, dostępny w sieci
i nieuśpiony; telefon nie przejmuje automatycznie roli serwera.

## Ustalenia lokalnego wykonania i budżetu

Właściciel wybrał na start modele uruchamiane lokalnie, bez płatnych API,
i zezwolił na instalację potrzebnych dodatkowych modeli oraz adaptację
zainstalowanego modelu. Nie jest to dyspozycja uruchomienia płatnych usług.
Koszt energii i wykorzystanie sprzętu nadal powinny być mierzone.

Odczyt lokalnego środowiska z 2026-09-12 potwierdził:

- CPU AMD Ryzen 7 9800X3D, 8 rdzeni / 16 wątków, około 30 GiB widocznego RAM.
- GPU NVIDIA GeForce RTX 5090, 32607 MiB pamięci GPU.
- Ollama z modelem o lokalnej nazwie `qwen3.8:27b`, około 17 GB na dysku.
- Metadane tego wpisu: GGUF, 27.3B parametrów, Q4_K_M, rodzina `qwen35`;
  lokalny tag nie jest niezależnym potwierdzeniem pochodzenia wag.
- Inne wpisy Ollama: `gpt-oss:20b` i `gpt-oss-20b-local:latest`.
- Konfiguracja aplikacji wskazuje lokalny Qwen; `tool_calling_enabled` jest
  wyłączone. Obsługa narzędzi deklarowana przez model nie oznacza aktywnej
  integracji narzędzi w aplikacji.
- Tailscale jest uruchomiony, a sieć zawiera urządzenie iOS. W chwili odczytu
  urządzenie iOS było offline; nie przeprowadzono testu dostępu z telefonu.

Wstępny kierunek zdalnego dostępu wykorzystuje istniejącą prywatną sieć
Tailscale oraz HTTPS i uwierzytelnienie aplikacji. Odczyt stanu nie zmienił
reguł dostępu ani nie opublikował żadnej usługi. Dokumentacja:
[Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).

Wariant lokalnej rozmowy składa się z rozpoznawania mowy, Qwen jako modelu
dialogowego i syntezy głosu. Rozpoznawanie i syntezę dobieramy po próbie polskiej
mowy oraz pomiarze łącznego zużycia zasobów i opóźnienia. Obecny klient LLM
zwraca pełną odpowiedź; wymaga rozszerzenia dla rozmowy strumieniowej.
Liczba równoległych agentów jest ograniczana zasobami. Powyższy odczyt sprzętu
nie stanowi benchmarku wydajności ani potwierdzenia płynnej rozmowy.

Aktualność wiedzy o firmie zapewnia pamięć i wyszukiwanie aktualnych źródeł.
Adaptacja modelu wymaga wskazania celu, przygotowania danych, pomiaru bazowego
i odrębnego wyniku treningu możliwego do porównania i wycofania. Zainstalowany
kwantyzowany GGUF nie jest automatycznie kompletnym środowiskiem treningowym;
odpowiedni format wag i narzędzia należy zweryfikować przed eksperymentem.

## Aktualna wiedza i analiza kierunku rozwoju

Wymaganie właściciela: system aktualizuje wiedzę o technologiach, wzornictwie,
modelach AI, konkurencji i popycie oraz wykorzystuje ją przy rekomendowaniu
dalszego rozwoju. Zakres należy do `business-marketing.market`,
`ai-automation.rag`, `ai-automation.evaluation` i `strategy.priorities`.

Należy odróżnić trzy procesy:

1. Synchronizacja stanu firmy: zadania, wyniki i zdarzenia widoczne na urządzeniach.
2. Aktualizacja wiedzy zewnętrznej: pobieranie źródeł, porównywanie zmian,
   weryfikacja, usuwanie duplikatów i oznaczanie nieaktualnych informacji.
3. Ocena strategiczna: propozycje inicjatyw i eksperymentów na podstawie wiedzy,
   realnych kompetencji, kosztów, wyników sprzedaży i celów właściciela.

Każda istotna informacja ma źródło, datę publikacji, datę sprawdzenia i ocenę
pewności. Brak dostępu do źródła nie oznacza braku zmian. Harmonogram sprawdzeń
jest zależny od tematu i limitu kosztów; panel pokazuje ostatnią udaną aktualizację.
Treści zewnętrzne są danymi do analizy i nie nadają agentom uprawnień.

Agent badawczy zbiera sygnały, analityk oddziela popularność od popytu,
kierownicy oceniają wykonalność, a orkiestrator przedstawia rekomendację:
co się zmieniło, źródła, możliwa wartość, koszt, niepewność i mały eksperyment.
Zmiany strategiczne pozostają w gestii właściciela. Kolejność zwykłej pracy
może być dostosowywana w ramach zaakceptowanych celów i limitów.

Pobranie nowych dokumentów aktualizuje bazę wiedzy, nie wagi modelu językowego.
Trening i adaptacja modeli pozostają wersjonowanymi eksperymentami opisanymi
w sekcji laboratorium modeli.

Odbiór: raport wskazuje źródła i ich aktualność, wyjaśnia wpływ na aktywne
projekty, odróżnia fakty od hipotez i pozwala prześledzić rekomendację do dowodów.

## Modele przychodów i wybór pracy

System powinien porównywać zlecenia, wdrożenia, utrzymanie abonamentowe,
własne SaaS, dostęp do generatorów i API, licencje, szablony, komponenty
oraz opłaty platformowe. Każdy kanał potrzebuje hipotezy popytu, kosztów,
metryk konwersji, retencji i rzeczywistej marży po kosztach modeli, infrastruktury,
komunikacji, jakości i poprawek. Nie zakłada się, że uruchomienie każdego
możliwego kanału jednocześnie zwiększa przychód.

Orkiestrator dobiera pracę do aktualnej zdolności dostarczenia, przewidywanej
wartości, kosztu, zależności i pewności estymacji. Właściciel ustala portfolio
oraz budżety. Automatyzacja działa wewnątrz istniejących zasad uprawnień.

Integracja platform zleceń jest osobnym adapterem. Upwork wymaga zatwierdzonego
zakresu użycia API; początkowy import wymagań przez właściciela pozwala testować
realizację bez tej integracji. Źródło:
[Upwork — automatyzacja](https://support.upwork.com/hc/en-us/articles/43342677368467-Use-bots-and-other-automation-properly).

## Stan kodu i pierwszy dowód kompletnego przepływu

Przegląd z 2026-09-12 potwierdza API, modele projektów i zadań, kolejkę,
orkiestrator, klientów LLM, zatwierdzenia, audyt oraz pulpit integracyjny.
`app/brain/planner.py` sortuje istniejące zadania według priorytetu.
`app/services/production_executor.py` uznaje niepusty wynik za sukces operacji,
ale ścieżki wykonania API i orkiestratora przekazują go teraz do odbioru.
Nowa próba ma status `awaiting_review`; zadanie pozostaje `in_progress`.
Właściciel odczytuje konkretną próbę przez `GET /api/tasks/{id}/review`,
a `POST /api/tasks/{id}/review` przyjmuje decyzję, checksumę wyniku, uzasadnienie
i dowody. Akceptacja ustawia `completed`; odrzucenie ustawia `blocked`.
`POST /api/tasks/{id}/review/retry` kolejkuje poprawki jako nową próbę.
Raport odbioru trafia do istniejącego modelu `Artifact`, a decyzja do audytu.
Ten etap jest odbiorem deklarowanym przez właściciela, nie automatycznym testem
funkcjonalności wygenerowanego produktu. Dotychczasowe `verify` nadal oznacza
kontrolę integralności; dawne zadania nie otrzymują wstecznie statusu odbioru.
`app/tools/registry.py` udostępnia operacje na plikach. Nie są to jeszcze
kompletne procesy budowy i niezależnego odbioru aplikacji.

Pierwsza realizacja demonstracyjna powinna połączyć dwa wymagania właściciela:
dopracowany fragment pulpitu 3D i wykonanie niewielkiego produktu end-to-end.
Właściciel przekazuje wymagania; kierownik tworzy plan; wykonawcy budują produkt
w odrębnym środowisku; kontroler uruchamia testy i przeglądarkę; pulpit pokazuje
artefakty, koszty, blokady, wynik odbioru i działający podgląd. Ten scenariusz
nie wymaga aktywowania wszystkich działów ani trenowania modelu od podstaw.

To kryterium pierwszego etapu. Szczegółowe zadania wykonawcze mają trafić
do istniejącego drzewa i projektów, a ich postęp ma wynikać z dowodów.
