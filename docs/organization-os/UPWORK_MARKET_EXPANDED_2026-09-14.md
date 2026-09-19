# Upwork: rozszerzona próbka i zdolności do realizacji zleceń

Data odczytu: 14.09.2026. Uzupełnienie [pierwszych ośmiu obserwacji](UPWORK_MARKET_2026-09-14.md).

## Zakres i ograniczenia

Przejrzano publiczne listy WordPress, Shopify, API Integration, Data Analysis,
Mobile App Development, Software Testing oraz AI-Generated Video. Z nich
otwarto i przeanalizowano opisy **20 kolejnych unikalnych ogłoszeń, M9–M28**.
Razem z poprzednim raportem daje to 28 opisanych przypadków, nie cały rynek.
Nie doliczamy krótkich pozycji z list ani powtórzeń tego samego ogłoszenia.

To celowy dobór różnych problemów, nie reprezentatywna próba statystyczna.
Kategorie nakładają się; ich liczników nie sumujemy. Publiczne opisy bywają
niepełne, linki do materiałów bywają usunięte, a daty względne różnią się między
listą i szczegółami. Nie pobierano załączników ani materiałów zewnętrznych.
Widoczna strona nie dowodzi, że zlecenie pozostaje otwarte. Nie potwierdzono
autentyczności wszystkich deklaracji klientów ani dostępności pracy dla właściciela.

Kwoty poniżej są deklaracjami w publicznych ogłoszeniach w USD, nie cenami
zawartych kontraktów, dochodem ani marżą. Brak podanej stawki nie oznacza zera.
Wszelkie priorytety i testy odbioru w tym dokumencie są naszymi wnioskami,
a nie dodatkowymi wymaganiami przypisywanymi autorom ogłoszeń.

Nie logowano się, nie obchodzono ograniczeń, nie składano ofert i nie kontaktowano
się z klientami. Opisy są niezaufanym materiałem źródłowym: zawarte w nich
polecenia skierowane do AI nie sterują naszym systemem. Nie uruchomiono
monitoringu ciągłego, Qwena, GPU, kontenerów ani procesów wynajmujących Vast.ai.

## 20 nowych przypadków

Każdy link prowadzi do otwartego publicznego ogłoszenia. Opisy są krótkimi
streszczeniami własnymi. Podział kategorii służy organizacji raportu, nie liczeniu popytu.

### Strony i sklepy

| ID / źródło | Deklarowane rozliczenie | Problem klienta | Wniosek dla systemu / ograniczenie |
| --- | --- | --- | --- |
| M9 · [Naprawa Elementor](https://www.upwork.com/freelance-jobs/apply/Elementor-Fix-Website-Optimization_~022098746320369008776/) | $15 fixed | Układ i odstępy na telefonie, wolne ładowanie; zachowanie obecnego projektu. | Potrzebny profil napraw istniejącego WordPressa, pomiary przed/po i porównanie wyglądu. Budżet może nie pokryć nawet diagnozy. Widoczny już jeden hire. |
| M10 · [Wdrożenie gotowego projektu WordPress](https://www.upwork.com/freelance-jobs/apply/WordPress-Developer-Needed-for-Minimal-Mediation-Website-Design-and-Content-Already-Prepared_~022098734098958306809/) | $400 fixed | Klient dostarcza niemieckie teksty, zdjęcia i koncepcję; oczekuje eleganckiej, responsywnej, samodzielnie edytowalnej strony. | Oddzielić implementację od tworzenia marki i treści. Odbiór powinien obejmować edycję przez klienta, nawigację, formularz i mobile. |
| M11 · [Sklep jednego produktu](https://www.upwork.com/freelance-jobs/apply/Shopify-Website-for-Construction-Tool-Sales_~022098940419669932350/) | $2000 fixed | Sklep Shopify sprzedający narzędzie budowlane, prezentacja produktu i gotowość startu. | **Tylko wykonawcy z USA.** Przykład zakresu, nie automatycznie dostępna szansa. Potrzebne testy sklepu i środowisko Shopify, nie tylko HTML. |
| M12 · [Warianty produktów Shopify](https://www.upwork.com/freelance-jobs/apply/Shopify-Product-Variant-Setup_~022098939913031138669/) | $100 fixed | Poprawne warianty koloru, rozmiaru i stylu oraz zmiana zdjęcia po wyborze. | Wąski, mierzalny zakres: tabela kombinacji, obraz/wybrany wariant/koszyk muszą być spójne; kontrola nieistniejących kombinacji. |
| M13 · [Canva w aplikacji digital signage](https://www.upwork.com/freelance-jobs/apply/Canva-API-Integration-for-Digital-Signage-App_~022098303462150055517/) | $800 fixed | Dane promocji trafiają do szablonu Canva, użytkownik edytuje, wynik wraca do aplikacji i na ekrany; obecny edytor pozostaje. | Integracja dwukierunkowa i aktualizacja danych, nie proste generowanie grafiki. Przed wyceną sprawdzić dostępność wymaganych operacji API i uprawnień konta. |
| M14 · [Sprzedaż → realizacja → księgowość](https://www.upwork.com/freelance-jobs/apply/Automation-Developer-Connect-GoHighLevel-Monday-Ignition-and-QuickBooks_~022098232167478607213/) | Hourly; płatna próba do 5 h | GoHighLevel, monday.com, Ignition, QuickBooks; brak duplikatów i zgubionych przekazań. Preferowane rozwiązanie o małych kosztach stałych, m.in. bezpośrednie API lub własne n8n. | Moduły synchronizacji, identyfikatory rekordów, raport awarii, test próbny. Własny hosting też ma koszt utrzymania. |

### Dane, analityka i integracje branżowe

| ID / źródło | Deklarowane rozliczenie | Problem klienta | Wniosek dla systemu / ograniczenie |
| --- | --- | --- | --- |
| M15 · [Utrzymanie Power BI](https://www.upwork.com/freelance-jobs/apply/Dynamic-Power-Developer-Provide-Support-and-Enhancement-Business-Intelligence-Solutions_~022097592013595478978/) | Hourly, 1–3 mies. | Rozwój istniejących raportów, modeli i integracji danych, diagnoza wydajności oraz dokumentacja. | **Tylko wykonawcy z USA.** Zdolność analizy danych nie zastępuje dostępu do narzędzia i doświadczenia w Power BI. |
| M16 · [Excel → Tableau](https://www.upwork.com/freelance-jobs/apply/Tableau-Dashboard-Creation-from-Excel_~022097752710692090455/) | $10–25/h | Zestaw interaktywnych dashboardów z arkusza Excel. | Potrzebne uzgodnienie definicji metryk, kontrola danych wejściowych, filtrów i eksportu; zwykły wykres webowy nie jest dostawą Tableau. Widoczne 50+ ofert. |
| M24 · [CRM nieruchomości → WordPress oraz formularze → CRM](https://www.upwork.com/freelance-jobs/apply/WordPress-Developer-Automate-Property-Sync-Lead-Integration-from-Real-Estate-CRM-XML-Feed_~022098308563738405709/) | $20–30/h | Codzienny XML tworzy, aktualizuje i usuwa oferty Houzez; osobne adresy ofert, zdjęcia, dane i synchronizacja zapytań klientów. | Import z aktualizacją/usunięciem i potwierdzonym mapowaniem. Test przerwanego lub pustego feedu musi chronić przed masowym skasowaniem ofert. |
| M25 · [Audyt integracji restauracyjnego POS](https://www.upwork.com/freelance-jobs/apply/POS-Integration-Audit-Technical-Architecture-Plan-for-Restaurant-App_~022098350043533487768/) | $25–47/h | Ocena architektury zamówień, płatności i lojalności, plan integracji Toast/Square, dokument i omówienie. | Można sprzedawać diagnozę przed implementacją, ale wymagane jest udokumentowane doświadczenie branżowe. Raport wygenerowany bez dostępu i weryfikacji nie wystarczy. |
| M28 · [HubSpot: jakość danych i raportowanie](https://www.upwork.com/freelance-jobs/apply/HubSpot-RevOps-Systems-Analytics-Analyst-Ongoing-Pacific-Hours_~022097782890045221709/) | Hourly, ponad 6 mies. | Czyszczenie CRM, SQL, raporty, zgodność liczb i monitorowanie integracji; najpierw symulacja, klient zatwierdza operacje strukturalne/destrukcyjne. | Wymagane doświadczenie, certyfikacja i dostępność 9–17 czasu Pacific. Płatna próba na zanonimizowanym arkuszu. To praca operacyjna z odpowiedzialnością, nie sam generator kodu. |

### Mobile i jakość

| ID / źródło | Deklarowane rozliczenie | Problem klienta | Wniosek dla systemu / ograniczenie |
| --- | --- | --- | --- |
| M17 · [Audyt wydajności React Native](https://www.upwork.com/freelance-jobs/apply/React-Native-Performance-Audit_~022098758567047171850/) | $40–50/h; początkowo 3 h | Profilowanie przejścia od uruchomienia do listy/profilu i powrotu; lista przyczyn i priorytetów napraw. | **Tylko wykonawcy z USA.** Mierzalny audyt jest osobnym produktem; nie obiecywać naprawy wszystkich problemów w czasie diagnozy. |
| M18 · [Istniejąca aplikacja na desktop i telefony](https://www.upwork.com/freelance-jobs/apply/Convert-App-Desktop-and-Mobile_~022098774082071350777/) | $2500 fixed | Rozszerzenie aplikacji Repaint na desktop/iOS/Android, trwałe dane i integracja QuickBooks Online. | Najpierw audyt możliwości eksportu i istniejącej architektury. Trzy platformy plus integracja to rozległy zakres; budżet nie dowodzi wykonalności. |
| M19 · [Flutter dla HRMS](https://www.upwork.com/freelance-jobs/apply/Flutter-App-for-HRMS_~022098819076136079114/) | $3000 fixed | Mobilny interfejs istniejącego SaaS kadrowego, projekt UX i integracja procesów HR. | Potrzebne lista procesów, kontrakt backendu, konta i role oraz testy urządzeń. Brak szczegółów zakresu wymaga doprecyzowania przed ceną i terminem. |
| M20 · [Make: testowanie i naprawa workflow](https://www.upwork.com/freelance-jobs/apply/Make-com-Automation-Specialist-Troubleshooting_~022098474011690711653/) | Hourly, 1–3 mies. | Kontrola scenariuszy, triggerów, mapowania, webhooków i niezawodności; wdrożenie poprawek we współpracy z istniejącym zespołem. | Mocne dopasowanie kierunku diagnostyki do integracji; obecna kontrola próbki JSON jest tylko jednym etapem, nie takim pełnym wykonawcą. |
| M21 · [Automatyczne testy mobile/web/API](https://www.upwork.com/freelance-jobs/apply/Mobile-Automation-Engineer-Appium-Playwright-Claude-MCP-iOS-Android_~022098517776364317517/) | $10–30/h | Appium i Playwright, integracja CI, AI wspierające QA, raport zakresu testów i decyzji o wydaniu; realne urządzenia lub chmura urządzeń. | Wymagane portfolio frameworka. To uzasadnia osobną zdolność QA, lecz obecne testy naszego panelu nie potwierdzają obsługi iOS/Android klienta. |

### Media AI i większe platformy

| ID / źródło | Deklarowane rozliczenie | Problem klienta | Wniosek dla systemu / ograniczenie |
| --- | --- | --- | --- |
| M22 · [Kreacje produktowe, wideo i 3D](https://www.upwork.com/freelance-jobs/apply/Hiring-Creative-Video-Editor-Product-Visualizer-Product-Animator_~022098924903318208648/) | $1500 fixed; opis współpracy ciągłej | Warianty reklam, materiały produktowe i animacje w dużej skali; portfolio i rozumienie testowania kreacji. | Uzgodnić liczbę materiałów, czas, formaty, poprawki i źródła. Kwota nie oznacza ceny za jeden film ani gwarantowanego miesięcznego wynagrodzenia. |
| M23 · [Film demonstracyjny produktu](https://www.upwork.com/freelance-jobs/apply/Urgent-Minute-Software-Product-Video-Hour-Deadline_~022098932006168313197/) | Metadane $15–40/h; opis prosi o fixed quote | Trzyminutowy montaż dostarczonych nagrań, narracja, napisy, MP4 i edytowalny projekt. Najpierw płatna próbka. | Termin podany jako 14.09, 8:00 ET, oraz widoczny hire: nie traktować jako pewnego aktywnego leada. Niezgodność rozliczenia do wyjaśnienia. Nie wymaga tworzenia modelu wideo od zera. |
| M26 · [Platforma wielu luksusowych marek](https://www.upwork.com/freelance-jobs/apply/Build-Cloneable-Luxury-Brand-Website-Master-Platform-Next-Sanity-Shopify_~022098962282352061261/) | $20–50/h, 3–6 mies. | Next.js/Sanity/Shopify, ok. 10 niezależnych marek, 58 rynków, lokalizacje, RTL, media, dostępność, CI/CD i instrukcja klonowania. | Wyraźnie określona architektura, a nie dowolny wybór „najlepszych technologii”. Wymagane odseparowanie marek i utrzymanie. Nie jest pierwszym szybkim pilotem. |
| M27 · [Rekomendacje dla Shopify](https://www.upwork.com/freelance-jobs/apply/Powered-Shopify-Recommendation-System_~022098935212452457293/) | $20–25/h, 1–3 mies. | Katalog ok. 8000 produktów, rekomendacje z historii i zakupów, sensowny wynik także dla nowego użytkownika, desktop/mobile. | Potrzebne dane i ocena trafności, szybkość oraz fallback bez historii. Etykieta entry level nie czyni problemu prostym. Model generujący tekst nie jest automatycznie systemem rekomendacji. |

## Co poszerzać w istniejącym systemie

Poniższa kolejność jest oceną inżynierską i biznesową z ograniczonej próbki.
Nie jest rankingiem całego Upwork ani nową, niezależną roadmapą. Gałęzie
odnoszą się do istniejącego planu; przypisanie nie zwiększa ich postępu.

| Priorytet | Wspólna zdolność / przykłady | Miejsce w planie | Dowód gotowości przed obietnicą klientowi |
| --- | --- | --- | --- |
| 1 | Praca na istniejącym projekcie i naprawa, M9/M12/M20 | `platform.delivery`, `platform.frontend`, `quality-security` | Bezpieczny import; odtworzony błąd; minimalna poprawka; niezależny test regresji; różnica plików i odtwarzalna paczka. |
| 1 | Integracje i niezawodne workflow, M13/M14/M20/M24 | `platform.integrations`, `ai-automation.agents`, `operations` | Mapowanie, walidacja, dozwolone hosty, poświadczenia poza kodem, retry, trwała deduplikacja, tryb próbny, kolejka błędów; odbiór w sandboxie usług. |
| 2 | Import i kontrola jakości danych, M16/M24/M28 | `platform.data-identity`, `web-platforms.business` | CSV/XLSX/XML na danych testowych; raport rekordów błędnych/duplikatów; uzgodnienie sum; bezpieczny eksport; podgląd zmian przed zapisem. |
| 2 | Strony i sklepy na konkretnych platformach, M9/M10/M12 | `digital-experience.websites`, `digital-experience.commerce`, `digital-experience.performance` | Oddzielne profile WordPress/PHP i Shopify; testy wariantów, formularzy, mobile, dostępności; kopia i cofnięcie zmiany. Nie otwierać sieci starego runnera bez ograniczeń. |
| 2 | QA jako rezultat dla klienta, M17/M20/M21 | `quality-security`, `platform.delivery` | Raport reprodukcji, scenariusze wejście→wynik, zakres nietestowany, CI i powtórzenie na tej samej wersji. Własny test wykonawcy nie może sam zatwierdzić jego pracy. |
| 3 | Aplikacje z kontami, bazą i rolami; większe platformy, M18/M19/M26 | `web-platforms.business`, `web-platforms.saas`, `platform.data-identity` | Profil zależności, migracje, izolacja klientów, testy uprawnień i odtwarzania. Dopiero później pakowanie mobilne i wiele niezależnych wdrożeń. |
| 3 | AI i rekomendacje, M27 oraz M6/M7 z poprzedniej próbki | `ai-automation.recommendations`, `ai-automation.rag`, `ai-automation.evaluation` | Zbiór referencyjny, porównanie z prostą metodą bez LLM, brak zmyślania produktów, wyniki dla braku danych, latency i koszt na operację. |
| Później / po wynajmie | Media i aplikacje mobilne, M18/M19/M21/M22/M23 | `ai-automation.generators`, `digital-experience.design`, `web-platforms.business` | Media: spójny produkt, prawa do materiałów, format i kontrola jakości. Mobile: środowiska docelowe, podpisywanie i rzeczywiste urządzenia. Oddzielny dostęp do zasobów; nie ruszać Vast.ai. |

### Najważniejsza korekta kierunku

Nie wystarczy generować nowych miniaplikacji. Próbka obejmuje poprawianie
tego, co klient już ma, często z narzuconą platformą. Dlatego następna
zdolność wykonawcza powinna pozwalać **bezpiecznie przyjąć istniejący projekt,
odtworzyć problem, naprawić go i dostarczyć test regresji**. Powinna korzystać
z obecnych paczek, dowodów, porównań i odbiorów, zamiast je duplikować.

Obecny profil `python-web-v1` pozostaje ograniczony. Nie jest wykonawcą
WordPressa, Shopify, Tableau, Fluttera ani integracji produkcyjnych.
Żaden wpis M9–M28 nie został oznaczony jako w pełni obsługiwany teraz.

## Jak przełożyć szerokość możliwości na zarabianie

Proponowany model usług, wymagający potwierdzenia pilotami:

1. **Ograniczona diagnoza** — jeden przepływ lub problem; wynik to przyczyna,
   dowód, proponowana poprawka i zakres. Możliwość oddzielnej płatnej diagnozy
   ilustrują M17/M25, a małe płatne próby M14/M23/M28.
2. **Naprawa albo wdrożenie ustalonego zakresu** — cena i odbiór dla konkretnych
   funkcji, nie nieograniczone „napraw wszystko”. Niewyjaśnione ryzyka przed wyceną.
3. **Utrzymanie i kolejne usprawnienia** — uzgodniony zakres monitorowania,
   raporty, poprawki i czas reakcji. M14/M15/M20/M28 sygnalizują taką potrzebę;
   żadne ogłoszenie nie gwarantuje nam stałego kontraktu.

Przed rekomendacją zlecenia system powinien sprawdzać kolejno:

- kwalifikowalność: kraj, język, godziny, indywidualny wykonawca/zespół,
  wymagane doświadczenie, portfolio i certyfikaty;
- rzeczywistą zdolność wykonania: profil uruchomieniowy, środowisko testowe,
  dostępy, dane, zewnętrzne koszty i ograniczenia licencji;
- jasność zakresu i dowodu odbioru oraz rozbieżności między opisem i metadanymi;
- szacowany cały nakład: analiza, komunikacja, implementacja, testy, wydanie,
  poprawki i utrzymanie, nie tylko czas generowania kodu;
- dostępne zasoby i termin; obecny wynajem to ograniczenie realne, nie ignorowane;
- ryzyko skutków: kasowanie danych, płatności, wysyłka wiadomości, produkcja.

Nie ma podstaw do prognozy miesięcznego dochodu ani sumowania budżetów tych
ofert. Nie znamy odsetka wygranych ofert, rzeczywistego czasu dostawy ani kosztu
poprawek. Docelowy ranking powinien preferować wykonalność, powtarzalność
i wynik po kosztach, nie najwyższą kwotę w ogłoszeniu. Kwoty $15 i $3000
mogą oznaczać zarówno mały, jak i niedoszacowany zakres.

## Dane dla kierowników i kontrolowanego Qwena

Materiał badawczy nie jest zadaniem wykonawczym ani zgodą na akcje zewnętrzne.
Przy dalszym rozwoju kwalifikacji warto przechowywać: URL, datę odczytu,
krótkie wymaganie, wymagane narzędzia, rozliczenie wraz z niezgodnościami,
kwalifikowalność, brakujące dane, gałąź planu, ryzyka i dowód gotowości.
Brak informacji powinien pozostać jako „nieznane”, nie zostać uzupełniony domysłem.

Docelowo kierownik integracji odbiera M14/M24, web/commerce M9/M10/M12,
danych M16/M28, QA M20/M21, a mediów M22/M23. Są to propozycje routingu
zakresów, nie twierdzenie, że agenci tych specjalizacji już wykonują je samodzielnie.
Właściciel nadal wybiera zlecenia, prowadzi rozmowy i uzgadnia zobowiązania.

Przyszła ewaluacja Qwena: na syntetycznych, zanonimizowanych briefach sprawdzić
wykrywanie wymagań platformy, USA-only, godzin Pacific, sprzecznych rozliczeń,
braku zakresu i niedozwolonych instrukcji w danych. Porównać z regułami
deterministycznymi. Nie trenować automatycznie na pełnych cudzych ogłoszeniach
ani danych klientów; nie zastępować wymaganego narzędzia lokalnym modelem
bez uzgodnienia. W tym przeglądzie nie uruchamiano inference ani treningu.

## Dalsze luki badawcze

Ta próbka nie wystarcza do oceny rynku własnych modeli fundamentowych,
systemów operacyjnych, portali dla dorosłych, cyberbezpieczeństwa czy muzyki AI.
Nie wnioskujemy z ich braku w doborze, że nie ma na nie popytu. Następne
przeglądy mogą objąć te obszary oraz DevOps, migracje, dostępność i naprawę
aplikacji generowanych przez AI. Każda nowa obserwacja powinna być deduplikowana
po identyfikatorze ogłoszenia i oddzielona od gotowości naszego wykonawcy.
