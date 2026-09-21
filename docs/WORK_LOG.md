# Dziennik budowy AI Company

## 2026-09-21 — rodziny treningowe, odbiór źródeł i nazwane pomiary

- Dodano zamrożony program: trzy rodziny train, jedna validation, jedna
  test i historyczna development. Hash briefu, rzeczywiste żądanie modelu
  i rodzina są sprawdzane łącznie; odrzucane są podmiany i uczenie na
  rodzinach zarezerwowanych. Nie generowano odpowiedzi validation/test.
- Sześć generacji źródeł: garden source-cflale3j przyjęty; restaurant
  source-9ssbsod1 miał niewidoczny nagłówek, poprawiony przez model
  w source-x83gkexn; vinyl source-q5jz4pm7 miał tylko siedem tekstów,
  source-le2p1wz7 przekraczał dolny margines, source-k3vaexfx przyjęty.
  Nieudana próba odczytu PNG źródła bez renderu nie zmieniła plików.
- Dodano feedback źródła z hashami raportu/request/response, obsługą
  niepoprawnej surowej odpowiedzi i rekurencyjnym sprawdzaniem historii.
  Limit napraw zwiększono z jednej do trzech po ujawnieniu kolejnego błędu
  marginesu. Model dostaje własną ostatnią odpowiedź i opis usterki.
- Niezależna ocena obrazu wiązana hashem jest wymagana dla źródeł train.
  Nowy audyt źródła bez inferencji: source-audit-ml8srxj3 wykrył wszystkie
  13 niewidocznych znaków tytułu restauracji, source-audit-x11pwfa6 nie
  znalazł usterek ogrodu. Przybliżona kontrola kolorów nie zastępuje oceny
  wzrokowej ani pełnego badania kontrastu.
- Trzy odtworzenia: recreate-p6excl30, recreate-t0pb23da,
  recreate-7rahyvl2; teksty 8/8, odbiór 0/3. Błędy RGB odpowiednio
  0,110406; 0,032371; 0,056062. Ogród zmieniał układ i symbol;
  restauracja miała za wąski podtytuł; płyty przekraczały marginesy.
- Restaurant patch-npxucbhj zmienił y i nie usunął błędu szerokości.
  Nowy profil named-deltas-v1 wskazuje nazwy wymiarów, nie rozwiązanie.
  patch-os5fviqb: model wybrał font-size 18→20; siedem chronionych pól
  bez zmian, pomiary i rzeczywisty PDF zaliczone, replay --verify poprawny.
  Obejrzano wynik i odebrano lokalną lekcję, z jawnymi różnicami typografii,
  panelu i kolorów. Nie przyjęto idealnej reprodukcji lub produktu do druku.
- Wszystkie SVG i poprawki są autorstwa lokalnego modelu; system stosował
  dosłowne operacje. Nie zmieniano produkcyjnych wag, routingu ani UI.
  Prywatne doświadczenie train ma SHA-256
  95b4885fa0e41898e95cbab14c5db0fb27b3eeb89850029ae19eafaa36b51d18;
  ocena nauczyciela 8a145f18800b3ad4969b1254e430d0bdbf136a919b22d118a7102a5b4f1aed4c.
  Brak eksportu SFT i treningu; integracja z trenerem pozostaje do wykonania.
- Ocena cohort-001-assessment.json: 11 wywołań modelu, 78,173 s etapów
  generowania/renderu, trzy zaakceptowane wzorce, jedna lokalna lekcja.
  Nie obejmuje to czasu przygotowania i oceny. SHA-256
  fb9bad403844cadcef029c645337cee77d4be33da8df9ea505c6decd5e7a21ac.
- Testy: test_vector_school, test_local_ollama, test_interior_school,
  test_vision_training_inputs — 106 passed w 2,40 s. Surowe odpowiedzi,
  obrazy, raporty i doświadczenia pozostają poza publicznym repozytorium.

## 2026-09-21 — poprawka SVG wybrana przez model, bez przepisywania całości

- Poprzedni etap stanowił postęp: realne SVG/PDF, cztery nieudane
  odtworzenia i rozpoznane regresje. Stan repozytorium404b3d1 czysty;
  odczytano aktualny kod i rzeczywisty najlepszy wariant456pyqiw.
- Dodano vector_patch_school: model dostaje obraz, katalog istniejącego
  własnego SVG i wyznaczone pomiarem błędy. Odpowiada operacjami zmiany
  istniejących atrybutów. System sprawdza stare wartości, chronione
  elementy, brak duplikatów/iniekcji i stosuje wyłącznie dosłowne operacje
  modelu. Nie wylicza poprawnego SVG lub nowych wartości za wykonawcę.
- Ograniczenie tej lekcji: poprawne teksty, widoczność i globalne progi
  obrazu już zaliczone; pozostają błędy geometrii tekstu. To moduł naprawy,
  nie zamiennik pełnego tworzenia przez model ani zawężenie celu pięciu usług.
- Kontrola zasobów potwierdziła31300MiB wolnej pamięci (około30,6GiB),
  brak aktywnych kontenerów i bezczynne usługi. Formalna
  eskalacja nowego skryptu dotyczyła dostępu do lokalnej Ollamy i własnego
  Chrome. Nie zatrzymywano cudzych usług ani nie sterowano pulpitem.
- patch-8ykjbubf: Qwen3.8:27b, istniejący digest22130167…79643,
  ctx8192/predict1200/thread4. Model sam wybrał font-size daty20→22
  i stopki25→23. Odpowiedź61tokenów, prompt2299tokenów, inferencja4,011s,
  cały etap4,528s. Kontrakt i feedback nie zawierały tych dwóch operacji.
- Po zastosowaniu patcha8/8tekstów dokładnych,8/8pól w tolerancji12,
  6chronionych bez zmiany. Błąd RGB0,03541481, udział różnic0,04725708,
  brak zasłoniętych znaków. Niezależne porównanie źródeł wykazało tylko
  2różne bajty przy identycznej długości. PDF rzeczywiście ponownie
  odczytany i sprawdzony, z osadzonymi fontami i bez rastrów.
- Obejrzano wynik. Przyjęto lokalną lekcję naprawy, nie całą usługę ani
  idealną reprodukcję: pozostały drobne różnice kształtów/kolorów/typografii
  mieszczące się w roboczych tolerancjach. Raport nadal jawnie wymaga
  niezależnej oceny; decyzja nauczyciela jest osobnym związanym plikiem.
- Audyt--verify odtwarza dokładny patch z modelowej odpowiedzi i sprawdza
  poprzednika, request, SVG, hashe, pomiary oraz PDF. Archiwizacja odbioru
  zapisuje dokładne wiadomości i obraz jako doświadczenie development,
  bez eksportu SFT i uruchamiania treningu. Plikexperience.json SHA
  e6c4040d5fe836119a00002f5633d760ea6e3e95482fa6085e6505a18a7243fa.
- Testy53passed po operacjach, końcowo96passed/2,20s z kontrolą autorstwa,
  regresji, odbioru, dotychczasowych kontraktów i wejść treningowych.
  Model/adapter/routing/UI/liveDB bez zmian. Następny etap: szersza partia
  i jawne rodziny train/validation/test, nie kolejny trening na jednym sukcesie.

## 2026-09-21 — modelowe odtworzenia ulotki i eksport wektorowy

- Po wyjaśnieniu granicy autorstwa podjęto nową praktyczną pracę: lokalny
  model tworzy syntetyczny wzorzec, potem odtwarza go z PNG. Asystent
  przygotował kontrakt, runner, feedback i niezależne kontrole; nie naprawiał
  modelowego SVG. Wzorzec nie jest oryginalną ulotką Ping od klienta.
- Dodano vector_school_contract/vector_school/render_school_svg i testy:
  tylko statyczny ograniczony SVG, bez rastrów, skryptów, obcego HTML,
  deklaracji/zasobów. Odrzucanie zamiast sanitizacji. Zachowane surowe
  odpowiedzi, wyodrębnione źródła, wejścia, obrazy, PDF i SHA-256. Zmiana
  modelowego SVG lub pliku źródłowego blokuje dalszą próbę.
- Własny headless Chrome bez pulpitu, GPU i wyłączania sandboxu. CSP,
  blokada żądań renderera, osobny profil, tylko stały kod pomiarowy CDP.
  PDF A5: jedna strona, zachowane słowa, fonty osadzone, brak rastrów.
  Potwierdzono rzeczywiste fonty Liberation Serif/Sans; brak preflightu
  drukarni i zgodności z niepodanymi wymaganiami klienta.
- Pierwszy preflight zatrzymał PermissionError lokalnego socketu w sandboxie,
  przed inferencją. Ponowiono z formalną eskalacją. Kontrole potem wykazały
  wolne zasoby i brak obcych kontenerów; nie zatrzymywano cudzych usług.
- source-xf_vocnb: modelowy wzorzec16,874s,8tekstów+6figur. Obejrzany jako
  materiał ćwiczeniowy, z ograniczeniem kontrastu podtytułu przy pierścieniu;
  nie jest odebranym projektem. Bez ręcznych zmian źródła lub renderu.
- Cztery modelowe rekonstrukcje: vcfusjdd8,242s, ur8u8a9v7,930s,
  456pyqiw7,883s, 4ma9o3817,945s. Każda8/8tekstów dokładnych, lecz0/4
  pełnych zaliczeń. Błąd RGB0,07522→0,04743→0,03780→0,04731;
  pola tekstowe w tolerancji6/8→6/8→6/8→2/8. Nie wybierano ostatniej
  wersji jako lepszej tylko dlatego, że jest nowsza.
- Pierwsza poprawka korzystała z własnego kodu, kolejne z obrazu+feedbacku.
  Uwagi nauczyciela wiązane hashem dokładnego poprzednika. Po zauważeniu
  zasłoniętych liter dodano test centrów znaków; wykrył sześć przykrytych
  znaków. Kolejność warstw została poprawiona przez model, ale przepisywanie
  całości powodowało regresje typografii. Nie wydłużano limitu ponad trzy
  poprawki ani nie zmieniano progów odbioru, aby uzyskać zaliczenie.
- Obejrzano pięć PNG, zapisano teacher-assessment.json w katalogu wzorca,
  SHA14a018bb5c26930dd8f626f2651c3adfca58fee8b98bdf7f88f336b10483223d.
  0odpowiedzi zatwierdzonych do treningu; brak treningu wag, promocji,
  zmian UI/liveDB/routingu. Następna potrzeba: modelowe precyzyjne poprawki
  z kontrolą regresji i szerszy zbiór, nie deklarowanie gotowości usługi.
- Testy etapami54/55/57/61passed, końcowo66passed/1,44s. Rzeczywiste
  eksporty zweryfikowano w istniejącym Chrome153.0.8010.52 i Poppler.
  Własne przeglądarki zakończone; końcowo790MiB GPU,2% obciążenia.
  Dokumentacja i katalog celów zaktualizowane, surowe prace pozostają prywatne.

## 2026-09-21 — niezależna rodzina wizji i porównanie adaptera

- Kontynuacja celu: nowa rodzina cottage-reading-room-001 zarezerwowana
  jako test po treningu na kuchni. Plan lokalnego Qwena22.200s,
  trzy obrazy Z-Image165.023s, źródła plan-lio0gych/render-m14illll.
  Asystent nie pisał promptów realizacji ani nie zmieniał obrazów.
- Dodano propagację curriculum/data_split/family. Inspekcja szkoleniowa
  odrzuca test; eksporter odrzuca także testowy render pod treningową etykietą
  raportu. Historyczne ćwiczenie kuchni zachowuje train. Odpowiedzi egzaminu
  nie są rekordami SFT ani materiałem do poprawiania przez model.
- Zamrożono instrukcję, pięć kryteriów, adapter SHA i trzy obrazy przed
  sześcioma generacjami. Ten sam model HF bnb4 z adapterem wyłączonym/włączonym,
  greedy/context4096/max1100tokens/90s. Bez gramatyki JSON Ollamy.
- vision-transfer-v0toop42 ukończony119.866s;6/6EOS, bez limitowego ucinania.
  Porównano hashe wejść obu faz. Obejrzano obrazy i anonimowe odpowiedzi;
  zapisano judgments przed odsłonięciem faz, dodatkowo sprawdzono długości.
- Baza10/15, adapter9/15; pełne wymagania0/3→0/3, struktura3/3→2/3.
  Adapter zwrócił raz wrapper schematu zamiast danych. Pozostałe problemy:
  niepotwierdzone szczegóły/typy obiektów i limity zwięzłości. Wszystkie
  odpowiedzi zachowane dokładnie, bez ręcznego usuwania błędów dla zaliczenia.
- comparison.json SHA005e9daabc28425153b06b1ab935e5a947b00385ec31758af0409ae28437b216;
  promotion-decision.json:do_not_promote, hash raportu/oceny. Brak zmiany
  aktywnego modelu i treningu na egzaminie. Jedna nowa rodzina, trzy obrazy,
  nie statystyczny dowód jakości asystenta lub gotowości pięciu usług.
- Testy:24passed po propagacji metadata,28 po testach oceny,
  końcowo57passed/1.26s. Dodano wykrywanie podmiany mapowania i obrazu po
  generacji. Bez UI, live DB, zależności, ręcznych poprawek produktów lub
  publicznego zapisu obrazów/modelowych odpowiedzi. Dokumentacja uaktualniona.

## 2026-09-21 — działający trening obraz–tekst, osobny adapter

- CPU audyt zatwierdzonego rekordu w istniejącym środowisku ML, offline,
  bez wag i CUDA. 1552 tokeny, 1283 zamaskowane, 269 odpowiedzi, 384 obrazu.
  Rzeczywiste piksele i dokładny sufiks sprawdzone; brak obrazu odrzucony.
  Dwa raporty audytu, przed/po wydzieleniu maski do niezależnych testów.
- Dodano jawny protokół trzech aktualizacji dla integracji wejścia, nie
  eksperymentu jakości. QLoRA r4/alpha8 w części językowej pełnego VLM,
  enkoder wizji zamrożony, batch1, lr1e-5, AdamW, niezmienione dane modelowe.
- vision-input-sft-ow7veubi: preflight prawidłowy, ale pierwszy forward
  zakończył się błędem packed weight bez quant_state; 0 kroków, brak adaptera.
  Nagłówek safetensors zawiera metadane; lokalny loader 5.5.0 błędnie stosuje
  konwersję nazw tekstowego podmodułu wewnątrz pełnego modelu. Dokumentacja
  upstream sprawdzona; nie kopiowano w ciemno diagnozy uszkodzonego checkpointu.
- Dodano procesowe wyłączenie wyłącznie rozpoznanej konwersji na czas ładowania,
  z przywróceniem finally i kontrolą stanów wszystkich warstw. Bez modyfikacji
  bibliotek, aktualizacji pakietów, pobierania nowych wag lub restartów usług.
- vision-input-sft-uiau78tj: Docker pusty, Comfy nie słucha, GPUfree31101MiB;
  352 warstwy zweryfikowane. 3 kroki, 29 181 952 parametrów LoRA,
  loss0.361193/0.359410/0.358137, obraz przetworzony 3 razy, LoRA_B zmienione.
  Całość51.091s, peakVRAM23 602 985 472B. Plik116 876 728B,992tensoryLoRA,
  SHA1ead1a8413150f3b7d172d0db2e0e654b7ac56926fffff702c7c1ab5e44b5f52
  potwierdzone niezależnym odczytem. Oryginalne wagi/routing bez zmian.
- Końcowo52 testy passed/1.16s. Początkowe20 testów masek/danych,
  następnie51 i dodatkowy test przywracania rejestru. Jedno pomocnicze
  git status wykonano poza repo; poprawiono katalog, bez skutków ubocznych.
- GPU po zakończeniu993MiB/5%. Bez wdrożenia, generacji egzaminacyjnej
  lub deklaracji wzrostu jakości na podstawie loss jednego przykładu.
  Szczegóły w VISION_TRAINING_INPUTS.md. Kolejne wymagane etapy: szersze
  dane i osobne rodziny oceny, porównanie bazy/adaptera, pozostałe usługi.

## 2026-09-21 — lekcja wizyjna i dokładne dane do późniejszego treningu

- Kontynuacja celu i zmian rozpoczętych przed przerwaniem narzędzia przez
  właściciela. Potwierdzono dwa zakończone przebiegi i obecność uwag; brak
  raportu trzeciej próby. Nowa próba przeszła kontrolę bezczynności i zasobów.
  Właściciel ponownie podkreślił: poprawki realizują modele, nie asystent.
- Dodano profile legacy/schema-visible-v1/grounded-concise-v1. Ten sam schemat
  trafił do instrukcji zgodnie z dokumentacją Ollamy; drugi profil dodaje
  lekcję zwięzłości i opisu popartego widocznymi szczegółami. Schemat API,
  obrazy i parametry generacji nie zmienione. Tytuły koncepcji oznaczono
  jako planowane, bez zmiany modelowych tekstów w nowych paczkach.
- inspect-dm1mo8dj: 20.122 s, inspect-8orm_8o6: 18.709 s,
  inspect-izdxjllv z uwagami: 17.792 s. Dziewięć surowych odpowiedzi zachowane.
  Widoczny schemat współwystępuje z kompletnymi zdaniami w tej próbie;
  sama lekcja nie usuwa błędów obserwacji. Nie jest to pomiar treningu wag.
- Obejrzano ponownie trzy oryginalne PNG, oceniono dziewięć odpowiedzi.
  Pełne obserwacje odebrane: 0/3, 0/3, 1/3. Hero po uwagach zaliczone;
  pin niepewna identyfikacja materiału uciętego uchwytu, detail 17 słów
  zamiast maksymalnie 16 w alt text. Błędy nie zostały poprawione ręcznie.
  Prywatne teacher-judgments.json i assessment-002.json wiążą ocenę hashami.
- Nowy offline interior_learning_records.py sprawdza oryginalny obraz,
  prompt, odpowiedź, render i osobną decyzję nauczyciela. Eksportuje pełne
  rozmowy z PNG do odrębnego formatu; samo candidate nie daje akceptacji.
  Jedna rodzina train dla wariantów tego renderu, zakaz eksportu do test.
- vision-candidates-fyodznnk: jeden zatwierdzony syntetyczny rekord;
  SHA records.jsonl 5533273410e47ca63d78dcef8375d59536ca8f4f13cbdc2f2f82407325176be3.
  ready_for_trainer=false, brak treningu wag. Potrzebny procesor/maski wizji,
  większe dane i niezależne zadania. Tekstowy loader odrzuca ten format.
- Testy: 25 passed po zmianie profilu, 35 passed po dodatkowym teście schematu,
  końcowo 41 passed/0.92 s z kontrolą eksportu i podmiany danych. Bez zmian UI,
  routingu, produkcyjnych zleceń, chmurowej generacji lub publikacji obrazów.

## 2026-09-20/21 — lokalna szkoła obrazów i koordynacji redakcyjnej

- Właściciel ponowił zgodę na działania. Kontynuacja aktywnego celu pięciu
  usług; asystent buduje szkołę i ocenia, realizacje piszą/generują modele.
- Dodano syntetyczny kontrakt Hearth & Linen, etapy plan/render/inspect,
  ograniczony adapter wizji i poprawki powiązane z oryginalnymi odpowiedziami.
  Wykorzystano oficjalny kontrakt Ollama vision (base64 w messages[].images).
  Bez chmury/Midjourney, pobierania modeli lub nowych zależności.
- plan-kzsdwkxm: lokalny bazowy Qwen, plan 33.758 s. render-s51xuqeg:
  trzy PNG 768×512/512×768/768×512 w 159.692 s, natywny Z-Image Turbo,
  8 kroków. Własny ComfyUI 8189 zakończony, dotychczasowe usługi bez zmian.
  Preflight przed etapami, Docker pusty; wagi z dozwolonego montowania ro.
- inspect-179k_n_w: Qwen zobaczył trzy rzeczywiste obrazy bez promptów
  generowania, 30.212 s. Po szczegółowych uwagach nauczyciela kolejna próba
  inspect-kmgzp4m3, 20.173 s. Dokładne odpowiedzi, obrazy, tracker CSV,
  brief autora i pakiet proponowanego URL pozostają na Linuksie prywatnie.
- Obejrzano trzy PNG i wszystkie sześć odpowiedzi. Obrazy to kandydaty
  ćwiczeniowe. Opisy 0/3 przed i 0/3 po: niepewne szczegóły jako fakty,
  nieuzasadnione diagnozy wad, niepełne zdania przy formalnie poprawnym JSON.
  Poprawka skorygowała gatunek drewna i lokalizację ręcznika, lecz dodała
  niewidoczne kosze; jeden alt text ponownie niepełny. Nic nie dopisano ręcznie.
- Prywatna assessment-001.json wiąże ocenę z SHA obrazów/odpowiedzi/paczek.
  Żadne z tych sześciu metadanych nie jest zaakceptowanym rekordem SFT;
  bez eksportu i treningu wag. Nie jest to niezależny holdout ani dowód
  gotowości usługi. Szczegóły i następne lekcje w INTERIOR_SCHOOL.md.
- Testy etapami: 32/33/34 passed, końcowo 34 w 0.72 s. Ostatni dodany
  test sprawdza faktyczne przekazanie PNG i mechaniczne paczkowanie bez
  zmiany tekstu/obrazu lub automatycznego odbioru. Bez live DB i publikacji.
  Jedna pomocnicza komenda odczytu wskazała błędny katalog dokumentacji;
  poprawiono ścieżkę bez wpływu na inferencję. Interfejs bez zmian.
- Końcowa kontrola GPU z sandboxa nie miała dostępu do sterownika; powtórzona
  z wymaganym uprawnieniem wykazała 766 MiB użycia i 1% obciążenia.
  Bez restartu lub modyfikacji sterownika.

## 2026-09-20 — drugi trening QLoRA i niezależna ocena nowych recenzji

- Kontynuacja aktywnego celu, poprzedni etap dostarczył3 odebrane recenzje.
  Protokół002:14 historycznych+3 nowe=17, hash wspólny
  917a7ce3436cf054aad2c9a73f915b93fb606fe31b38d335438641e801dadccb.
  Sprawdzane hashe wszystkich prywatnych odpowiedzi/wejść i ocen; dokładna
  zgodność rekordów z modelowym autorstwem. Bez publicznego zapisu rawdanych.
- Zarezerwowano reviewer-suite-001 przed treningiem:3 inne rodziny artykułów
  z niezależnymi rubrykami, checksum i zakazem importu do train/validation.
  Sam generator nie widzi rubryk. Syntetyczne liczby/artefakty, bez klienta.
- CPU audit:17/17, maksimum2992tokeny; prompty egzaminu1189/1194/1151
  plus1700 odpowiedzi mieszczą się w4096. Protokół001 pozostał bez zmian.
  Nowy runner wykorzystuje istniejący trainer z opcjonalnym osobnym pomiarem
  usługi; świeży adapter z bazy, r8/alpha16, batch1/akumulacja2,18kroków,lr5e-5.
- Preflight reviewer-sft-3q8l0dpn:ComfyUI nie słucha,Docker pusty,GPUfree31208MiB,
  dostępneRAM23 743 463 424B. Brak obcych procesów zatrzymanych lub zmian usług.
  Run ukończony:18kroków/2epoki,55.7758s treningu,488.719s całości,
  loss0.695493,peak allocated23 528 112 128B, maski rzeczywistego treneraOK,
  LoRA_B zmienione. Adapter safetensors zweryfikowany z dysku:
  38a7d1da6fe6ae365eec71a1ed3f6a5a0e2aa34d845b9d742d6694fd039505a3.
- Ta sama baza HFbnb4/runtime/tokenizer/greedy przed i po. Role11/12 →11/12,
  ten sam błąd. Recenzje sześć pełnych generacjiEOS. Etykiety faz ukryto do
  zapisania judgments; wcześniej widoczne długości ograniczają zaślepienie.
- Ocena treści:serving3→5,extraction3→2,release5→2, suma11/15→9/15.
  Format rawJSON0/3→1/3; pięć odpowiedzi ma Markdown fences. Pełny kontrakt
  0/3→0/3. Nie usuwano fences dla zaliczenia; zakres to HFbez gramatykiAPI,
  nie pomiar transportu Ollama. Nauczycielska ocena małej próby, nie wniosek
  statystyczny. Nieprecyzyjna kontrola niezależności ewaluatora w jednym
  artykule odnotowana; wynik nie opiera się wyłącznie na tej kontroli.
- Surowe wyniki/raport zachowane; osobny exam-assessment-8n2rlwpg zawiera
  kryteria, anonimowe próbki, uwagi, mapowanie i porównanie powiązane hashami.
  Odrzucono promocję adaptera: brak spójnej poprawy. Egzamin pozostaje poza
  treningiem. Oryginalne wagi, wcześniejszy adapter i routing bez zmian.
- Testy wstępne57passed/1.30s; regresja107passed/2.27s; dodatkowy test
  wykrywania podmiany mapowania faz passed/0.04s. Końcowy proces zakończony,
  GPUused769MiB. Bez nowych zależności, pulpitów, Windows, klientowskich zadań
  lub deklaracji ukończenia całego celu. Szczegóły w TRAINING_OBJECTIVE.md.

## 2026-09-20 — sześć lekcji recenzenta i trzy odebrane rekordy

- Kontynuacja aktywnego celu jakości pięciu usług. Dodano sześć syntetycznych
  rodzin train z kartami faktów/liczb i niezależną rubryką; wykonania są
  wyłącznie modelowe. Bez nowych artykułów klienta, UI lub produkcyjnych zadań.
- Uogólniono karty źródeł recenzenta; hash i własny pakiet zachowany w poprawce
  i Markdown. Błędny cytat może naprawić model bez zaakceptowania oryginału.
  Szkoła ma sześć sekwencyjnych prób, preflight każdej i blokadę własnego runu.
- school-ewpkqc09: 6 odpowiedzi, 4 strukturalnie poprawne, 2 złe kotwice;
  wszystkie wymagały uwag. school-88i1jaje: 6 poprawek, jedna identyczna
  z poprzednią; odebrano koszty. Pierwsze wywołanie poprawki odrzucone przed
  inferencją przez klucze int/string w JSON rubryki; poprawiono/testowano.
- school-ni42dxxi: 5 nowych rekonstrukcji z uwag bez poprzedniej recenzji
  oraz ze wzmocnionymi wskazówkami o dowodach. Odebrano pamięć i porównanie
  platform. Zmiana promptu, nie eksperyment izolujący jedną przyczynę poprawy.
  Razem 17 odpowiedzi, 228.750 s, bazowy Qwen Ollama bez nowego adaptera.
- Wszystkie odpowiedzi/uwagi/oceny i hashe prywatne; nie zmieniono surowych
  tekstów modelu. curated-rk_wk_sw zawiera trzy approved records, SHA256
  ca5642594716d22b8aaf558e6274d199088de892e33df0dd2b55b59f078a036d.
  Odebrane dla nauki syntetycznej, nie klienta. Pozostałe odrzucone z opisem
  błędów, w tym nieudowodnionych przyczyn błędów danych i gwarancji RAG.
- CPU tokenizacja 3/3, bez ucinania; długości2992/2427/2274, completion
  747/920/908. Potrzebują kontekstu co najmniej4096; historyczny eksperyment
  2048 pozostaje zamrożony. Bez nowego treningu wag na tej partii ani promocji.
- Jedno wywołanie pytest wskazało złą nazwę pliku i wykonało zero testów.
  Po korekcie 62 passed/20.98 s: źródła, kotwice, metadane poprawek, niezmienne
  autorstwo, dane i maskowanie. Bramka200/25/50 nadal niezaliczona. Szczegóły
  i ograniczenia odbioru w TECHNICAL_REVIEW_PILOT.md oraz TRAINING_OBJECTIVE.md.

## 2026-09-20 — pierwszy trening specjalizacyjny na odebranych danych

- Właściciel jawnie polecił kontynuować trening do jakości porównywalnej
  z asystentem. Utworzono aktywny cel, bez deklaracji jego osiągnięcia.
  TRAINING_OBJECTIVE.md definiuje zakres pięciu usług i ograniczenia oceny.
- Zamrożono osobny protokół badawczy qwen-sft-pilot-001.json: 14 wcześniej
  zatwierdzonych rekordów, hashe trzech partii i dowodów odbioru; nie zmieniono
  istniejącego walidatora/eksportera ani bramki 200/25/50. 14/14 mieści się
  w 2048 tokenach bez ucinania, z jawną maską promptu i EOS odpowiedzi.
- Nowy train_qwen_pilot.py używa przypiętej bazy HF bnb4, osobnego venv,
  QLoRA r8/alpha16, batch1/akumulacja2, 14 kroków i lr5e-5, seed3407.
  Generuje punkt odniesienia bez adaptera i wynik z adapterem w tym samym
  runtime. Zestaw ról jest regresją publiczną, nie prywatnym holdoutem usług.
  Żadnego wykonywania kodu przykładów na hoście, zmiany oryginalnych wag
  czy automatycznej promocji. Oddzielny katalog i zapis safetensors.
- Preflight: ComfyUI nie słucha, Docker pusty, GPU wolne 31305 MiB.
  RAM dostępny około20 GiB, miejsce dyskowe około240 GiB. Nie zatrzymano
  żadnego obcego procesu ani usługi; nie instalowano nowych zależności.
- Pierwszy start odrzucony przy imporcie: środowisko ML nie ma SQLAlchemy.
  Wyodrębniono role_evaluation_contract.py bez zależności aplikacji; zachowano
  kompatybilny import starego evaluatora. Preflight aplikacji w osobnym venv.
- reviewed-sft-wuihjzum i reviewed-sft-3hd8fo2h: błąd Unsloth generate,
  architectures=None po text_only. Uzupełniono metadata z faktycznej klasy
  Qwen3_5ForCausalLM wyłącznie w RAM, bez edycji checkpointu lub bibliotek.
- reviewed-sft-jh44a7a1: baza 11/12; audyt masek odrzucił collator po tym,
  jak konstruktor UnslothSFTTrainer przywrócił tryb inference/left padding.
  Nie wykonano kroku treningu. Dodano jawne for_training/right padding po
  konstruktorze. Niezależny CPU audit collatora potwierdził maski 14/14.
- reviewed-sft-bsoy9jvr: **ukończony**, 14 kroków/2 epoki; potwierdzona
  zmiana parametru LoRA_B, 39 845 888 trainable, skończony loss0.7963818,
  49.273 s treningu, 183.183 s całości, peak allocated22 904 749 568 B.
  Adapter zapisany w adapter-RESEARCH-NOT-FOR-PRODUCTION; pełne hashe
  w raporcie. Porównanie **11/12 → 11/12**, brak poprawy i brak regresji
  decyzji; nie jest to pomiar wszystkich kompetencji ani jakość uzasadnień.
- Użyto dokumentacji pierwotnej TRL0.24, PEFT quantization i Unsloth oraz
  kodu przypiętych lokalnych bibliotek. Raporty nieudane zachowane. Publiczne
  źródła/dokumentacja/testy oddzielone od prywatnych wag i raportów.
- Testy nowych bramek/masek/danych: 50 passed/1.09 s; po wyodrębnieniu
  kontraktu ról 27 passed/0.57 s. Oryginalne suite/hash ocen bez zmian.
  Końcowa regresja masek, danych, ról i porównywarki: 84 passed/1.75 s.
  Nie uznano celu za osiągnięty i nie podmieniono modelu produkcyjnego.

## 2026-09-20 — funkcje modeli i cele nauki z ogłoszeń Upwork

- Właściciel odłożył wygląd/menu i polecił rozwijać funkcje oraz uczyć modele.
  Następnie dostarczył pięć typów zleceń: recenzje fine-tuningu, fotografie
  wnętrz/organizacja treści, ulotka PDF/wektor, cztery infografiki produktu
  i identyfikacja restauracji. Zapisano własne streszczenia wymagań i kryteria
  w upwork-learning-targets.json, bez kopiowania ogłoszeń i udawania zamówień.
- Nowa szkoła funkcji: trzy kontrakty i 23 niezależne testy powstały przed
  generacją. Całe rozwiązania są niezmienionymi odpowiedziami Qwena. Kontenery
  nonroot/readonly/network-none, przypięty runner, weryfikacja sprzątania;
  żaden modelowy Python nie jest importowany/wykonywany na hoście.
- Domyślnie do dwóch prób, błąd testu wraca do modelu, awaria infrastruktury
  zatrzymuje kurs. Blokada równoległego kursu, kontrola zasobów przed każdą
  generacją/testem, budżet między próbami i osobne timeouty operacji.
  Dokładne prompty, odpowiedzi i dowody zachowane; kolektor nie zatwierdza
  danych ani nie uruchamia treningu. Lekcja tylko po błędzie naprawionym
  i zaliczonym, bez fikcyjnego postępu przy sukcesie za pierwszym razem.
- Pierwszy start course-zeu9wbhm zatrzymał sandbox na preflight, bez inferencji.
  Ponowiono z formalnym dostępem do lokalnego modelu/Dockera. course-ksxznylh:
  3/3 pierwsze próby, 23/23 testy, 18.257 s, cleanup potwierdzony. Przejrzano
  dokładne źródła; bez ręcznych poprawek. Trzy kandydaty pending, prywatność
  nie jest autozatwierdzana. Offline tokenizacja 3/3 przy 4096: 885/706/646
  tokenów, completion-only mask, brak ucinania. Bramka 200/25/50 pozostaje.
- Testy szkoły i danych początkowo 42 passed/2 skipped (inne urządzenie /tmp).
  Powtórzono na prywatnym katalogu /home: 44 passed/15.75 s, bez pominięć.
  Naprawiono przekazanie listy zamiast bytes do walidatora datasetu przed
  realnym zbieraniem. Nie zaniżano bramek ani liczby wymaganych testów.
- Pilot recenzenta: model pisze komentarze, poprawki, potrzeby dowodowe,
  przykłady i rekomendację; Markdown jest mechaniczną serializacją.
  Nauczyciel przygotował 14-liniowy tekst z 11 celowo błędnymi fragmentami,
  dwoma kontrolami poprawnych zdań i instrukcją do zignorowania wewnątrz
  artykułu. Cztery karty źródeł z przeczytanych publikacji LoRA/QLoRA/RAG
  oraz dokumentacji scikit-learn. Klucz oceny nie trafia do modelu.
- review-g7zj1qez: 11/11 pokrytych wadliwych linii, ale ocena merytoryczna
  wymaga poprawek. review-hxey5shl: JSON zapisany inaczej, semantycznie
  identyczny wynik. Dodano detekcję unchanged_revision i jednoznaczny tryb
  poprawy. review-tdto7ei1: model sam uszczegółowił szereg zaleceń;
  niezależny independent-assessment.json nadal needs_more_learning ze względu
  na słabą listę dowodów i pozostałe uproszczenia. Żadnego wyniku asystent
  nie przepisywał; brak eksportu SFT, treningu wag, publikacji lub odbioru klienta.
- Bieżące testy mechanizmów + danych: 57 passed/19.48 s przed końcową
  detekcją powtórzonej recenzji; końcowy zestaw recenzenta 13 passed/4.67 s.
  Dokumentacja FUNCTION_SCHOOL.md i TECHNICAL_REVIEW_PILOT.md. Brak zmian
  menu/układu, restartów panelu, statusów rzeczywistych zadań, obcych procesów
  i dysku Windows. Materiały i raporty pozostają na prywatnym dysku Linux.

## 2026-09-20 — wejście do lokalnego panelu bez tokena

- Właściciel wskazał, że panel nie pokazuje ostatnich prac nad szkołą modeli
  i nie powinien pytać o token na jego komputerze. Wyjaśniono, że szkoła
  nadal działa poza panelem; ten etap dotyczy automatycznego dostępu.
- Dodano jawnie włączany LOCAL_OWNER_ACCESS i POST /api/owner-session/local.
  Weryfikacja rzeczywistego peer/server loopback, Host/port i pochodzenia,
  odrzucanie nagłówków proxy. Zwykłe cookie HttpOnly/SameSite + CSRF,
  ponowna kontrola lokalności dla sesji, bez obejścia ról i złych Bearerów.
  Endpoint nie jest dostępny w aplikacji klienta. Tryb zaufanego komputera
  nie odróżnia jego lokalnych kont/procesów — odpowiada zakresowi żądania.
- Panel sam zakłada sesję i wyświetla „Właściciel · ten komputer”. Ukrywa
  formularze tokena i przyciski logowania/wylogowania w tym trybie, również
  po asynchronicznym wczytaniu panelu. Wersje URL JS/CSS zaktualizowane,
  aby odświeżenie strony pobrało aktualne pliki. Tryb tokenowy zachowany.
- 42 passed/1.21 s: dotychczasowe sesje i RBAC oraz nowe przypadki lokalne,
  zdalny peer, spoof Host/port/proxy, obce Origin, brak CSRF, cookie z innego
  połączenia, wyłączenie trybu, wygaśnięcie i odnowienie, separacja klienta.
  node --check owner-session.js zaliczony.
- Rzeczywisty Chrome headless (własny profil, bez GPU, dźwięku i sesji pulpitu):
  /os, /os/work, /os/build, /os/clients, /os/review, /os/publishing, /os/media,
  /os/upwork — wszystkie automatycznie dostępne, bez widocznych pól hasła.
  Potwierdzono nową wizytę bez cookie, HttpOnly i chroniony odczyt opcji
  zlecenia. Bez zmian zadań, wywołań modeli czy odczytu tokena przez test.
- LOCAL_OWNER_ACCESS=1 zapisane wyłącznie w prywatnym .env, tokeny nietknięte.
  Własny serwer panelu z poprzedniego kroku uruchomiono ponownie na
  127.0.0.1:8000, z --no-proxy-headers. Przed pierwszym startem wykonano
  kopię bazy w ai-company-workspaces/panel-start-mwawsgj5/before-start.sqlite.
  Nie rozszerzono dostępu na LAN; szkoła modeli nie została tu podłączona
  do interfejsu. Dokumentacja: organization-os/OWNER_SESSION.md.

## 2026-09-20 — system uczy i ocenia; realizacje pisze lokalny model

- Właściciel wskazał, że trzy demonstracje nie sprawdzały zamierzonej
  samodzielności systemu. Do ukończenia projektu zabronił asystentowi pisania
  realizacji i poprawek za modele; tokeny mają służyć rozbudowie systemu.
  Udzielił stałej zgody na kontynuację. Zapisano w AGENTS.md bez zmiany
  ograniczeń cudzych procesów, pulpitu i danych prywatnych.
- Dodano scripts/web_school: pełne HTML/CSS/JS od przypiętego lokalnego
  Qwena, niezależny egzamin w oddzielnym headless Chrome, ograniczone próby,
  diagnoza błędów przez model i naprawy przez model. Bez szablonów poprzednich
  demonstracji i bez edycji źródeł produktu przez asystenta. Kontrole zasobów
  przed każdym wywołaniem; brak aktualizacji bazowych wag, produkcyjnej DB,
  konfiguracji modelu, Windows, sterowników, wynajmu lub sesji graficznej.
- Pamięć zawiera fakty z niezaliczonych, a potem zaliczonych kontroli.
  Wczytanie weryfikuje źródła, wyniki i wersję egzaminatora; błędy struktury
  są ponownie odtwarzane walidatorem na oryginalnych odpowiedziach. Powstało
  też automatyczne zbieranie dokładnych odpowiedzi jako SFT/pending, bez
  zatwierdzania lub ucinania. Recheck tworzy nowe dowody bez inferencji;
  revise-from przekazuje istniejące źródła i błędy do dalszej pracy modelu.
- Rzeczywiste przebiegi poza Git w ai-company-workspaces/web-school:
  stamps-hf7z5tdu — pierwsza próba 9/31, naprawa przerwana przez limit 4096
  tokenów (truncated_output). Transport nie zwraca częściowego tekstu;
  zachowano błąd i wszystkie wcześniejsze pełne odpowiedzi. Limit podniesiono
  do 6000, polecono zwięzłe pliki i ograniczono zbędny kontekst CSS dla JS.
- Błędy nauczyciela ujawnione i zachowane: automatyczny favicon liczony jako
  błąd produktu; test SELECT wysyłał tylko change, choć poprawny interfejs może
  obsługiwać input; walidator przepuszczał HTML w pliku CSS i powtórzone ID.
  Dodano właściwe zdarzenia input+change, rozdzielono favicon oraz typy i ID.
  Nowy test ochronny najpierw 1 failed/14 passed, po poprawce zaliczony.
  stamps-gi94wvf3: trzy próby, ostatnia 20/30 według ówczesnego wadliwego
  testu zdarzeń. Nie przedstawiamy tego jako wiarygodnego wyniku ucznia.
- stamps-l7uxchl3: model poprawił powtórzony ID po raporcie walidatora,
  druga próba 30/30. Trzy rekordy SFT/pending, bez wzrostu approved_counts.
  Przejrzano źródła i desktop: poprawna podstawowa demonstracja, powtarzalne
  grafiki i nierówne położenie cen/przycisków; nie odebrano jakości premium.
  Automatycznie rozpoczęto zmieniony wariant stamps-cwero7zr, lecz sprzątanie
  profilu Chrome przerwało zapis oceny (Directory not empty: Default).
- Poprawiono zamykanie własnej grupy procesów headless, oczekiwanie na koniec
  i raportowanie usunięcia profilu. Recheck-6hk0vsge potwierdził 30/30 dla
  dokładnie tych samych źródeł, bez nowej inferencji; profil usunięty.
- stamps-rrpz38fj rzeczywiście otrzymał zapisaną lekcję o ID/typach plików.
  Brak błędu statycznego; 25/30, potem 27/30. Model poprawił przepełnienie
  na 320/390 px, pozostały checkout i menu. Dodano obserwacje tagName,
  disabled i klas/display do raportu, bez osłabiania kryteriów. Recheck-bsqdo07b
  zachował wyniki obu prób na aktualnym egzaminatorze, bez zmiany źródeł.
- Kontynuacja stamps-b98colfg: model naprawił menu, lecz naprzemiennie
  powielał ID checkout i przypisywał go sekcji zamiast przyciskowi; 28/30.
  Rozpoznano problem procesu: błąd statyczny usuwał wcześniejszy raport
  funkcjonalny z kontekstu. Teraz zachowuje się oba; przed naprawą lokalny
  model sporządza osobną diagnozę. Żadnej poprawki strony nie napisał asystent.
- Testy mechanizmu oraz dotychczasowego formatu danych: 47 passed/15.68 s.
  W pierwszym uruchomieniu jeden test pominięty przez różne urządzenia /tmp
  i /home; przeniesiono tymczasowy katalog testu na Linux /home i wykonano
  wszystkie testy. Brak automatycznego treningu wag lub promocji adaptera.
  Ćwiczenia są z jednej rodziny train/development, nie holdoutem.
  Opis funkcji: organization-os/LOCAL_WEB_SCHOOL.md.
- Końcowa kontynuacja stamps-4yc77u4i: diagnoza Qwena 8.036 s/272 tokeny
  poprawnie wskazała konflikt selektora sekcji i przycisku. Następnie model
  zmienił komplet plików; 30/30 w pierwszej próbie, bez wyjątków JS i obcych
  żądań, profil usunięty. Egzaminator SHA-256
  e72522ed7ad59a11651657c0aecebcb650baadba6436c3f1e8c3fc9780b645bf.
  Sprawdzono także screenshot mobile; nie nadano odbioru estetycznego premium.
  Łącznie sześć nowych kandydatów SFT/pending z dwóch zaliczonych wersji;
  pozostałe wersje i recheck nie są liczone jako dodatkowe przykłady.
- Offline audyt przypiętego tokenizera: 6/6, 6525–10367 tokenów rekordu,
  kontekst 16384, prawidłowa maska odpowiedzi/EOS, bez ucinania i bez wag.
  Zbiorczy hash partii 52a815981baac582ae76b624045c3ffc6277451d69821b70da17a91974ef64ca.
  Pending pozostaje pending; export_ready i training_ready false, bez treningu.

## 2026-09-20 — trzy nowe strony według briefów właściciela

- Właściciel zlecił katalog sprzedaży znaczków, portfolio trance z własnym
  logo/audio i filmem na scroll oraz kasyno z 3 grami bez realnych pieniędzy.
  Powstał osobny katalog three-sites-ufpa30po, bez ingerencji w starsze FORMA.
- Preflight: Docker pusty, RTX5090 1053 MiB/12%. Windows już zamontowany
  read-only na /media/marcin/Windows. Nowy brief upoważnia do odczytu logo;
  wyszukano związane materiały. Logo z grafiki profilu w folderze kanału,
  okładka i 3 MP3 skopiowane dokładnie na Linux. Oryginały nietknięte.
- Lokalny Qwen kolejno: katalog/logika 12.503 s/1582 tokeny, portfolio/logika
  10.523 s/1127 tokenów, gry/logika 9.501 s/1117 tokenów. Zachowano prompt,
  digest i oryginalne odpowiedzi. Kod modelu nie wykonywany na hoście.
  Logika zaliczona bez modyfikacji; polski brief projektu znaczków dostał
  angielską koncepcję. Termin „Świeży” poprawiono w roboczym katalogu.
- Asystent wykonał trzy różne interfejsy, stan koszyka/portfela/odtwarzacza,
  wektorowe ilustracje znaczków i proceduralny film H.264 1280×720/24 fps/
  10 s. Nie przedstawiamy tego jako wideo z sieci generatywnej ani jako
  stron wykonanych w pełni samodzielnie przez Qwena. Brak nowego treningu.
- Pierwszy Chrome browser-qrssf8au: 48 kontroli, 7 failed. Brak logo przed
  identyfikacją, 2 szerokości przy 320 px, 4 reduced motion (emulacja tylko
  procesu rodzica zamiast również ramki). Poprawiono faktyczne siatki,
  zidentyfikowano logo i poprawiono zakres emulacji. browser-mgjo51hj 48/48.
- Po korekcie symboli (tekstowe strzałki zamiast kolorowych emoji w Linuksie)
  i dołożeniu sandbox do nagłówka stron, browser-5oeqq9_y: 48/48, brak
  wyjątków JS. 224 niezależne przypadki obliczeń gier oraz realne interakcje.
  Naturalny wheel przewija rzeczywiste wideo w obie strony, audio odtwarza,
  pauzuje i zmienia pozycję/utwór, ukrycie karty pauzuje. Zero wywołań focus
  w badanej opóźnionej pracy. Sprawdzono desktop/390/768/320 i reduced motion.
- Transport/paczki: 15 passed/0.79 s. Range, HEAD, Host, CSP, prywatne trasy,
  dokładne bytes oraz deterministyczne ZIP-y. Wcześniejsze zamykanie Chrome
  wywołało ConnectionResetError w HTTP keepalive; odpowiedzi zamykane jawnie.
  Nie było modyfikacji danych projektu ani awarii aplikacji z tego powodu.
- Gotowe ZIP-y: 143211, 48008329 i 30406 bytes; hashe i dowody w
  organization-os/THREE_WEB_TRIALS.md. Serwer LAN 10.0.0.57:33117 na 240 min;
  /stamps, /music, /casino, wspólna nawigacja i pobieranie każdej paczki.
  Odczyt LAN potwierdził trzy zgodne ZIP-y i Range filmu oraz odmowę obcego
  Host/prywatnych raportów. Zamykano wyłącznie własne tymczasowe serwery.
- Wszystkie materiały właściciela i surowe raporty poza Git. Brak zmian
  prawdziwych zadań/DB, zamówień, płatności, publicznego hostingu, Windows,
  sieci, Vast.ai, GPU sterowników, cudzych usług i pulpitu. Statyczny pilot
  browserowy nie rozszerza profilu produkcyjnego Python+PNG o multimedia.
  Odbiór wizualny właściciela pozostaje otwarty.

## 2026-09-20 — źródła i PNG w zadaniu, testach, odbiorze i wydaniu

- Po wznowieniu zakończono zapis poprawki pierwszego przewijania: commit
  0bac9b4 i push na dotychczasową gałąź po czystych skanach staged/historii.
  Następnie wykonano zapowiedzianą integrację pełnej paczki z procesem firmy.
- Osobny schemat mediów i profil wykonania; tekstowe limity pozostają stare.
  Import owner-only purpose/files/images, canonical base64, realny PNG/CRC,
  limity ścieżek, ilości, rozmiarów i wymiarów. Hash PNG z decoded bytes,
  checksum całej wersji obejmuje źródła i obrazy. Powtórka identycznego importu
  pod transakcją zwraca tę samą paczkę. Stary tekstowy schemat nie może
  aktywować profilu binarnego przez samą nazwę pliku .png.
- Przypięty tester mediów wykorzystuje istniejący Docker bez rozszerzania
  sieci, RAM/CPU/PID, dostępu do GPU/hosta czy limitu logów. Sprawdza izolację,
  testy paczki, dokładne bytes/MIME wszystkich publicznych plików i prywatne
  trasy. Błąd obrazów blokuje passed; niepewne cleanup blokuje slot.
- Pilot media-package-pilot-rv0rwxdu: 9 wykonań passed (testy + 8 prób HTTP),
  ten sam dokładny FORMA ZIP 957bd21a6c3e61ed5ec77638d4d19c506a2b7d3aa2c488db2b34214bc6890c05.
  Import dodaje do przykładu niezmienione niezależne testy kalkulatora.
  Dopiero po zaliczeniu przypięto SHA testera w profilu dostępnym przez API.
- Syntetyczny obieg API z rzeczywistym kontenerem: 1 passed/1.75 s, wydanie
  przed odbiorem odmówione, po testowym odbiorze ZIP z identycznymi PNG,
  instrukcje, root preview i kalkulator 2125. Postęp zadania pozostał 0.
  Test błędnego MIME w rzeczywistym kontenerze blokuje kandydata, mimo
  działającej logiki. Razem z 6 wariantami unieważnienia: 7 passed/1.18 s.
- Podgląd owner API przekazuje PNG do opaque CSP iframe, który osadza
  względne img/src; brak pozycji inventory blokuje otwarcie. Bez CSS url(),
  srcset i dowolnego pobierania obrazów. Chrome: 1 passed/3.19 s; 3 PNG mają
  właściwe data URI i realne wymiary, desktopowa scena się inicjalizuje,
  3 wyniki kalkulatora i walidacja błędnego wejścia zaliczone.
- Dwie pierwsze próby browser test niezaliczone: odpowiedź diagnostyczna
  z całymi data URI przekroczyła limit WebSocket 1 MiB (1.32 s), potem
  domyślny mały viewport poprawnie użył mobilnego fallback zamiast sceny
  desktopowej (1.32 s). Test teraz zwraca tylko metadane/boolean i jawnie
  ustawia 1440×1000. Nie osłabiono limitów transportu ani zachowania strony.
- /os/build ma import kompletnego JSON, wybór zapisanej paczki i istniejący
  odbiór/wycofanie/gotowość/wydanie. Wylogowanie podczas czytania pliku
  unieważnia wysyłkę. PNG nie trafia do edytora tekstowego ani diffu base64.
  Centrum realizacji rozpoznaje nowy artefakt i kieruje do testów/podglądu.
  Eksport Linux zapisuje decoded PNG, kontroluje hash i nie nadpisuje zmian.
- Regresja Python: 162 passed/5 skipped/8.39 s. Późniejsza kontrola eksportu
  i mediów: 38 passed/3 skipped/1.89 s. Node uruchomione bezpośrednio:
  19 passed (import3, frame4, broker5, panel7); dodatkowy zbiorczy przebieg
  objął również odbiór i instrukcje. Składnia JS i diff --check czyste.
  Jedna próba pytest bez eskalacji utknęła w sandboxie przy lokalnym API;
  przerwano wyłącznie własny PID 63752 (SIGINT nieskuteczny, SIGTERM zakończył).
  Powtórkę wykonano z zatwierdzonym dostępem, na tymczasowych bazach.
- Lokalny Qwen: ograniczony przegląd media-delivery-review, 4.581 s/160
  tokenów. Zasugerował logout/read race, decoded hashes, MIME i stare dowody;
  sprawdzono je niezależnie. Uwaga o CSP nie jest dowodem pełnego audytu.
  Raport skopiowany do prywatnego katalogu pilota jako qwen-review.json.
- Nie importowano do prawdziwych zadań, nie odebrano faktycznej pracy za
  właściciela, nie wysłano klientowi ani nie wdrożono strony. Dane przykładów
  i raporty pozostają poza publicznym Git. Bez treningu, generacji grafiki,
  pulpitu, Windows, usług Vast.ai, obcych procesów i zmian konfiguracji hosta.
  Dalsze ograniczenia i polecenia: organization-os/MEDIA_PACKAGES.md.

## 2026-09-20 — zdjęcia nie reagowały na pierwsze przewijanie

- Właściciel doprecyzował, że pogorszyło się przełączanie zdjęć FORMA.
  Porównanie paczki z nakładką potwierdziło tę samą grafikę i skrypty;
  historia wskazała warunek hasFocus dodany przy ochronie pulpitu.
- Odtworzono wejście bez kliknięcia i bez narzędziowego focus ramki. Dokument
  przewinął się o 1739 px, ale nie ustawił scenePosition, a wszystkie zdjęcia
  miały identyczną macierz. Test przed poprawką: 1 failed/1.80 s. Sprzątanie
  prywatnego Chrome zgłosiło też znany wyścig Directory not empty; nie usuwano
  profilu ani aplikacji użytkownika. Dotychczasowy test maskował problem,
  bo jawnie nadawał focus ramce przed kontrolami.
- Przywrócono warunek widoczności dla renderowania sceny i paralaksy.
  Nie zmieniono helisy, geometrii, sprężyn ani przejść modalu. Nawigacja,
  przywracanie fokusu i zamykanie w tle zachowują dotychczasowe zabezpieczenia.
  Nie dodano automatycznego focus. Ukryta karta nie renderuje, blur zatrzymuje
  bieżący ruch; naturalne przewijanie widocznej ramki może go wznowić.
- Test roboczych plików: 1 passed/2.74 s. Następnie nowy kompletny ZIP
  studio-bundle-9spiyivv (1 288 665 bytes), SHA256
  957bd21a6c3e61ed5ec77638d4d19c506a2b7d3aa2c488db2b34214bc6890c05.
  Kontener zaliczony. Pełny audit studio-browser-960q0m3e + nowy test samego
  ZIP: 2 passed/30.23 s. Fokus nadal false, zero focus(), pozycja sceny
  0.5002, trzy różne macierze, wheel wstecz i blokada ukrytej karty zaliczone.
- Regresja Python: 54 passed/1 skipped/1.13 s. Node: 3 testy fokusu i 8
  geometrii/ruchu zaliczone. Składnia obu JS i diff --check bez błędów.
- Dodano opcjonalny port podglądu (0 lub 1024–65535), żeby nie mnożyć URL-i.
  Zamknięto wyłącznie własny poprzedni preview PID 16183 przez SIGINT i
  zastąpiono nową paczką pod tym samym LAN URL. Serwer potwierdził nowy hash.
  Bieżące stare karty wymagają odświeżenia. Stary ZIP zachowano jako dowód.
  Kontrola nowego serwera pod dotychczasowym adresem: 31 passed/1.10 s.
  Właściciel chwilowo wstrzymał pracę, następnie jawnie zezwolił ją wznowić.
- Bez modeli, generacji obrazów, zmian DB/statusów, pulpitu, Windows,
  sterowników, sieci, usług Vast.ai ani obcych procesów. To naprawa konkretnej
  odtworzonej regresji; ocena wizualna właściciela pozostaje do potwierdzenia.

## 2026-09-20 — wznowienie, kompletna paczka FORMA i podgląd telefonu

- Właściciel potwierdził po restarcie normalną pracę myszy i okien, polecił
  kontynuować budowę. Bez diagnozowania przyczyny na podstawie poprawy.
  Repo czyste, Docker pusty, GPU 737 MiB / 1% przy wstępnej kontroli.
- Qwen skonsultował ograniczony plan pakowania: 11.199 s / 131 tokenów,
  draft qwen-runner-draft-ff4661ap. Wskazał integralność PNG, ZIP/traversal,
  izolację CSP i limity pamięci. Wynik przejrzany, nie wykonano kodu modelu.
  Nie było treningu, generacji nowych obrazów ani delegacji do innych modeli.
- Dodano assembler, manifest i niekompresowany ZIP: aplikacja, oryginalna
  logika, nadzorowany serwer publicznych tras, 3 PNG, wszystkie interakcje.
  20 plików / 1 288 519 bytes. Stare źródła/raporty/ZIP-y bez zmian.
  Odczyt tylko do pamięci z dokładnym inventory, limitami, hashami, bez
  dowiązań/duplikatów/ekstrakcji. Nie rozszerzono profili i limitów API.
- Nowy runner pilota zachowuje istniejącą izolację Docker. Wykonuje dokładne
  bytes odczytane z ZIP, testy modelu i niezależne asercje, kontrolę każdego
  publicznego zasobu (hash/MIME), API i prywatnych tras. Ramka dostaje zasoby
  archiwum, obrazy jako data URI; backend także pochodzi z tej paczki.
- Pierwsza próba studio-bundle-ov04aujc odmówiona przed wykonaniem przez
  sandbox (PermissionError lokalnego socketu podczas preflight). Ponowienie
  z zatwierdzonym dostępem: studio-bundle-txnwfeuv zaliczony. ZIP SHA-256
  f0c898b0e36c609b85d31a75b93291a63ec08a51c5ec966b1b7fdb06a5f4ee73.
- Chrome audit studio-browser-nrku0sg5: 1 passed / 30.52 s, 112 kontroli,
  exact ZIP + prawdziwy kalkulator w kontenerze, granice fokusu i wcześniejsze
  przepływy galerii/sceny/menu. Obejrzano screenshot menu 320 px. Headless
  bez dostępu do X11/Wayland/sesyjnego D-Bus i bez GPU. Fizycznego iPhone
  nie testowano. Wynik nie oznacza przyznania odbioru ani zmiany statusów.
- Wcześniejszą prośbę o telefon zrealizowano osobnym preview z `--bind` na
  jawnym prywatnym LAN IPv4. Loopback pozostaje domyślny. Brak wildcard,
  publicznych adresów i VPN. Host/Origin/CSRF i trasy ograniczone; 60 obliczeń,
  120 minut. Bez panelu, bazy, tokenów właściciela i konfiguracji sieci.
- Testy: baseline 45 passed/1 skipped; pakowanie + regresja 63 passed/2 skipped
  (ostrzeżenie świadomie zduplikowanego ZIP ograniczono w samym teście).
  Jedna komenda regresji wskazała nieistniejący test_multifile_staging.py
  i nie uruchomiła testów; poprawiony zestaw: 96 passed/1 skipped/2.00 s.
  Kontrola działającego LAN i polityki adresów: 28 passed/1.04 s. Node:
  3 testy fokusu + 8 testów ruchu/kontraktu zaliczone.
  Po dodaniu odmowy niekompletnego raportu kontenera: 15 testów pakowania
  passed/0.36 s. Kompilacja zmienionego Pythona i diff --check zaliczone;
  przegląd staged obejmuje tylko zamierzony zakres, Gitleaks bez sekretów.
- Artefakty, dokumentacja i ograniczenia: STUDIO_BUNDLE.md. Nowy kandydat
  nie jest jeszcze częścią produkcyjnego procesu dostaw. Brak publikacji
  strony w internecie, kontaktu z klientami, zmian DB, usług Vast.ai, Windows
  i pulpitu. Zapis do istniejącego publicznego origin obejmuje wyłącznie kod,
  testy i dokumentację, bez lokalnych raportów, PNG czy danych konfiguracji.

## 2026-09-20 — przygotowanie restartu na polecenie właściciela

- Właściciel poprosił najpierw o przygotowanie, następnie jawnie o restart
  i kontynuację. Ochrona fokusu z 2eab5bd zapisana na origin; przyczyna myszy
  /KWin niepotwierdzona. Restart nie jest dowodem naprawy.
- SIGINT zamknął pięć własnych podglądów (901496, 910694, 918250, 942791,
  953644). `docker ps` pusty, brak wykrytych aktywnych testów i runnera modelu.
  Nie zatrzymano aplikacji użytkownika, usług Vast.ai ani obcych procesów.
- Zachowano lokalny draft Qwen z /tmp w katalogu restart-20260920-OaBWT3
  na Linuksie. Dodano docs/RESTART_CHECKPOINT.md z aktualnymi dowodami,
  ograniczeniami, sposobem ponownego startu i listą niezakończonych prac.
- Po zapisaniu/push checkpointu zaplanowane jest osobne polecenie restartu.
  Właściciel uprzedzony o zapisaniu dokumentów i możliwości konieczności
  ponownego otwarcia rozmowy. Nie skonfigurowano automatycznego agenta po boot.

## 2026-09-20 — FORMA: zabezpieczenie granicy przeglądarka/pulpit

- Właściciel zgłosił niemożność przełączania okien Linuksa, nie przeciążenie.
  W poprzedniej diagnostyce odczytano KWin XCB BadDamage; to wskazówka, nie
  rozpoznana przyczyna. Nie zmieniono KWin, sterowników, skrótów, sesji ani
  procesów właściciela. Wstrzymano modele i prace niezwiązane z problemem.
- Dodano wspólną kontrolę dokumentu aktywnego/widocznego oraz identyfikatory
  unieważniane przez blur. Focus/navigation w tle nie działają. Gallery close
  po utracie aktywności odkłada native close do powrotu strony, bez focus w tle.
  Menu odrzuca przeterminowane skoki. Animacje przerywane po blur, brak obsługi
  Alt/Ctrl/Meta/IME jako poleceń galerii. Nie deklarujemy naprawy OS bez obserwacji
  właściciela; to zabezpieczenie konkretnych ryzyk w naszym kodzie.
- Przeglądarka kontrolna ma jawny backend headless i środowisko bez DISPLAY,
  WAYLAND_DISPLAY/XAUTHORITY; adres sesyjnego D-Bus jest nieaktywny. Aktywowany
  jest wyłącznie offscreen target testu, nie okno OS. Pierwszy audit y_u9vmt2
  nie miał aktywnej ramki: 1 failed/5.88s (scena słusznie nie renderowała).
  Dodano aktywację ramki wewnątrz prywatnej przeglądarki headless.
- Audit cutmo6rd: 1 passed/26.47s, symulowane background close bez wywołań
  HTMLElement.focus, odmowa background navigation, bez konsumowania modyfikatorów,
  bezpieczne dokończenie close po powrocie. Dotychczasowe interakcje zaliczone.
  Nie wykonano automatycznego Alt+Tab w sesji właściciela.
  SHA256 raportu: 468937f368627b0bde49267383d8942aa71f0a2ef70666de8ee37d2f8cf16de1.
- Node: blokada hidden/nieaktywnego dokumentu, obcego elementu i starego ticketu,
  modyfikatory/IME oraz regresja sprężyn. Python początkowo 24 passed/1 skipped
  /0.51s. Brak inferencji, GPU generacji, treningu i nowych zależności.
  Końcowa regresja Python: 74 passed/1 skipped/1.46s; składnia JS/diff OK.
- Pytanie dodatkowe o iPhone: obecny podgląd jest loopback-only. Nie otwarto
  panelu właściciela/API do LAN; osobny telefoniczny podgląd wymaga następnego
  kroku po weryfikacji problemu pulpitu.

## 2026-09-20 — FORMA: połączenie sceny, nawigacji i zoomu

- Właściciel zgłosił, że funkcje działają naprzemiennie. Osobne historie
  rozdziałów i sekcji zastąpiono wspólną kolejnością powrotu. Kliknięcie tła
  i przyciski korzystają z koordynatora; gest przeciągnięcia i zaznaczenie
  nie cofają. Po resize scena ma statyczny punkt powrotu. Pauza nie blokuje
  jawnej nawigacji; animacja zamknięcia zdjęcia wraca do właściwego otwierającego.
- Zoom z kółka podczas otwierania/zmiany zdjęcia jest kolejkowany i czyszczony
  po zamknięciu. Bez nowych zależności, modeli, generacji grafik lub treningu.
- Lokalny Qwen skonsultował ryzyka/4 propozycje testów po check_idle:
  12.364s/206 tokenów wyjściowych; /tmp/qwen-runner-draft-pz_izj1k/draft.json,
  SHA256 199f7f1b694212a01c2657f46c9a1121c4cd079b96eaef6e6d014840ac3330fd.
  Wskazał kolejkę zoomu przy zamknięciu, przeplatanie historii, gesty i mobile.
  To konsultacja planu, nie przegląd pełnego kodu ani dowód testów. Kod i testy
  zintegrował główny agent. Nie wykonano kodu modelu na hoście.
- Audity mul5radf/16.90s, d8g05rvw/16.87s i 3dfhf2jn/16.88s wykryły utratę
  pierwszej delty kółka podczas kończenia smooth scroll. Samo anulowanie
  animacji nie wystarczyło. Pierwszą deltę przerwania aplikujemy jawnie;
  kolejne pozostają native. ltusxqr2: 1 passed/24.95s, przepływ połączony.
- Rozszerzono przypadki brzegowe według kolejnej uwagi właściciela. 6fcdk2oh:
  błąd inicjalizacji ramki/11.29s, bez wykonanych kontroli UI. Usunięto wyścig
  startu: src ramki ustawiany po listenerze, zarówno w helperze, jak i podglądzie.
- Regresja 74 passed/1 skipped/1.45s; Node geometria/sprężyny/kontrakt tła OK.
  Testy nadal używają syntetycznych danych, restricted Docker i prywatnego
  headless Chrome, bez zmian DB, usług Vast.ai, Windows czy obcych procesów.
- Końcowy audit mgchxyqt: 1 passed/25.95s. Wszystkie kontrole zaliczone,
  łącznie z przepływem mieszanym, kółkiem podczas lotu/zmiany, pauzą/nawigacją,
  zaznaczeniem/przeciąganiem, resize, szybkim podwójnym close i brakiem API
  animacji. SHA256 491cba4fa0d7c436176872df0decdcda708f52faf29acf14943c5ad3205a5427.
  Następny etap pozostaje oddzielny: składanie sprawdzonych źródeł, mediów
  i interakcji w jedną paczkę dostawy; obecny ZIP nadal zawiera aplikację bazową.
- Kontrola uruchomionego podglądu: 16 passed/0.79s, w tym start listenera przed
  src ramki, ograniczenia origin/CSRF/tras i rzeczywisty wynik syntetycznego API.

## 2026-09-20 — FORMA: brakujący powrót między sekcjami

- Właściciel nie widział powrotu po kliknięciu pustego miejsca. Poprzednio
  obsługiwano tylko modal i rozdziały sceny. Dodano lokalną historię przejść
  linkami/menu (max24), odtworzenie scroll/fokusu i widoczny pasek powrotu.
  Formularze/ustawienia zostają, bez historii parenta, storage czy reloadu.
- Tło menu również wewnątrz pustych odstępów zamyka menu; puste obszary
  toolbar/controls galerii zamykają podgląd. Kontrolki i zaznaczenie chronione.
  Globalna nawigacja odrzuca gest przeciągnięcia/przewinięcia. Scena zachowuje
  własną historię, respektuje wysokość paska; przywrócenie fokusu nie dopisuje
  fałszywego rozdziału do historii. Nie zmieniono modelu ani istniejących PNG.
- Regresja Python: 74 passed, 1 skipped/1.47s; Node testy geometrii,
  sprężyn, briefu i kwalifikacji pustego tła; składnia 4 JS i diff OK.
- Pierwszy Chrome audit cu5yvayg: brak inicjalizacji ramki testowej, 11.28s,
  bez wykonanych kontroli UI. Ponowienie bez zmiany kodu pttqocv4: 1 passed
  /21.44s. Obejrzano screenshot mobile-contextual-return.png. Hash i zakres
  dowodów w STUDIO_MEDIA_PILOT.md; nie deklarujemy testu fizycznego iPhone.
- Właściciel doprecyzował kółko również dla filmów/animacji. Native scroll
  i istniejący zoom/scena zachowane i sprawdzone. Dodano kryteria przyszłego
  wideo, bez twierdzenia, że odtwarzacz już istnieje albo został przetestowany.
- Kolejne doprecyzowanie: model musi rozróżniać funkcję elementu od efektu.
  Wspólny UI_INTERACTION_CONTRACT v1 dołączono do generatora wieloplikowego
  i planera web-design: menu/nawigacja/media/scroll/zoom/wideo/powrót/dekoracje,
  wyzwalacz/stan/alternatywa/kryterium. Test podłączenia promptów, bez inferencji
  ani treningu i bez zmiany zamrożonego briefu FORMA. To wskazówki wymagające
  niezależnego odbioru, nie gwarancja braku błędów modelu.
- Uwzględniono perspektywę nowego użytkownika: cel, orientacja, spodziewany
  rezultat, informacja zwrotna i wyjście bez ślepych zaułków. Nie deklarujemy
  ludzkiego myślenia modelu; sprawdzamy konkretne zachowania interfejsu.
- Test integracji promptów wykrył za długą instrukcję: 6 failed/19 passed
  (odmowa 409 przez limit kontekstu). Skrócono wspólną instrukcję, nie podniesiono
  limitu ani nie wyłączono bramki. Ponowienie poza sandboxem: 25 passed/1.29s,
  z atrapą modelu, bez inferencji. Pierwszy proces testu w sandboxie zawiesił
  się po 13 kontrolach; zakończono wyłącznie własny PID 919350 po identyfikacji.
- Kod demonstracji uruchomiony tylko w restricted Docker i izolowanej ramce;
  osobny headless Chrome, bez GPU/modeli, zmian DB, Windows czy Vast.ai.
  Nakładka nadal osobna od bazowego ZIP; to poprawka podglądu, nie wydanie klienta.

## 2026-09-20 — FORMA: sprężysta przestrzeń, drzewo narzędzi i responsywne menu

- Właściciel poprosił o rozbudowę poza kalkulator: ruch 3D/sprężyny, skalowanie
  wszystkich interakcji, rozwijane menu, powrót kliknięciem tła i stałe działanie
  przewijania/zoomu. Zmieniono nakładkę demonstracji, nie produkcyjne zlecenia.
- Dodano helisę, orbitę, falę i spokojny tor; X/Y/Z, orientację płaszczyzn,
  rzut krzywej, sprężyny z tłumieniem, głębię, pauzę i reset. Brak nowego
  silnika WebGL, pakietów, generacji, treningu i modeli; grafiki ComfyUI użyte
  ponownie. Kod głównego agenta, bez przypisywania go Qwenowi.
- Drzewo narzędzi i modalne menu Studio: grupy rozwijane, rzeczywiste przejścia,
  fokus, Escape, dotyk, tło-zamknięcie. Kreator briefu (5 typów, 8 modułów)
  produkuje jawny plan/kryteria, nie udaje AI ani wykonania wybranych usług.
  Zaznaczenie do ręcznego kopiowania, bez storage, publikacji czy danych klienta.
- Native scroll na stronie zawsze pozostaje dostępny; zoom w podglądzie
  zdjęcia również nad pustym obszarem. Ctrl+wheel i pinch nie są blokowane.
  Tło sceny/przycisk Wróć odtwarzają historię wyborów (max16), bez globalnego
  cofania po kliknięciu formularza. Menu/podgląd zamykają się po kliknięciu tła.
- Pierwszy audit 1i57v9k2 wykrył wyjście peryferyjnej karty poza szerokość;
  ograniczono amplitudę, bez usunięcia kontroli. txnplkpu: 1 passed/17.94s.
  Audity up7x4vmt i relyj8s3 wykryły wyścig opóźnionego close i ponownego
  otwarcia menu; stan open/closing/closed i kontrolowany Escape naprawiły fokus.
  lyp6wmcz: 1 passed/20.45s. Audit iqc6v26o wykrył zbyt długie dochodzenie
  sprężyny przy wolniejszych klatkach; dodano twardy limit 1.8s od wejścia.
  Przy sprzątaniu tego błędu wystąpił wyścig profilu Chrome (Directory not empty),
  bez ingerencji w profil użytkownika. pzxb24g1: 1 passed/23.46s, z powrotem tłem.
- Regresja 74 passed/1 skipped/1.46s; dodatkowo 24 passed/1 skipped/0.49s po
  zmianie opisu podglądu. Node: geometria, sprężyny (także duży krok czasu),
  tory, walidacja briefu i brak fałszywego wykonania. Składnia JS i diff OK.
- Kontrole responsywności obejmują 320–2560px, menu otwarte, formularze,
  tekst 200%, emulowany dotyk i zmianę viewportu. Nie testowano fizycznego
  iPhone/Safari ani FPS. Przy małym/niskim ekranie i reduced motion wszystkie
  narzędzia zostają w układzie statycznym. Obejrzano zrzuty helisy i 320px.
- Python demonstracji nadal tylko restricted Docker; osobny Chrome bez GPU,
  preflight istniejącego helpera. Bez zmian DB, usług Vast.ai, Windows i wag.
  Osobna nakładka podglądu nie jest jeszcze paczką bazowa aplikacja+media w ZIP.
- Końcowy audit y443q1s6: 1 passed/21.95s, hash w STUDIO_MEDIA_PILOT.md.
  Uwzględnia zoom całego podglądu, systemowy pinch, cofanie tłem, funkcje menu
  na sześciu rozmiarach, touch/Escape, konfigurację ruchu i brief. Obejrzano
  końcowe menu 320px. Właściciel pozytywnie ocenił działanie; zachowano wersję
  bez dokładania następnych efektów. Nie oznaczono projektu jako wydanego.

## 2026-09-20 — FORMA: główna scena zdjęć sterowana przewijaniem

- Właściciel doprecyzował, że oczekuje interakcji całej strony, nie jedynie
  płynniej otwieranych okien. Rozwinięto istniejącą nakładkę: hero prowadzi
  do sceny, naturalne przewijanie przesuwa trzy zdjęcia w perspektywie CSS,
  zmienia skalę projekcji, pierwszy plan, nasycenie i rozdział.
- Dodano nawigację studiów, wskaźnik przebiegu, „Pomiń scenę”, obsługę fokusu.
  Bez przejęcia wheel na stronie, krzywych płaszczyzn tekstu, nowych zależności
  i nieustannej pętli renderu. Modal pozostał opcją detali. Mobile, niski ekran,
  reduced motion i brak JS mają czytelny układ zwykły. To płaszczyzny PNG,
  nie przestrzenne modele obiektów; nie deklarujemy „najnowszej technologii”.
- Pierwszy Chrome audit studio-browser-x23lxwzc wykrył poziomy overflow od
  przekształconych elementów. Naprawiono clipping warstwy perspektywy; test
  nie został osłabiony. Przy sprzątaniu tego nieudanego testu wystąpił też
  wyścig usuwania prywatnego profilu Chrome (Directory not empty); nie
  usuwano danych użytkownika. Kolejny audit q5wvo7iw zaliczony (7.93s).
- Przegląd zrzutów ujawnił prześwitywanie obrazów podczas przejścia; usunięto
  przezroczystość obu pierwszoplanowych kart, zachowując głębię i nasycenie.
  Dodano rzeczywisty test kółka wstecz oraz pominięcia sceny.
- Końcowy audit studio-browser-hnfxdrs9: 1 passed/9.93s; hash i szczegóły
  w STUDIO_MEDIA_PILOT.md. Test wiąże wszystkie cztery CSS/JS nakładki,
  bazowe źródła i media hashami. Regresja 74 passed/1 skipped/1.46s,
  Node geometria i składnia JS, diff --check zaliczone.
- Uruchomiono nowy podgląd lokalny na 120 minut. Obrazy wykorzystano ponownie,
  bez inferencji, treningu, pobierania ani nowych wag. Testowy Python tylko
  w restricted Docker z kontrolą dostępności zasobów; przeglądarka bez GPU.
  Bez danych produkcyjnych, publikacji strony, Upwork, zmian Windows/Vast.ai.
  Nadal demo/nakładka podglądu, nie kompletne wydanie aplikacja+media w ZIP.

## 2026-09-20 — FORMA: animacja zdjęć zamiast zwykłego otwierania okien

- Na uwagę właściciela przebudowano istniejącą nakładkę galerii: powiększanie
  zdjęcia od karty, animowane kadrowanie bez deformacji, powrót, przełączanie
  kierunkowe i łagodne ujawnienie sterowania. Dialog pełnoekranowy bez ramki;
  pozostają fokus, Escape, zoom kółkiem/przyciskami, motywy i mobilny układ.
- Maszyna stanów chroni przed nakładającymi się przejściami; szybkie zamknięcie,
  resize i reduced motion nie pozostawiają klonów ani blokady przewijania.
  Parallax/skalowanie kart działa przez rAF na scrollu, bez przejęcia scrolla.
  Kod głównego agenta, bez przypisywania go Qwenowi; istniejące PNG ComfyUI
  użyte ponownie. Bez inferencji, treningu, pobierania i modyfikacji Windows.
- Trzy niezaliczone audity zachowano: studio-browser-07a1g91t, -i32vs2gw,
  -y7c0vi58. Pierwsza hipoteza opóźnionego cancel nie wystarczyła. Trace
  wykazał natychmiastowe native close po Escape mimo preventDefault w cancel.
  Dodano obsługę Escape przed native close watcher, bez osłabienia kryterium
  faktycznie działającej animacji powrotu.
- Końcowy Chrome audit studio-browser-qffj4d4d: 1 passed/7.93s; hash i zakres
  w STUDIO_MEDIA_PILOT.md. Testuje rzeczywiste kółko/klawisze, animacje,
  fokus, mobile/reduced motion, szybką rezygnację, kalkulator i źródła ZIP.
  Prywatny Chrome bez GPU, syntetyczny backend wyłącznie restricted Docker;
  preflight dostępności zasobów w istniejącym helperze. Bez danych produkcji.
- Regresja: 74 passed, 1 skipped/1.45s; test_studio_motion.cjs sprawdza skalę,
  crop i niepoprawne prostokąty; node --check i git diff --check zaliczone.
  Obejrzano zrzuty otwierania i mobilnego widoku. Brak pomiaru FPS/fizycznego iOS.
- Uruchomiono nowy lokalny podgląd 120 minut (stary zachowuje stare zasoby).
  Dokumentacja wyjaśnia restart podglądu i reduced motion. Nadal osobna nakładka,
  nie gotowe wydanie klienta: archiwum bazowe nie zawiera jeszcze mediów.
  Nie publikowano strony ani nie zmieniano statusu rzeczywistych zleceń.

## 2026-09-19 — obrazy ComfyUI na stronie FORMA i dostęp do wag Windows

- Na polecenie właściciela sprawdzono współpracę lokalnego Qwena z ComfyUI,
  bez chmury. Preflight: Docker pusty, Ollama bez modeli, GPU RTX5090
  912 MiB zajęte/3%, Comfy8188 nie działa. Qwen utworzył trzy ustrukturyzowane
  prompty; przejrzano je przed renderem. Własny graph/native nodes,
  brak wykonywania poleceń/grafów dostarczonych przez model.
- Pierwszy render zatrzymany: dysk Windows niewpięty do filesystemu,
  mimo widoczności nvme0n1p4. Nie pobrano niczego. Próba sudo -n odmówiona
  z powodu hasła; właściciel wykonał polecenia montowania. Potwierdzono ro.
  Stary niekompletny raport studio-media-gh_2xp2l zachowany. Skrypt teraz
  zapisuje jawny blocked/shared_weights_not_mounted zamiast niepełnego wyniku.
- Na dodatkowe żądanie stałego montowania przygotowano jednostkę systemd
  po zweryfikowanym UUID, ro/nosuid/nodev/noexec, timeout15s i opcjonalny
  WantedBy. Nie zmieniano fstab (zawiera zastany wpis placeholder Dockera),
  bootloadera ani usług wynajmu. Administrator zainstalował jednostkę;
  odczyt systemctl potwierdził enabled/active, mount ro. Nie restartowano.
  Publiczny wzór nie zawiera rzeczywistego UUID; lokalny plik poza repo.
  Launcher ComfyUI ostrzega teraz przy braku dysku zamiast sugerować download.
- Własny ComfyUI8189 użył istniejących wag Z-Image Turbo/Qwen4B/VAE
  z Windows tylko do odczytu, wyniki wyłącznie Linux. 3 PNG 768×512, 8 kroków:
  53.268s/48.651s/48.747s. Proces zakończony po generacji. Obejrzano wszystkie
  trzy obrazy (chromowana rzeźba, betonowy pawilon, szkło/limonka/metal).
- Dodano zaufaną nakładkę galerii do osobnego podglądu: hero, trzy obrazy,
  scroll-scale, modal, kółko 100–240%, +/−/Reset, strzałki, Escape i fokus,
  motywy/mobile/reduced-motion. Grafiki przez checksum + sprawdzone PNG,
  data URI w istniejącej opaque ramce. Bez rozluźniania CSP lub uprawnień.
  Kod integracji głównego agenta, prompty Qwen, bitmapy ComfyUI.
- Pierwsze testy launchera: 3 failed przez import modułu przy uruchomieniu
  jako pakiet; naprawiono import i izolowano powiadomienia w testach.
  Potem 44 passed/1 skipped. Audity browser wykazały problemy sterowania
  testu (kursor kółka, asynchroniczny close/fokus, zbyt krótki smooth scroll).
  Zachowano wszystkie raporty; bez osłabiania asercji dodano ruch kursora
  oraz ograniczone oczekiwanie na stan. Końcowo 1 passed/5.42s z prawdziwym
  kółkiem CDP, Escape, PNG, mobile i kalkulatorem. Regresja95 passed/1 skipped
  w2.91s, osobno9 passed/.21s po dodaniu kontroli obcych kolejek co5s.
- Udostępniono właścicielowi dwugodzinny lokalny podgląd z obrazami. Nie
  zmieniono produkcyjnego pulpitu/danych. ZIP kandydata nadal bazowy bez
  nakładki mediów, jawnie opisany w raporcie. To pilot integracji, nie
  autonomiczna dostawa premium. Szczegóły/prompty/ścieżki/hashes/ograniczenia:
  docs/organization-os/STUDIO_MEDIA_PILOT.md.

## 2026-09-19 — projektant CSS, kontrola wyniku i podgląd FORMA

- Wydzielono ograniczone zadanie projektowe lokalnego Qwena. Tylko CSS,
  niezmienne funkcje/testy, potwierdzona bazowa wersja i browser, jeden
  wariant bez resetu wcześniejszego limitu napraw. Testy wejścia/kontraktu:
  początkowo 47 passed/0.90s; z walidacją podglądu 62 passed/1.17s.
- Kontrola zasobów przed generacją: Docker pusty, ComfyUI nie nasłuchuje,
  31223 MiB wolnej pamięci GPU. Bez zmian Vast.ai, sterowników, Windows
  czy innych procesów. Qwen zmienił wyłącznie style.css; całość z ponownymi
  testami logiki i 8 HTTP trwała 17.703s. Nie trenowano modelu.
- Browser funkcjonalny 1 passed/4.42s: poprawne kalkulacje, mobile/menu,
  motywy, FAQ, kontrole braku obcięcia kontrolek, widoczność wyniku, ZIP
  zgodny ze źródłami i zamknięta bramka wydania. Główny agent obejrzał
  4 screenshoty. Prototyp nadal szablonowy, bez odbioru jakości premium.
- Wymaganie z briefu CSS (ukrycie zbędnego Menu na desktopie) pominięte
  przez model; po dodaniu osobnej kontroli projektowej realny browser:
  1 failed/3.83s, design-desktop-menu-hidden. Zachowano porażkę i poprzedni
  raport funkcjonalny; nie obniżano kryteriów i nie generowano bez końca.
- Na prośbę właściciela o pokazanie efektu dodano ograniczony lokalny
  podgląd syntetycznej witryny FORMA. To nie pulpit firmy. Bez produkcyjnej
  bazy/tokenów, localhost, limit 120 minut/60 wycen, opaque iframe i CSP,
  Host/Origin/CSRF, backend wyłącznie w istniejącym restricted Docker.
  Kontrola działającego podglądu 16 passed/0.79s, w tym odmowy dostępu
  i rzeczywista wycena 2125. Udostępniono adres właścicielowi; proces ma
  sam zakończyć się po limicie. Nie publikowano strony klientom.
- Narzędzia, dokładne raporty, ograniczenia i sposób ponownego otwarcia:
  docs/organization-os/UPWORK_WEB_PILOT.md. Surowe raporty/ZIP/screenshoty
  pozostają w prywatnym workspace; na GitHub wyłącznie kod/testy/docs.
- Końcowa regresja: 95 passed, 5 skipped/3.20s. Pominięte wyłącznie jawne
  pilotaże opt-in; kontrolę żywego podglądu i CSS opisano osobno powyżej.
  `git diff --check` bez błędów.

## 2026-09-19 — syntetyczne zlecenie webowe: Qwen, poprawki, browser, ZIP

- Po przypomnieniu priorytetu Upwork rozwinięto istniejący profil wieloplikowy,
  nie tworzono równoległej fabryki. Właściciel nadal sam komunikuje się na
  Upwork. Nie pobierano ogłoszeń ani nie przedstawiano fikcyjnego briefu jako
  rzeczywistego klienta. Nowy własny case FORMA jest wyłącznie ewaluacyjny.
- Ustalono przed generacją brief, niezależne testy cen, osiem prób HTTP oraz
  interakcje desktop/mobile. Qwen wygenerował 9 plików w 28.115s/3738 tokenów;
  cały pierwszy przebieg 36.585s. Logika zaliczona, health timeout: model
  pominął /health. Zachowano niezaliczony raport; bez obniżania kryteriów.
- Dodano ograniczone narzędzie rewizji tego pilota: hash rodzica/źródeł,
  przypięty model, jawne dozwolone pliki, limit dwóch poprawek w łańcuchu,
  niezmienne testy/moduł cen/README, wszystkie nowe wersje oddzielnie.
  Feedback przygotował główny agent; nie deklarujemy autonomicznego ogólnego
  frontend repair w produkcyjnym panelu. Kod poprawki nadal generował Qwen.
- Poprawka 1 (23.54s z testami) naprawiła backend; nie poprawiła app.js,
  choć wskazano jego problemy, i zmieniła również CSS. Osiem HTTP zaliczone.
  Rzeczywisty browser odrzucił kwotę 9437.50 zamiast wymaganego 9437.5.
  Poprawka 2 ograniczona wyłącznie do app.js: 5.511s/389 tokenów inferencji,
  9.552s łącznie z powtórzeniem testów. Oryginał i obie wersje zachowane.
- Przegląd kodu ujawnił błąd naszej ramki: gubione atrybuty root/body,
  w tym początkowy data-theme. Naprawiono tylko jawny allowlist atrybutów
  semantycznych/wyglądu, bez kopiowania root event handlers/style i bez
  zmiany CSP/tokenów/uprawnień sandboxa. Dodano trzy testy JS.
- Browser drugiej wersji: pierwszy audit 1 passed/3.80s; pełny z ZIP
  1 passed/4.41s. Osiemnaście zapisanych kontroli, cztery screenshoty,
  testowy ZIP przez realne API, porównanie wszystkich źródeł, bramka
  wydania nadal zamknięta. Testowa baza i sztuczny token, realne kontenery
  i Chrome bez GPU; wygenerowany Python nigdy nie był importowany na hoście.
- Obejrzano cztery zrzuty tych samych źródeł. Czytelny prototyp, nie poziom
  premium: szablonowy art direction, zbędne desktop Menu, dominująca notka
  uruchomienia, polski tekst do redakcji. Funkcjonalne passed nie oznacza
  gotowości biznesowej, dostępności WCAG ani oceny Awwwards.
- Testy: początkowo 2 porażki nowych fixture (test_logic w podkatalogu,
  niezgodnym z kontraktem generowania); poprawiono fixture, nie walidator.
  Następnie 30 passed/1 skipped. Szeroki przebieg w sandboxie utknął;
  zidentyfikowano i zakończono wyłącznie własny pytest PID780774 (143).
  Ponowienie z timeout poza sandboxem: 58 passed/5 skipped, a końcowo
  59 passed/5 skipped w 2.57s. Osobno 3 testy frame i 4 broker JS passed,
  składnia JS i git diff --check OK. Skipy to jawne rzeczywiste pilotaże.
- Zasoby sprawdzane przed inferencją/przeglądarką; żadnych obcych kontenerów
  nie zatrzymywano. Koniec: Docker pusty, Ollama models=[], GPU867MiB/0%.
  Bez restartów usług/hosta, zmian Vast.ai/Windows, treningu, zmian modeli,
  prawdziwych zadań, odbioru właściciela ani publikacji klientowi.
- Dokumentacja i hashe wszystkich dowodów: UPWORK_WEB_PILOT.md. Wynik to
  kandydat lokalny; kolejnym etapem jest poprawa jakości projektowania oraz
  rozszerzanie testów o kolejne autorskie briefy, a nie nauka na tym teście.

## 2026-09-19 — porównanie lokalnych modeli i podział specjalizacji

- Po akceptacji podziału ról sprawdzono rzeczywisty lokalny inwentarz:
  Qwen3.8:27b, gpt-oss:20b oraz jego lokalny alias. Gemma nie jest dostępna;
  nie wznowiono pobierania, nie instalowano innych modeli. Aktualną zgodę
  właściciela na zasoby stosowano zgodnie z AGENTS.md, bez zmian Vast.ai.
- OpenAI Docs i dokumentacja Ollama posłużyły do jawnego `think=low` dla
  lokalnego gpt-oss; boolean nie jest właściwym profilem tej rodziny.
  Adapter zachowuje domyślne think=false Qwena, ignoruje pole rozumowania
  w zapisywanej odpowiedzi i odrzuca nieprawidłowy profil przed siecią.
  Nie używano płatnych usług/API ani modelu GPT-6 do lokalnej inferencji.
- Porównanie v2: wspólne kontekst8192, 6 wątków, timeout120s, maks.2400
  tokenów naprawy/1200 decyzji. Digest sprawdzany przed wywołaniem. Format
  JSON nie zastępuje testów. Profile i różnice opisano w MODEL_COMPARISON.md.
- Preflight sandbox początkowo blokował odczyt GPU/Dockera/loopback;
  powtórzono po eskalacji. Docker pusty, Ollama pusta, RTX5090 867 MiB.
  ComfyUI nie nasłuchiwało. Zezwolono wyłącznie na ConnectionRefusedError
  tej usługi; timeout/uprawnienia/nieznany stan nadal blokują testy.
- gpt-oss: cztery naprawy, 3/4; dwanaście decyzji, 9/12; 60.822s.
  Qwen pierwszy przebieg: 4/4 naprawy, 6/6 podjętych decyzji, przerwanie
  przez ValueError preflight przed dalszymi przypadkami (53.178s).
  Nie udajemy znajomości dokładnej przyczyny: oryginalny raport jej nie podał.
  Dodano bezpieczne stałe kody preflight zamiast logowania obcych danych.
- Po ponownym odczycie zasobów wykonano jedną nową pełną serię Qwena:
  4/4 naprawy, 11/12 decyzji, 65.699s. Zachowano pierwszy raport i wszystkie
  nieudane odpowiedzi; nie uśredniano wyłącznie najlepszych prób.
- Główny agent przejrzał kod/uzasadnienia pełnych serii. Zidentyfikowano
  błędne łączenie rozłącznych przedziałów u gpt-oss, błędy decyzji odbioru
  obu modeli, niewłaściwą eskalację cyklu u gpt-oss i dwa angielskie
  uzasadnienia. Ograniczenia i hashe raportów zapisano w MODEL_COMPARISON.md.
- Kod modeli uruchamiano wyłącznie w istniejącym ograniczonym Docker runnerze,
  bez sieci, z testami niezależnymi od modelu. Kontenery własne zakończone;
  końcowy Docker pusty, Ollama models=[], GPU867MiB/3%. Żadnych restartów
  hosta/usług, ingerencji w obce procesy, Windows ani danych klientów.
- Testy adaptera/porównania/napraw/ról/quality/inference/history:
  82 passed / 2.86s; końcowo po dodatkowych testach JSON null/nieznanej
  kolejki oraz pamięci GPU: 88 passed / 2.90s. Mniejsze serie: 45, 67 i 28 passed.
  Tryb dry-run obu modeli nie wykonuje inferencji; git diff --check OK.
- Nie zmieniono produkcyjnego routingu/konfiguracji, wag ani statusów zadań.
  Dane treningowe nadal 14 train, 0 validation, 0 test; bez treningu.
  Qwen pozostaje wykonawcą pod kontrolą. Nie przyznano żadnemu modelowi
  autonomicznego odbioru ani nie ogłoszono gotowości premium web/media.

## 2026-09-19 — specjalizacja modeli przed stroną pokazową

- Właściciel zmienił priorytet: najpierw dostrojenie i ocena modeli dla
  stron wysokiej jakości, potem demonstracja. Nie deklarujemy maksymalnej
  możliwej jakości ani zakończenia treningu. Plan i źródła zapisano w
  WEB_MODEL_SPECIALIZATION.md: frontend, art direction, interakcje,
  dostępność, funkcjonalność i wizualny odbiór, nie tylko testy Pythona.
- Sprawdzono aktualną instrukcję Unsloth Qwen3.8, kartę checkpointu oraz
  TRL 0.24. Architektura qwen3_5 w lokalnym config jest zgodna z opisem
  Qwen3.8; nie należy przenosić ostrzeżeń dotyczących innej rodziny bez
  sprawdzenia właściwej instrukcji. Odczytano strony referencyjne jako
  inspirację; nie kopiowano ich zasobów. Szczegółowa strona ocen Awwwards
  niedostępna przez narzędzie (timeout), bez udawania audytu wizualnego.
- Dodano CPU/offline check_sft_tokenization.py: dokładna granica prefiksu,
  niezmieniona odpowiedź, EOS, odrzucenie tokenów sterujących, brak cichego
  truncation. Maskowanie jawne, bo szablon nie ma bloków generation dla
  assistant_only_loss. To preflight, nie integracja z właściwym trenerem.
- Rzeczywisty tokenizer: istniejące 12 przykładów, 345–1850 tokenów,
  wszystkie mieszczą się w 2048. Nowe dwie specyfikacje: 1703/1408 tokenów,
  1376/1094 tokeny odpowiedzi, kontrola przy limicie 4096 zaliczona.
  Wagi nie były ładowane ani zmieniane przez kontrolę tokenizacji.
- Zasoby przed inferencją: Docker pusty, RTX5090 867 MiB/3%, Ollama models=[].
  Dodano generator sześciu autorskich briefów planning, nie kodu.
  Pierwsze wywołanie zablokowała sieć sandbox (przed inferencją); po
  eskalacji lokalny Qwen zakończył sześć propozycji w 112.188 s.
  Raporty i surowe odpowiedzi zachowane w web-design-drafts-d7m70f1h.
- Wszystkie formaty przeszły, lecz przegląd wszystkich treści wykazał m.in.
  nieaktywną kulę Właściciela, zamianę Brain w księżyc, pominięte przybliżanie,
  angielski zamiast polskiego, niedokończony opis mimo done_reason=stop oraz
  pozorny sukces wysyłki. Poprawny JSON nie jest dowodem gotowości.
- Przygotowano dwie nowe autorskie odpowiedzi do istniejących briefów;
  odebrano tylko planning po przeglądzie. Hash rzeczywistej notatki odbioru
  przypisano w rekordach; pozostałych czterech propozycji nie zatwierdzono.
  Zbiór wzrósł z 12 do 14 train, validation/test nadal 0. Bramka 200/25/50
  pozostała bez zmian; --require-ready zwróciło oczekiwane 2. Brak eksportu,
  treningu, zmiany modeli produkcyjnych i publicznej publikacji surowych danych.
- Testy narzędzi danych/treningu: 95 passed / 1.92 s. git diff --check
  poprawny. Końcowe odczyty po eskalacji: Ollama models=[], Docker pusty.
  Kontrole nie zatrzymywały żadnych usług; wywołania odczytu w sandboxie
  były blokowane i nie stanowiły dowodu zatrzymania serwera Ollama.
- Poprzedni checkpoint 7d916b0cda2bc89caed481d7703f27ee8c253742 został
  wysłany na gałąź roboczą origin i potwierdzony odczytem ls-remote.

## 2026-09-19 — przygotowanie publicznego checkpointu GitHub i ponowne użycie OSS

- Właściciel polecił nadzorować wyniki lokalnych modeli, zapisywać projekt
  na GitHub i korzystać z istniejących komponentów. Zapisano zasady w AGENTS.md
  oraz GITHUB_WORKFLOW.md. Odczyt REST potwierdził publiczne origin
  Ultra-990/ai-company. GitHub CLI GraphQL zwrócił 401, lecz odczyt REST
  oraz git ls-remote przez istniejące SSH powiodły się po eskalacji sieci.
- Pracę krótko wstrzymano po zgłoszeniu ruchów kursora; odczyt hosta:
  GPU 869 MiB/2%, bez ingerencji w procesy. Właściciel wskazał i usunął
  problem portu USB, wycofał zgłoszenie i praca została wznowiona.
- Zastano ponad 300 nieśledzonych plików i zmiany wcześniejszych etapów.
  Przygotowany checkpoint zachowuje tę pracę; nie przypisujemy jej całej
  bieżącej sesji ani nie uznajemy za końcowe wydanie produkcyjne.
- Uzupełniono .gitignore: cały data/ z zagnieżdżonymi backupami, SQLite
  WAL/SHM, swap edytora, stare kopie, lokalne aktywne profile wykonania,
  wagi i skompresowane archiwum UI. Dodano wyłączone szablony konfiguracji.
  Sprawdzono konkretne problematyczne ścieżki przez git check-ignore.
  Pliki prywatne i archiwum pozostają na dysku; niczego nie usuwano.
- Gitleaks 8.30.1 pobrano z oficjalnego wydania do prywatnego workspace,
  sprawdzono SHA-256 archiwum z digestem upstream przed wykonaniem.
  Skan dokładnego snapshotu indexu: około 5.30 MB, brak wykrytych sekretów.
  Skan historii HEAD: 181 commitów, również bez wykrytych sekretów.
  Raporty redagowane w /home/marcin/ai-company-workspaces/git-publication-H3jVq0/.
  Brak wykrycia nie stanowi dowodu braku wszystkich rodzajów danych wrażliwych.
- Sprawdzono listę staged: bez baz, archiwów binarnych i symlinków.
  git diff --cached --check wskazał tylko zastany whitespace w vendored
  three.core.js:49957; nie modyfikowano oryginału biblioteki. Kontrola
  naszego kodu z wyłączeniem vendor przeszła. Licencja Three zachowana.
- Przejrzano pierwotne README/licencje Aider (Apache-2.0), Playwright
  (Apache-2.0), OpenHands/Agent Canvas (MIT). OPEN_SOURCE_REUSE.md opisuje
  potencjalne zastosowania i wymagane pilotaże; nie instalowano ich stosów,
  nie włączano obcych agentów z uprawnieniami hosta. Gitleaks już użyty.
  Nie wysyłano repozytorium do modelu chmurowego ani danych klienta do Qwena.
- Pełna regresja przed zapisem: 1212 passed, 9 skipped, 69.48 s.
  Pominięte testy to jawne pilotaże modelu/kontenera/przeglądarki wymagające
  osobnych flag. Brak inferencji/treningu podczas tego przebiegu.
- Node: 15/15 plików testowych CJS/MJS zaliczonych. Ostateczny snapshot
  indexu około 5.31 MB ponownie sprawdzono Gitleaks: brak wykrytych sekretów.
  Przygotowano 354 zmienione/dodane pliki do checkpointu gałęzi
  chore/roadmap-bootstrap-20260909T122313Z, bez merge/force/main.

## 2026-09-19 — Qwen generuje aplikacje modułowe, rzeczywisty pilot i przeglądarka

- Dodano python-web-multifile-v1 do istniejącego owner-only LocalInference.
  Ten sam model/digest, kolejka, limit kontekstu, audyt i powiązanie instrukcji;
  bez drugiego systemu zadań. JSON Schema oraz walidator: 7–16 plików,
  moduł logiki i osobny plik testów, kontrola ścieżek, składni i duplikatów.
  Atomowy zapis paczki i nieodebranej próby; żadnego kodu modelu na hoście.
- /os/work: osobny przycisk modułowy dla wykonawcy, opcjonalny istniejący
  runner po generowaniu i komunikat kierujący do odbioru paczki w Budowie
  i testach. Zmieniono wersję work.js dla cache. Uzupełniono centrum pomocy
  i MULTIFILE_RUNNER.md. Pełna regeneracja odrzuconej wersji modułowej
  jest blokowana: nie udajemy naprawy przez wymianę testów. Ręczna korekta,
  test nowej wersji, odbiór i wydanie są dostępne; automatyczna naprawa
  modułowa pozostaje kolejnym etapem. Płaski profil napraw zachowany.
- Pierwszy przebieg: 2 failed/47 passed — fixture miała test w katalogu
  nested zamiast wymaganego tests/test_logic.py. Naprawiono fixture;
  49 passed/3.28 s. Następnie 82 passed/3 deselected/4.91 s obejmujące
  generowanie, odrzucanie niepoprawnych źródeł, uprawnienia, idempotencję,
  rewizje, runner, preview oraz odbiór. Osobne testy Node sprawdzają nowy
  przycisk, profil żądania i związanie opcjonalnych testów z zapisaną paczką.
- Kontrola zasobów przed pilotem: Docker pusty, GPU RTX5090 770 MiB/2%.
  Pierwsza próba w piaskownicy nie dotarła do Ollamy (raport zachowany
  w multifile-generation-i0ae4zzp). Po wymaganej eskalacji jeden rzeczywisty
  przebieg Qwena wygenerował siedem plików. Niezależny kod testów napisano
  przed generacją i dodano wyłącznie do kopii testowej w kontenerze.
  11 metod testowych (9 modelu + 2 własne/15 subprzypadków) oraz 7 kontroli
  HTTP zaliczone. Całość 18.636 s. Raport, prompt, wynik i sumy źródeł:
  /home/marcin/ai-company-workspaces/qwen-training/multifile-generation-ermobazb/report.json.
- Kod Qwena przejrzano jako dane. Rzeczywisty Chrome + testowe API + własne
  kontenery sprawdziły niezmienione źródła: 8*322=2576, zmianę parametrów,
  wynik zero, błąd wartości ujemnej, pusty formularz oraz brak dostępu do
  parent.document. Pierwszy przebieg doszedł do końca asercji aplikacji,
  ale sprzątanie profilu Chrome zgłosiło Directory not empty. Dodano
  kontrolowane Browser.close przed usunięciem profilu; ponowienie:
  1 passed/3.28 s. Bez wyłączenia izolacji przeglądarki i bez jej GPU.
- Końcowy zestaw help/generation/pilot: zawieszenie TestClient w sandboxie
  podczas startu pustej testowej FastAPI. Po eskalacji 36 passed/1 skipped/
  1.58 s. Własny zawieszony PID 719174 zidentyfikowano i zakończono SIGTERM.
  Nie dotykano cudzych procesów. Node i składnia work.js zaliczone.
- Pełny stary smoke check_work_browser.py dwukrotnie nie doszedł do strony
  wejściowej. Odczyt curl potwierdził brak serwera na 127.0.0.1:8000;
  nie jest to zaliczony audyt całego Centrum realizacji. Nie uruchomiono
  produkcyjnego lifespan/migracji dla testu. Nowa logika formularza ma
  test DOM/żądań, a wygenerowana aplikacja rzeczywisty test Chrome powyżej.
- Artefakt podsumowania: evidence/qwen-multifile-20260919.json. To pojedynczy
  syntetyczny przykład, nie ogólny benchmark, trening, odbiór klienta lub
  dowód jakości stron premium/generatorów muzyki i wideo. Demo mnoży float,
  nie stanowi aplikacji księgowej. Nie zmieniano prawdziwych postępów,
  zleceń, modelu bazowego, usług Vast.ai, sterowników ani dysku Windows.
  Końcowy Docker pusty; Ollama models=[]; git diff --check poprawny.

## 2026-09-19 — odbiór paczki, wydanie wielomodułowe i przygotowanie treningu

- Na polecenie właściciela domknięto etap wydania przed treningiem modeli.
  Nowy package_acceptance wykorzystuje istniejące Artifact/AuditEvent, bez
  nowej bazy. Odbiór wiąże run, źródła, raport, profil i zakres Task; nie
  podszywa się pod LocalInference i nie zmienia postępu/zamknięcia zadania.
- Owner-only GET/POST package-review: jawne kryteria, dowody, decyzja,
  potwierdzenie, checksum kontekstu i UUID. Powtórzenie nie tworzy duplikatu
  ani nie przywraca starej decyzji po wycofaniu. Najnowszy test i aktualny
  profil wymagane. Zmiana zakresu, anulowanie zadania lub wybrany plan HTTP
  starego cyklu blokują wydanie. Nie omijamy planu, którego nowy cykl nie wykonuje.
- Release/released.zip/handoff obsługują wielomodułowy profil po tej decyzji.
  Historyczne decyzje i wydania zachowane; wycofanie odbioru blokuje nowe
  pobrania, ale nie odwołuje wcześniej pobranych ZIP-ów. Wydanie zawiera
  odpowiednie unittest discover, instrukcje PL/EN i prawidłowy profil
  w metryce. Prywatne notatki odbioru nie trafiają do instrukcji klienta.
- Formularz w historii Budowy i testów: wczytanie kontekstu, jawna decyzja,
  dowody, potwierdzenie i obsługa identycznego ponowienia po błędzie sieci.
  Tekst nie trafia do innerHTML. Testy Node formularza i panelu zaliczone.
  Nie wykonano jeszcze osobnego wizualnego audytu nowego formularza w Chrome.
- Pierwszy zestaw: 33 passed/1 deselected/1 error — pytest zebrał pomocniczą
  funkcję „tested” jako test. Zmieniono nazwę helpera; następnie 56 passed/
  1 deselected. Dalszy przebieg w piaskownicy zawiesił się bez wyniku;
  powtórzenie po eskalacji: 18 passed/1 deselected/1.09 s. Własny proces
  pytest 685295 zakończono SIGTERM po weryfikacji PID poza namespace;
  pierwsza próba w piaskownicy miała „No such process”. Bez cudzych procesów.
- Rozszerzony rzeczywisty pilot API: 1 passed/1.58 s, własny kontener,
  syntetyczna tymczasowa baza. Test → odbiór → wydanie → handoff → ZIP,
  następnie podgląd; brak zmian rzeczywistego Task. Szersza regresja:
  98 passed/3 deselected/8.12 s; bez modeli w testach jednostkowych.
- Po sprawdzeniu zasobów (pusty Docker/Ollama, 770 MiB GPU) uruchomiono
  lokalnego Qwena w zamrożonej ocenie napraw: 4/4, 19.677 s, 8 rzeczywistych
  kontenerów przed/po, wszystkie cleanup_confirmed. Raport:
  /home/marcin/ai-company-workspaces/qwen-training/repair-evaluation-u2pio8kc/report.json.
  Źródła przejrzano niezależnie. Brak kodu modelu wykonywanego na hoście,
  brak treningowego eksportu tej suite i brak zmian produkcyjnego routingu.
- Rozbudowano walidator zbioru: kilka jawnych partii, wspólna kontrola
  duplikatów i wycieku rodzin/splitów, łączny limit rozmiaru, hashe partii,
  zatwierdzone liczniki, braki oraz rozkład umiejętności. Testy danych,
  generowania i oceny napraw: 83 passed/1.67 s.
- Dwie partie zweryfikowane wspólnie: 12 approved train, 0 validation/test;
  braki 188/25/50. Nie obniżono progu i nie udawano gotowości treningu.
  Zgoda na trening pozostaje zapisana; kolejny etap to kuracja nowych rodzin
  i odłożona ocena, potem osobny adapter i porównanie przed wdrożeniem.
  Nie powtarzano starego trzy-krokowego smoke jako rzekomego ulepszenia.
- Dokumentacja funkcji, centrum pomocy, dane i plan QWEN_TRAINING uaktualnione.
  Końcowa kontrola po dodaniu blokady anulowanego zadania: 33 passed/1.82 s;
  składnia JS i git diff --check poprawne. Kontenery własnego runnera nie
  pozostały, Ollama models=[] po zakończonej ocenie.
  Ostatnia aktualizacja komunikatu ujawniła nieaktualne dopasowanie tekstu
  w teście package-profile; poprawiono asercję tak, by nadal wymagała
  wyraźnego rozróżnienia kontroli struktury od wykonania aplikacji.
  Bez restartów usług, ingerencji w Vast.ai/Windows, publikacji klientom,
  płatności, prawdziwych odbiorów lub ręcznego poprawiania STATUS.md.

## 2026-09-19 — podgląd wielomodułowy, kontrola przeglądarki i ocena Qwena

- Domknięto następny etap: bezstanowy podgląd python-web-multifile-v1 przez
  istniejące API. Osobny tester, schemat raportu i przypięty SHA
  `6f655533645b196378e325f14f16e7b11d59eaa357d57c6dcd0ac39e8706abcd`.
  Klient nie dostarcza pliku sterującego, konfiguracji ani polecenia.
  Zachowano slot, limity, kontrolę izolacji i sprzątanie własnych kontenerów.
- API udostępnia ramce tylko publiczne CSS/JS (root i static/), bez Pythona,
  testów i README. Ramka ładuje lokalne klasyczne skrypty/style z manifestu;
  nie pobiera zależności. Opaque origin, CSP, brak credentiali i sieci
  pozostają zachowane. Każde GET to nowy kontener, brak sesji/POST/bazy.
- Capabilities i panel umożliwiają podgląd oraz ZIP kandydata, ale nadal
  blokują wielomodułowy automatyczny repair i zatwierdzone wydanie. Nie
  przeniesiono odbioru starszej paczki na nowe źródła. Bump wersji JS panelu.
- Kontrola sumy źródeł obejmuje teraz także każdą odpowiedź API w ramce,
  nie tylko stronę startową. Zamknięcie czyści HTML. Dodano testy komunikacji
  między ramką a rodzicem, obcego źródła/origin, limitu 30 żądań, złej sumy,
  spóźnionej odpowiedzi i zachowania blokady nowej ramki podczas przełączenia.
- Testy etapowe: 2 passed/1 skipped; następnie 20 passed/2 skipped.
  Prawdziwy pilot HTTP root/API: 1 passed/0.89 s; rozszerzony pilot API:
  1 passed/1.54 s. Bez źródeł klientów i produkcyjnej bazy.
- Chrome: pierwsza próba niezaliczona przez przestarzały kontekst CDP po
  nawigacji, nie błąd aplikacji. Helper obsługuje kasowanie kontekstów i
  osobne sesje ramek; bez wyłączania site isolation. Powtórzenie 1 passed/
  1.76 s, końcowe 1 passed/1.83 s. Potwierdzone CSS z static/, JS, kliknięcie
  obliczenia 8 × 322 = 2576 i zakaz dostępu do parent.document.
  Własny Chrome z GPU wyłączonym i prywatnym profilem; to nie ocena estetyki.
- Końcowa regresja runner/preview/quality/handoff/help/model adapter:
  120 passed, 4 deselected/6.58 s. Pominięte realne testy wywoływano osobno,
  nie uznawano pominięcia za sukces. Testy Node panelu/edytora/profilu i nowej
  komunikacji ramki zaliczone. Składnia JS i git diff --check bez błędów.
- Przed modelem: Docker ps pusty, Ollama models=[], RTX 5090 32607 MiB,
  770 MiB zajęte, 3% — migawka, nie gwarancja braku późniejszego wynajmu.
  Właściciel ponownie dopuścił użycie zasobów. Nie zmieniano usług Vast.ai.
- Qwen (lokalny alias qwen3.8:27b, przypięty digest) zaliczył 3/3 krótkie
  próby schema: pytania o brakujące dane, obliczenie bez wymyślania podatku
  i rozpoznanie niewspieranego zlecenia mimo instrukcji wstrzykniętej w opis.
  Raport: /home/marcin/ai-company-workspaces/model-quality-rua3tr_6/report.json.
- Przegląd kodu przez Qwena: pierwsza próba truncated_output, nie zastosowano
  wyniku. Powtórzenie ze schematem (po 4 krótkie uwagi/testy, 1536 tokenów)
  zakończone w 6.212 s. Wszystkie cztery zarzuty odrzucono po weryfikacji:
  mylenie kontekstów fetch, wildcard z broadcastem, lookup z żądaniem sieciowym
  i kierunku odpowiedzi. To konkretna porażka analizy, mimo poprawnego JSON.
  Nie trenowano na tych sugestiach jako poprawnych i nie awansowano modelu
  do samodzielnego audytora. Uzasadnienia i digest zachowano w
  evidence/qwen-preview-review-20260919.json obok dokumentacji Organization OS.
- Zaktualniono MULTIFILE_RUNNER, PACKAGE_EDITS, WORKBENCH i pomoc. Bez
  restartów hosta/usług, modyfikacji Windows, produkcyjnych statusów,
  publikacji klientom ani sztucznego podnoszenia procentu organizacji.
  Kolejny etap: odbiór dokładnej wersji edytowanych źródeł oraz wydanie,
  potem kontrolowane generowanie/naprawa modułów przez lokalny model.

## 2026-09-19 — wielomodułowe wykonanie przez API, raport i kandydat

- Kontynuowano priorytet realizacji zleceń; nie uruchamiano modeli i nie
  delegowano prac do GPT-5.6. Właściciel podtrzymał zgodę na samodzielne prace.
- Dodano zaufany dobór profilu na podstawie manifestu. Istniejący POST
  /api/package-runs uruchamia teraz także python-web-multifile-v1. Klient
  nie może przekazać własnego polecenia, obrazu, limitów, sieci ani nazwy
  profilu. Przypięto SHA testera do zaliczonego pilota: jego zmiana blokuje
  wykonanie do kolejnej weryfikacji. Zachowano Emergency Stop i konfigurację.
- Oddzielny schemat raportu wielomodułowego, wymagane wszystkie kontrole
  izolacji, poprawne zakończenie i sprzątanie. Rejestrowane istniejącymi
  PackageRun/Artifact/AuditEvent, bez nowej bazy lub sztucznego procentu.
  Ponowienie UUID nie wykonuje ponownie; limity trzech prób wersji, wspólny
  slot i niepewny stan zachowane. Zmiana konfiguracji podczas testu blokuje pass.
- Kandydat ZIP zawiera katalogi źródeł, raport dla tej wersji, manifest i
  właściwe polecenie unittest discover. Nie jest zatwierdzonym wydaniem.
  Podgląd, automatyczne poprawki i wydanie wielomodułowe jawnie niedostępne;
  API odrzuca takie operacje, a gotowość wskazuje brakującą integrację.
- Metadane paczek i wykonań otrzymały capabilities. UI pokazuje testowanie,
  historię, ZIP i link do edycji nowej wersji. Nie pokazuje niedziałających
  przycisków podglądu/naprawy Qwen. Kontrola struktury pozostaje samym odczytem.
- Testy pierwszej próby: 101 passed, 1 failed, 1 skipped. Błąd atrapy:
  zastępowała funkcję konfiguracji, zamiast zmieniać odczytywaną konfigurację;
  runner prawidłowo przechowywał referencję do fabryki. Test poprawiony,
  wynik: 102 passed, 1 skipped / 3.48 s. Pominięty tylko realny pilot.
- Rzeczywisty pilot API uruchomiony osobno po pustej liście Docker ps:
  AIC_MULTIFILE_API_PILOT=1 pytest test_real_multifile_api_pilot — 1 passed,
  0.56 s. Syntetyczne zadanie i tymczasowa baza, rzeczywisty własny kontener,
  kontrola importów/testów, raport, ZIP, identyczne ponowienie bez nowego
  wykonania, brak zmiany Task.progress; sprzątanie potwierdzone w raporcie.
- Regresje istniejących napraw, generowania, odbiorów, przekazania i pomocy:
  72 passed, 1 deselected / 7.73 s, modele i kontenery zastąpione atrapami.
  Trzy zestawy testów Node zaliczone, w tym wielomodułowe kontrolki i historia.
  Składnia JS oraz git diff --check poprawne. Brak testu rzeczywistego UI
  w przeglądarce; nie wykorzystano starszego skryptu zapisującego podglądy
  do produkcyjnego zadania #45. Końcowy odczyt Docker wymagał eskalacji
  po odmowie dostępu do socketu w piaskownicy; nie zmieniano jego uprawnień.
- Zaktualniono pomoc, WORKBENCH, PACKAGE_EDITS i MULTIFILE_RUNNER. Nie
  restartowano usług ani hosta, nie zmieniano Vast.ai, Windows, modeli,
  produkcyjnych danych, prawdziwych odbiorów ani generowanego STATUS.md.
- Następne prace: bezpieczny podgląd modułowy, odbiór dokładnej edytowanej
  paczki i finalne wydanie; następnie generowanie i naprawa modułów z oceną
  jakości modelu. Nie deklarujemy jeszcze pełnej obsługi dowolnego zlecenia.

## 2026-09-19 — wznowienie i rzeczywisty pilot wielomodułowego Pythona

- Właściciel potwierdził zakończenie wynajmu i zgodę na CPU/GPU, ocenę oraz
  trening modeli. Uaktualniono AGENTS.md; bez delegowania prac do GPT-5.6.
  Nie zmieniano Vast.ai, cen, sterowników, sieci ani usług. Podwyższona cena
  nie jest blokadą nowego najmu; zachowano wymóg ostrożnej kontroli zasobów.
- Domknięto zapis prac rozpoczętych przed przerwą: kontrola wielomodułowych
  źródeł (ścieżki, init, testy, składnia 3.10), owner-only odczyt z integralnością,
  panel problemów, bezpieczny staging, osobny adapter i tester oraz pilot CLI.
  Domyślny CLI tylko analizuje dane; wykonanie wymaga --run --rental-ended.
  Dotychczasowy płaski runner nadal odrzuca katalogi; nowy nie jest podłączony
  do produkcyjnego API wykonawczego. Odczyt paczki nie uruchamia jej kodu.
- Poprzedni przebieg: 54 passed, następnie 109 passed / 2 failed. Dwa błędy
  dotyczyły testów sprawdzających pusty tmp_path, w którym fixture tworzy test.db.
  Testy poprawiono, wydzielając katalog stagingu; po przerwie zweryfikowano:
  111 passed / 3.19 s (multifile, runner/preview, edycja i paczki), bez bazy live.
- Node: trzy pliki testów panelu profilu i edycji zaliczone sekwencyjnie.
  git diff --check bez błędów. Nie uruchamiano rzeczywistej przeglądarki.
- Po zmianie komunikatów końcowy przebieg w piaskownicy zatrzymał się przy
  teście API (bez tracebacku); przerwano wyłącznie własną sesję testową.
  Powtórzenie poza piaskownicą, z tymi samymi izolowanymi bazami i diagnostyką
  faulthandler: 79 passed / 1.94 s, w tym pomoc. Przyczyny zawieszenia nie
  przypisano kodowi bez dowodu. Ponowne trzy zestawy Node i składnia JS OK.
- Pierwszy odczyt Docker/NVIDIA w piaskownicy był niedostępny; po prawidłowej
  eskalacji Docker nie pokazał uruchomionych kontenerów, RTX 5090: 32607 MiB,
  771 MiB zajęte, 0% obciążenia. To migawka, nie ciągły monitoring wynajmu.
- Wykonano pięć rzeczywistych, sekwencyjnych pilotów w przypiętym obrazie:
  poprawny projekt importuje modules/ i odkrywa testy w tests/nested/;
  odrzucane są brak testów, błędne obliczenie, ujawnienie kodu przez HTTP
  i timeout. Każdy scenariusz uzyskał oczekiwany wynik; wszystkie kontenery
  posprzątane i brak pozostałości potwierdzony Docker ps z własną etykietą.
- Limity pilota: 1 CPU, 512 MiB RAM, 64 PID, 45 s, bez sieci i urządzeń GPU.
  Nie zmieniano danych produkcyjnych, statusów zadań, odbiorów ani STATUS.md.
  Zapis wyników z identyfikatorami obrazu/testera/kontenerów:
  docs/organization-os/evidence/multifile-pilot-20260919.json.
- Zaktualniono pomoc, dokumentację i komunikat panelu: pilot zakończony,
  ale nadal brak integracji nowego profilu z PackageRun, podglądem, odbiorem
  i wydaniem. Nie ogłoszono obsługi dowolnego zlecenia ani sukcesu paczki klienta.
  Modele nie były uruchamiane/trenowane w tym kroku; trening wymaga uprzedniej
  oceny jakości i przygotowania danych, nie samej dostępności GPU.

## 2026-09-14 — podgląd i bezpieczna edycja wieloplikowych źródeł

- Kontynuowano rozbudowę bez nowego pytania o zgodę. Inspekcja potwierdziła,
  że manifesty paczek obsługują katalogi i 100 plików, ale runner nadal
  wymaga wąskiego, płaskiego profilu Python. Nie rozszerzano jego uprawnień,
  nie uruchamiano kontenerów i nie przedstawiono zapisu plików jako wykonania.
- Dodano owner-only GET źródła pojedynczego pliku z manifestu oraz POST edits
  ze wskazaniem bazowej sumy i UUID. Zmiany/dodania/usunięcia są składane jako
  tekst w nową paczkę. Brak zapisu do plików hosta i brak importu kodu.
- Transakcja zapisuje nową wersję, istniejący audyt paczki i potwierdzenie
  pochodzenia wersji. Ponowienie identycznego żądania zwraca ten sam rezultat;
  inne zmiany z tym samym UUID są konfliktem. Błąd zapisu wycofuje całość.
- Oryginalna paczka i niezmienione pliki pozostają nienaruszone. Nowa paczka
  nie dziedziczy task_attempt_id, wyników testów ani odbioru. Zmiany chronionych
  testów rozpoznanych po konwencjach nazw są odrzucane; nowe testy dozwolone.
  To nie semantyczne rozpoznanie wszystkich testów ani ocena ich skuteczności.
- Zachowano limity 100 plików / 256 KiB / 1 MiB paczki i 8 MiB żądania JSON.
  Walidowane ścieżki, kolizje wielkości liter, plik/katalog, puste zmiany,
  usunięcie nieistniejącego pliku, unikalność usunięć i sumy potwierdzeń.
- Budowa i testy otrzymała listę ścieżek, podgląd źródła jako inertnego tekstu,
  edycję wielu plików w szkicu, opis wersji, zapis i link/ZIP nowej paczki.
  Szkic jest tylko w karcie; nie udajemy trwałego automatycznego zapisu szkicu.
  Zapisany szkic jest zamrożony; kolejna edycja otwiera nową bazę. Niepewny
  zapis zachowuje UUID i wymaga identycznej treści przed ponowieniem.
- Metadane paczki wskazują execution_profile albo null, na podstawie układu
  i niepustych źródeł. To nie wynik testów i nie potwierdzenie dostępności CPU.
  Nieobsługiwany układ zachowuje edycję, lecz nie pokazuje wykonania obecnym
  runnerem. Lista dozwolonych plików współdzielona z jego walidatorem.
- Wzmocniono odrzucenie spóźnionej odpowiedzi po wylogowaniu także po etapie
  dekodowania JSON, by stara odpowiedź nie przywracała źródeł w interfejsie.
- Testy: 47 passed / 1.87 s (edycja + paczki); szerszy zestaw obejmujący
  porównania, runner-atrapę, generowanie-atrapę, koordynację i pomoc:
  99 passed, 1 deselected / 4.77 s. Po dokumentacji i rozszerzeniu pomocy:
  83 passed, 2 deselected / 4.30 s. Testy przechodziły na izolowanych bazach.
- Node: test_package_editor.cjs i test_build_package_editor.cjs zaliczone
  (5 + 2 scenariusze symulowanego DOM/VM). Obejmują inertne źródła, wieloplikowy
  szkic, dokładny zapis, niepewne ponowienie, ochronę testów, ukrycie runnera
  dla niezgodnej paczki i brak przywrócenia danych po wylogowaniu.
  node --check build.js/package-editor.js i git diff --check zaliczone.
- Dokumentacja: PACKAGE_EDITS.md, odnośnik WORKBENCH.md oraz nowy temat pomocy
  właściciela. Bez ręcznej zmiany STATUS.md lub rzeczywistych statusów zadań.
- Nie używano Qwena, GPU, sieci modelowej, nowych kontenerów ani ciężkich testów.
  Nie restartowano serwera, usług, Dockera, hosta lub Vast.ai. Brak zmian
  na dysku Windows i w danych produkcyjnych. Brak E2E w rzeczywistej przeglądarce.
- Pozostaje pełne wykonanie kodu z wielu modułów i zależności: zmiana wymaga
  osobnego profilu, kontroli importów, limitów i rzeczywistego pilota izolacji.
  Nie odblokowano takiego wykonania na podstawie samych testów przechowywania.

## 2026-09-14 — koordynator przygotowania etapów i historia wznowień

- Kontynuacja zatwierdzonego planu bez ponownego pytania o zgodę na rutynowe
  prace. Aktywny wynajem Vast.ai nadal wyklucza inferencję, trening, kontenery
  i obciążające testy. Nie monitorowano ani nie zmieniano procesu najmu.
- Dodano checkpoint projektu (SHA-256 kanonicznego stanu) i owner-only
  POST /api/work-orders/{project_id}/prepare-next. Sprawdza dokładny widziany
  etap oraz zmiany briefu, statusów projektu/planu, delegacji, prób i inferencji.
  Daty UTC normalizowane identycznie przed i po odczycie SQLite.
- Atomowe przygotowanie zapisuje istniejącą instrukcję i jej audyt, bez nowej
  tabeli/kolejki. Ponowienie niezmienionego kontekstu zwraca tę samą instrukcję.
  Zmiana stanu daje 409 zamiast przygotowania innego etapu; błąd zapisu wycofuje
  transakcję. Nie zmienia postępu, zgód, kolejki ani odbioru właściciela/klienta.
- Koordynator przygotowuje jeden etap; po odrzuceniu ten sam z uwagami,
  po odbiorze kolejny. Nie jest jeszcze samodzielnym schedulerem i nie
  zastępuje modelu, QA ani bramki wydania. Nie dopisano fikcyjnych rezultatów.
- Wspólny handoff dodatkowo sprawdza stan projektu i planu: zablokowanego,
  anulowanego lub zakończonego zakresu nie można obejść starszym API instrukcji.
  Powtórzone identyfikatory etapów i zadania z obcego planu są niespójnością.
- UI /os/work: przycisk przygotowania bieżącego etapu, otwarcie konkretnej
  trwałej instrukcji bez ID do kopiowania; ochrona przed podwójnym kliknięciem
  i brak automatycznego ponawiania po konflikcie. Wyczyszczony panel nie
  pobiera już list w tle tylko dlatego, że wspólna sesja nadal istnieje.
- GET /api/local-inference: opcjonalne project_id, before, attention_only,
  paginacja 30 wyników i licznik wszystkich nierozstrzygniętych wpisów w zakresie.
  Historia w UI domyślnie dotyczy wybranego projektu; można przełączyć na całość,
  stare wyniki i same oczekujące/trwające/niepewne. Odczyt nie odpytuje modelu.
- Testy: 36 passed (wstępna regresja), 10 passed (pierwszy koordynator),
  72 passed / 5.40 s (koordynacja, historia, inferencja-atrapa, handoff i projekty).
  Końcowy zestaw: 134 passed, 4 deselected / 9.20 s; w tym blokady planu,
  wszystkie cztery etapy, poprawa odrzuconego wyniku, konflikt starej karty,
  rollback zapisu, właściciel/worker, historia i brak duplikatów.
- Node: oba pliki test_project_guide.cjs i test_work_coordination.cjs zaliczone
  (8 + 5 scenariuszy, mały DOM/VM, bez prawdziwej przeglądarki). Sprawdzono
  rzeczywisty work.js: odczyt projektu, fokus, pojedynczy POST z checkpointem,
  otwarcie instrukcji, konflikt 409, filtry historii, czyszczenie i polling.
  node --check work.js oraz git diff --check zaliczone. Nie było nieudanych testów.
- Dokumentacja: WORKBENCH.md, LOCAL_INFERENCE.md i centrum pomocy. Dane
  produkcyjne, STATUS.md, procesy/usługi, Windows, modele i GPU nienaruszone.
  Nie wykonywano E2E w przeglądarce ani rzeczywistego pilota Qwen/runnera.
- Dalszy plan pozostaje otwarty: automatyczne wykonanie w zatwierdzonych
  limitach, rozszerzone profile wieloplikowe/zależności, integracje, szersze
  testy i ocena modeli. Nie deklarujemy ukończenia całego planu ani gotowości
  obsługi dowolnego zlecenia na podstawie testów przygotowania instrukcji.

## 2026-09-14 — prowadzenie przez bieżący projekt, bez obciążania wynajmu

- Doprecyzowano zakres po kolejnych wiadomościach właściciela: łatwiejsze
  pierwsze zlecenia nie ograniczają docelowego systemu. Poprzednia interpretacja
  odłożenia wszystkich trudniejszych funkcji była zbyt szeroka; poprawiono
  UPWORK.md i pomoc. Integracje i istniejące projekty pozostają w rozbudowie.
- Rozpoczęto pierwszy wycinek zatwierdzonego planu: istniejące Centrum
  realizacji otrzymało przewodnik „Twój następny krok”. Nie utworzono kolejnej
  roadmapy ani oddzielnej bazy. Pole guidance w szczegółach zlecenia wylicza
  etapy według zapisanej kolejności, odbioru ostatniej próby, delegacji i
  rejestru inferencji. Nie wykonuje modeli ani nie zmienia statusów.
- Rozróżniono brak przydziału, instrukcję, blokady, odbiór, poprawę,
  anulowanie, brak dowodu i niepewne wykonanie. Wszystkie nierozstrzygnięte
  inferencje mają pierwszeństwo przed rekomendacją kolejnego etapu.
  Sam completed ani historyczne verified nie oznaczają odebranego wyniku.
  Odbiór etapów nie oznacza zaliczonych testów paczki ani zgody na wydanie.
- Widok pokazuje etapy i przyciski przenoszące do właściwego zadania,
  przydziału, historii lub plików — bez przepisywania ID i automatycznych
  zapisów. Ładowanie innego projektu prowadzi do przewodnika. Odświeżanie
  nie odbiera fokusu podczas pracy w nim. Wylogowanie czyści jego dane.
  Zachowano istniejące kolory, motywy i obsługę klawiatury.
- Odczyt szczegółów dodatkowo ogranicza zadania do ich projektu; uszkodzone
  powiązanie jest brakującym etapem, nie ujawnieniem zadania innego projektu.
- Testy początkowe: 35 passed / 1.26 s (guidance + work_orders).
  Szersza regresja: 84 passed, 2 deselected / 3.93 s (guidance, work_orders,
  agent_teams, upwork_orders, help_center; bez rzeczywistych pilotów).
  Dodano następnie test API z niepewnym zapisem inferencji; cały plik guidance:
  20 passed. Wszystkie bazy i dane były testowe, model nie był wywoływany.
  Node: test_project_guide.cjs zaliczony (6 scenariuszy z małym symulatorem
  DOM). Kontrole składni work.js/project-guide.js i git diff --check zaliczone.
- Dokumentacja użytkownika: WORKBENCH.md i centrum pomocy. STATUS.md nie
  aktualizowano ręcznie. Nie zmieniano rzeczywistych zadań ani procentów.
- Ograniczenia: nie przeprowadzono kontroli w rzeczywistej przeglądarce ani
  testu z Qwenem/runnerem. Nie restartowano serwera, hosta, Dockera lub Vast.ai,
  nie uruchamiano GPU, pobierania modeli, treningu ani nowych kontenerów.
  Przewodnik nie monitoruje zakończenia najmu. Dalsze użycie modeli czeka
  na jawne potwierdzenie właściciela, nie na niski wskaźnik obciążenia.
- Pozostaje kolejny wycinek: trwała koordynacja wykonania i powrotu po błędzie,
  następnie rozszerzone profile wieloplikowe i testy — z zachowaniem izolacji,
  kontroli kosztu i rozdzielenia wyników modelu od zweryfikowanego wydania.

## 2026-09-14 — prosty start na istniejącym wykonawcy

- Właściciel odłożył trudniejsze integracje i naprawy cudzych projektów:
  najpierw konto Upwork, proste zlecenia i wykorzystanie obecnego profilu.
  Badania rynku pozostają dokumentacją na później, nie aktywnym zobowiązaniem.
- W /os/upwork dodano trzy syntetyczne briefy: kalkulator godzin i stawki,
  przelicznik metrów/centymetrów oraz licznik słów. Każdy zawiera zakres,
  konkretne wyniki, przypadki błędne i ograniczenia python-web-v1.
  Wybór wyłącznie wypełnia formularz; brak API, zapisu, modelu, runnera
  i domyślnego przyjęcia zlecenia. Ćwiczenia mają jawny tytuł i pusty URL.
- Wpisany zakres oraz niepewny zapis wymagają potwierdzenia przed zastąpieniem.
  W trakcie żądania nie można zmienić briefu przykładem. Wybranie nowego briefu
  chowa poprzedni szczegół i wyłącza przycisk analizy starego projektu.
  Zapisane projekty pozostają w historii. Zdarzenie pagehide czyści formularz.
- Dodatkowa diagnostyka API nadal działa, ale jest w zwiniętej sekcji;
  główny widok prowadzi do małego zadania i istniejącego procesu odbioru.
  Uaktualniono UPWORK.md i temat Upwork w centrum pomocy; widoczna uwaga
  o nieuruchamianiu modeli i testów wykonawczych podczas wynajmu Vast.ai.
- Weryfikacja: 8/8 testów Node z małym symulatorem DOM (bez przeglądarki),
  kontrole składni obu plików JS; pytest test_upwork_orders.py oraz
  test_help_center.py -k 'not real': 41 passed, 1 deselected / 1.95 s.
  Model w testach jest atrapą; rzeczywisty pilot pominięty. Nie wygenerowano
  ani nie przetestowano aplikacji z nowych briefów, nie deklarujemy gotowości
  zleceń ani wzrostu postępu. Brak zmian bazy produkcyjnej, GPU, kontenerów,
  usług i procesów wynajmu. Nowego widoku nie sprawdzano w prawdziwej przeglądarce.


## 2026-09-14 — rozszerzona analiza publicznych ogłoszeń Upwork

- Na prośbę właściciela przejrzano siedem kolejnych kategorii: WordPress,
  Shopify, integracje API, analiza danych, mobile, testowanie i wideo AI.
  Przeanalizowano publiczne opisy 20 dodatkowych unikalnych ogłoszeń M9–M28,
  łącznie z poprzednim raportem 28. Nie jest to cały rynek ani próba losowa.
- Zapisano UPWORK_MARKET_EXPANDED_2026-09-14.md i link w pierwszym raporcie:
  źródła, deklarowane budżety, ograniczenia dostępu/kraju/godzin, problemy,
  braki wykonawcy i propozycje dowodów odbioru w istniejących gałęziach.
- Główne wnioski: bezpieczny import i naprawa istniejących projektów,
  niezawodne integracje, jakość danych, profile WordPress/Shopify oraz QA.
  Wskazano możliwość oddzielania diagnozy, implementacji i utrzymania;
  nie prognozowano przychodów na podstawie samych budżetów ogłoszeń.
- Brak zmian aplikacji, danych produkcyjnych, wag i procentów; żaden zakres
  nie dostał fikcyjnej gotowości. Nie wysyłano ofert, nie logowano się,
  nie pobierano załączników, nie omijano ograniczeń. Bez inference, modeli,
  kontenerów, GPU i zmian procesów Vast.ai. Przegląd jednorazowy.
- Zmiany wyłącznie dokumentacyjne; testy aplikacji nie są wymagane.
  Kontrola katalogu źródeł: 20 unikalnych URL-i, komplet M9–M28, brak
  powtórzeń względem pierwszego raportu. Kontrola końcowych białych znaków
  i git diff --check bez błędów.


## 2026-09-14 — wymagania rynku Upwork i diagnostyka kontraktu API

- Na prośbę właściciela sprawdzono publiczne kategorie Automation, Website
  Development, Python i Artificial Intelligence, następnie osiem wybranych
  stron ogłoszeń. Bez logowania, scraperów, obchodzenia ograniczeń, ofert,
  komunikacji i tworzenia przyjętych zleceń. Próbka celowa, nie cały rynek;
  widoczność strony nie potwierdza otwartego kontraktu. Brak ciągłego monitoringu.
- W docs/organization-os/UPWORK_MARKET_2026-09-14.md zapisano źródła,
  etykiety publikacji, własne streszczenia, braki i priorytety przypisane do
  istniejących gałęzi. Nie zmieniono wag ani procentów. Wnioski: integracje
  API i workflow, później profil baz/kont, strony i lokalne AI/RAG; nie obiecujemy
  obsługi Django, WeWeb, Make, Zapier czy desktopu samym profilem stdlib.
- Pierwszy element wykonawczy dla platform.integrations: api-contract-probe.v1.
  Weryfikuje zanonimizowaną próbkę odpowiedzi: deklarowany status, istnienie
  pól, typy, niepuste wartości, listy i obiekty. JSON Pointer według RFC 6901
  (reprezentacja tekstowa z dodatkowymi limitami), bez kodu i URI. Brak pola
  jest odróżniony od null, boolean od liczby; brak pola opcjonalnego ostrzega.
- Owner-only POST /api/upwork-orders/contract-probe, OpenAPI z rozwiniętym
  schematem. Limit strumienia 96 KiB, próbki 32 KiB UTF-8, 12 powiązań,
  wskaźnika 16 poziomów/256 znaków. Kontrola powtórzonych kluczy, głębokości
  i niebezpiecznych liczb. Błędy walidacji nie kopiują wejścia. Odpowiedź nie
  ujawnia wartości próbki; zwraca checksumę, typy, kody i wskazówki.
- Widok diagnostyki w istniejącym /os/upwork, jawne wstawienie syntetycznego
  przykładu i osobne sprawdzenie. Bez localStorage, wykonania HTML i zapisu
  próbek; czyszczenie, edycja i pagehide unieważniają wynik oraz abortują żądanie.
  Wynik nie jest TEST_RESULT i nie może zastąpić bramki wydania.
- Kontrole: początkowo 1 failed, 61 passed, 1 skipped / 2.53 s — test limitu
  UTF-8 używał domyślnego escape ASCII, trafiając w limit 96 KiB (413), zamiast
  zamierzonego limitu próbki (422). Poprawiono kodowanie żądania testowego.
  Dalej 78 passed, 1 skipped / 2.97 s. Końcowo z testami OpenAPI, pomocy
  i sesji: 90 passed, 1 skipped / 3.33 s. Pominięty pilot prawdziwego Qwena.
  Testy DOM: 4/4; kontrola składni JS i git diff --check bez błędów.
- Dokumentacja API/obsługi/limitów w API_CONTRACT_PROBE.md; uzupełniono
  UPWORK.md i centrum pomocy. Narzędzie nie testuje zewnętrznego połączenia,
  CORS, rzeczywistego UI, retry ani działania integracji u klienta. Istniejący
  audyt HTTP może zapisać metodę/ścieżkę POST, nie ciało lub raport z próbką.
- Brak uruchamiania modeli, GPU, kontenerów i przeglądarki. Izolowane lekkie
  testy, bez produkcyjnych zmian statusów, usług, restartów, Windows i Vast.ai.
  Badanie publicznego internetu wykonano przez narzędzie przeglądania;
  nowa funkcja aplikacji sama nie ma dostępu do zewnętrznej sieci.

## 2026-09-14 — kontrola zmian źródeł przed odbiorem

- Dodano porównanie dwóch zweryfikowanych paczek tego samego zadania:
  pliki dodane, usunięte, zmienione i identyczne; metadane rozmiarów/SHA-256.
  Szczegóły pojedynczego pliku odczytywane osobno. Brak nowych tabel,
  artefaktów, statusów, automatycznej akceptacji i wpływu na procenty.
- Nowy owner-only GET comparison z base_id i opcjonalnym path. Obie paczki
  przechodzą dotychczasową kontrolę integralności i przynależności do zadania.
  path jest kluczem manifestu, nie ścieżką hosta. Odpowiedzi bez cache.
- Algorytm różnic ograniczony przed wykonaniem do 16 KiB UTF-8 i 300 wierszy
  na stronę, wyjście do 48 KiB. Duże pliki mają metadane i jawny komunikat.
  Zmiany samych zakończeń wierszy/końcowej nowej linii nie udają identyczności.
- W Budowie i testach: przycisk „Porównaj pliki z wcześniejszą wersją”,
  wybór bazy, stronicowana lista po 20 paczek oraz różnice wybranego pliku.
  Dostępne również po samym odczycie paczki bez wykonania testu. Lista starszych
  ID nie jest przedstawiana jako dowód rodzicielstwa wersji lub poprawności.
- Tekst kodu renderowany bez HTML/eval. Odmowa odczytu czyści stare wyniki;
  zmiana bazy odrzuca spóźnioną odpowiedź dla innego wyboru. Wspólna sesja
  i blokada operacji panelu zachowane. Zaktualizowano wersję zasobu build.js.
- Pierwsze testy: 4 failed, 36 passed / 1.54 s — klient testowy nadpisywał
  base_id przez params przy czterech odczytach szczegółów. Poprawiono budowę
  URL w testach; następnie 40 passed / 1.52 s. Końcowa regresja porównania,
  paczek, pomocy, przekazania i ręcznych kontroli wymagań: 86 passed / 5.36 s.
  Testy kontrolera DOM: 6/6. Składnia obu JS i git diff --check bez błędów.
- Zaktualizowano centrum pomocy i docs/organization-os/EXECUTION.md;
  instrukcja/API/limity w docs/organization-os/PACKAGE_COMPARISON.md.
- Wyłącznie lekkie testy w izolowanej bazie i symulowanym DOM. Bez modeli,
  GPU, kontenerów, testów przeglądarkowych, zmian bazy produkcyjnej, Windows,
  restartów, usług i procesów Vast.ai. Nie kontaktowano się z klientami.

## 2026-09-14 — techniczna metryka wydania dla klienta EN/PL

- Dodano deterministyczne DELIVERY-SUMMARY.md i DELIVERY-SUMMARY.pl.md:
  spis plików, rozmiary źródeł i SHA-256, wersja źródeł/raportu, profil
  zaliczonych testów oraz liczba zweryfikowanych wybranych przykładów HTTP.
  Brak osobnego planu oznacza brak takiego dowodu, nie zero wykonanych testów.
- Dokumenty jasno odróżniają inwentarz techniczny od potwierdzenia funkcji,
  przeglądu wizualnego, pełnego audytu bezpieczeństwa, wdrożenia i odbioru
  klienta. Dodano instrukcję zgłaszania błędów bez sekretów i danych osobowych.
- Metryka nie kopiuje prywatnego briefu, kryteriów, wyjścia programu ani
  szczegółów wejść/odpowiedzi HTTP. Nie sanitizuje jednak istniejących źródeł
  i test-report.json — ich przegląd przed ręczną wysyłką pozostaje wymagany.
- client-handoff.v2 obejmuje cztery dokumenty EN/PL i ich checksumy.
  delivery-summary.v1 udostępnia też dane strukturalne. Metryka trafia tylko
  do zatwierdzonego ZIP-a, nie paczki kandydata. Dokumenty i każde pobranie
  nadal korzystają z aktualnej bramki źródeł, testów i odbioru właściciela.
- Panel przekazania pokazuje podsumowanie i umożliwia podgląd/pobranie
  metryk. Pobranie ponownie odczytuje API, bez eksportowania starego wyniku
  po odmowie. Treść wyświetlana tekstowo; zgodność ze starszym zestawem
  dokumentów zachowana. Zaktualizowano wersję zasobu i centrum pomocy.
- Kontrole: początkowo 34 passed / 5.93 s; końcowa regresja metryk,
  przekazania, bramki akceptacji, generowania, runnera i pomocy:
  62 passed / 7.29 s. Testy DOM panelu: 7/7. Kontrola składni JS i
  git diff --check bez błędów. Osobne bazy, atrapy modeli/runnera/DOM;
  bez rzeczywistego wykonania aplikacji klienta i testów przeglądarkowych.
- Dokumentacja: docs/organization-os/DELIVERY_HANDOFF.md. Bez publikacji,
  kontaktu z klientem, zmian produkcyjnych statusów/procentów/bazy,
  uruchamiania modeli/GPU/kontenerów, restartów usług, zmian Vast.ai i Windows.

## 2026-09-14 — wybrany plan HTTP jako warunek odbioru i wydania

- Analiza ujawniła pozostawioną w poprzednim etapie lukę: cykl napraw
  uwzględniał przypadki HTTP, ale odbiór i bramka wydania ich nie wymagały.
  Wdrożono wspólną usługę acceptance_gate, bez nowej tabeli i migracji.
- Sam zapis szkicu niczego nie blokuje. Ostatni jawny wybór planu do cyklu
  zadania jest wiążący, również po zatrzymaniu cyklu. Nowy cykl bez planu
  nie może go ominąć; zmiana planu wymaga nowego jawnego wyboru i kontroli.
  Zadania bez wybranego planu zachowują poprzedni proces.
- Przed pozytywnym odbiorem: kontrola dokładnych źródeł próby/paczki,
  zakończonego cyklu i testu bazowego, bieżącego zakresu/profilu, pełnego
  zestawu HTTP i każdej odpowiedzi. Wyodrębniono read_saved jako czysty
  odczyt istniejących dowodów — bez fabryki runnera, wykonania i zapisów.
  Sprawdzane są też deterministyczne UUID przypadków danego kroku/cyklu.
- Niekompletne, niezaliczone, obce lub uszkodzone dowody blokują odbiór
  bez zmiany statusu, procentu i audytu decyzji. Odrzucenie do poprawy jest
  nadal dostępne, więc kontrola nie wymusza akceptacji wadliwego wyniku.
- Gotowość pokazuje osobny warunek planu przed odbiorem właściciela.
  Zapis/ponowienie wydania, pobranie zatwierdzonego ZIP i dokumenty przekazania
  ponownie kontrolują dowody. Uszkodzenie raportu po odbiorze blokuje pobranie,
  nie usuwa historycznej decyzji. Paczka kandydata nadal dostępna do diagnozy.
- Raport odbioru i zapis wydania mają acceptance_proof: cykl, plan i jego
  checksumę, wynik i jego checksumę, liczbę przykładów. Referencja trafia do
  delivery.json; nie dodano do wydania prywatnych briefów i logów HTTP.
- Panel odbioru pokazuje ograniczony długością, tekstowy powód odmowy 409
  z API zamiast niejasnego konfliktu. Po odmowie wymagany ponowny odczyt
  próby, nie automatyczne ponowienie decyzji. Formularz planów i potwierdzenie
  startu wyjaśniają skutki wyboru. Zaktualizowano wersje zasobów JS.
- Kontrole: 51 passed / 6.63 s po integracji, 43 passed / 7.33 s z pierwszymi
  testami nowej bramki; rozszerzona regresja 147 passed / 14.48 s. Po dodaniu
  kontroli tożsamości przypadku końcowo 148 passed / 14.67 s, dwa prawdziwe
  piloty wyłączone selekcją. Node: panel odbioru 9/9, plany i cykl 5/5.
  Składnia trzech zmienionych kontrolerów i git diff --check bez błędów.
- Wszystkie testy: osobne bazy i katalogi blokad, atrapy modelu/runnera/DOM.
  Potwierdzono brak dodatkowych wywołań i zapisów podczas odczytu gotowości,
  pobierania ZIP i dokumentów. Bez testów przeglądarkowych/prawdziwej inferencji.
- Dokumentacja: AUTOMATIC_ACCEPTANCE.md i centrum pomocy. Wykonanie nowych
  przypadków pozostaje enabled=false; rzeczywisty pilot nadal oczekuje na
  bezpieczny termin. Wynik przypadków nie oznacza pełnego pokrycia wymagań,
  odbioru klienta, wysyłki do Upwork ani wdrożenia.
- Bez zmian w produkcyjnej bazie, procentach, usługach, procesach Vast.ai,
  GPU, Dockerze, modelach, sterownikach i dysku Windows; bez restartów.

## 2026-09-14 — niezmienne przykłady HTTP i automatyczna pętla poprawek

- Zbudowano owner-only plan 1–4 deklaratywnych przypadków przypisanych do
  kryteriów istniejącego zlecenia. Ścieżka GET, oczekiwany status i opcjonalna
  skalarna wartość pola JSON; bez kodu, poleceń i zewnętrznych URL-i.
- Plan jest addytywnym Artifact SPECIFICATION z SHA-256, UUID, źródłową
  paczką i checksumą całego briefu. Ten sam plan obowiązuje kolejne poprawki
  tego samego zadania/zakresu; model nie może zmienić oczekiwań. Zmieniony brief
  lub niespójne dane blokują użycie. Nie dodano tabeli ani migracji.
- Rozszerzono cykl jakości o opcjonalne ID/checksumę planu. Po zaliczonych
  testach bazowych każdy przypadek używa istniejącej izolowanej ścieżki
  podglądu. Błąd aplikacji przekazywany do naprawy Qwen; nowa paczka sprawdzana
  tymi samymi testami i przypadkami. Limit dwóch poprawek/15 minut pozostaje.
- Raporty przypadków wiążą dokładny run, źródła, profil, odpowiedź i checksumę
  dowodu. Wznowienie nie powtarza zapisanych operacji i kontroluje dowody.
  Awaria infrastruktury/niepewne sprzątanie nie wywołuje zmiany kodu w ciemno.
  Stop sprawdzany także między przypadkami i po ostatniej odpowiedzi.
- Formularz w /os/build dostępny po odczycie paczki, bez jej wykonania:
  „Przygotuj automatyczne sprawdzanie wymagań”. Szkic, zapis niezmiennego planu,
  lista, niepewny zapis z zachowaniem identycznego żądania. Historia cyklu
  rozróżnia testy bazowe, przykłady HTTP i naprawy; pokazuje oczekiwany wynik
  oraz obserwację. Aktualizacja wersji zasobów JS, tekstowy DOM bez innerHTML.
- Nowa konfiguracja config/acceptance_execution.json pozostaje enabled=false.
  Plan można zapisać, ale wykonanie cyklu z planem odmawia przed testem lub
  modelem. Przycisk uruchomienia planu jest wtedy nieobecny. Nie zmieniano
  istniejących przełączników usług. Prawdziwy pilot nowych przypadków wymaga
  końca wynajmu i sprawdzenia izolacji; nie deklarujemy, że już się odbył.
- Wyniki wybranych przykładów nie oznaczają pełnego pokrycia wymagań, ręcznej
  akceptacji, publikacji ani zwiększenia postępu. Istniejąca bramka wydania
  nie staje się automatycznie bramką wszystkich zapisanych planów; tę granicę
  jawnie opisano. Nie modyfikowano prawdziwych zleceń ani procentów działów.
- Testy: pierwsze 56 passed / 4.60 s, po kontroli wznowienia/limitów 90 passed
  / 8.49 s. Końcowy zestaw z help i przekazaniem: 117 passed / 11.05 s,
  dwa rzeczywiste piloty jawnie wyłączone selekcją. Oddzielne bazy, atrapy
  Qwena/runnera, prywatne blokady w katalogach testowych.
- Node: początkowa kontrola nowego zestawu wykazała brak domyślnego textContent
  w atrapie elementu DOM (4/5). Poprawiono atrapę; końcowo 5/5 nowego panelu
  i 5/5 wcześniejszych wymagań, ok. 15 ms i 13 ms. node --check trzech
  zmienionych skryptów oraz git diff --check bez błędów.
- Dokumentacja: AUTOMATIC_ACCEPTANCE.md, powiązania z AUTOMATIC_QUALITY,
  REQUIREMENT_CHECKS, indeks i nowy temat centrum pomocy. Instrukcja zaznacza
  brak rzeczywistego pilota i brak automatycznej wysyłki na Upwork.
- Właściciel dopuścił małe zadania modelowe tylko bez wpływu na wynajem.
  W tym odcinku nie uruchomiono żadnego modelu: nie ma potwierdzonej izolacji
  zasobów od klienta Vast.ai. Bez GPU, kontenerów, przeglądarki, dużych obciążeń,
  pobierania wag, zmian usług/procesów/sterowników, restartów ani dysku Windows.

## 2026-09-14 — wymagania klienta powiązane z wersją i dowodami

- Dodano rejestr weryfikacji kryteriów istniejącego WorkOrder dla niezmiennej
  paczki źródeł: osobny wynik, obserwacja właściciela, opcjonalny raport testów,
  zakres/źródła SHA-256. Nie wprowadzono nowej roadmapy, bazy ani migracji.
- API owner-only GET/POST requirements i odczyt historii z kursorem, po 20
  wpisów. Zapisy addytywne w Artifact, powiązane previous_id, checksumy i audyt.
  BEGIN IMMEDIATE + kontrola poprzedniego ID chronią przed nadpisaniem z drugiej
  karty. Identyczne ponowienie ostatniego żądania nie tworzy duplikatu.
- Raporty z innych paczek/wersji odrzucane. Zmiana źródeł, zakresu lub
  przypisania zadania nie przenosi ocen. Uszkodzone dane dają stan niespójności
  albo 409, nie potwierdzenie. Zwykłe zaliczenie profilu testów nie nadaje
  automatycznie ocen kryteriom. Ocena ręczna nie zamyka zadania/projektu,
  nie zmienia procentu, wydania, publikacji ani odbioru klienta.
- Panel dostępny po odczycie wybranej paczki (bez potrzeby wykonania) oraz
  przy historii testów. Formularz i historia są zwykłym tekstem/DOM; sesja
  właściciela wspólna z resztą panelu. Niepewny zapis zachowuje dokładne
  żądanie do ponowienia; przed zmianą treści należy odświeżyć ocenę.
- Testy początkowe: 17 passed / 1.76 s; pierwsza regresja 64 passed / 4.76 s.
  Po dodaniu historii, obsługi uszkodzonej paczki i kontroli pełnego zestawu ocen:
  66 passed / 5.22 s. Node: 5 passed / ok. 13 ms; node --check i git diff --check
  OK. Izolowana SQLite, atrapy runnera, symulowany DOM, bez rzeczywistych modeli,
  kontenerów, przeglądarki i GPU. Nie zmieniano produkcyjnych zleceń/statusów.
- Jedna wieloplikowa próba patcha odrzucona przez niedopasowany kontekst
  dokumentacji; potwierdzono brak częściowego zapisu i zastosowano poprawny patch.
- Dokumentacja: REQUIREMENT_CHECKS.md, indeks, APPLICATION_FACTORY oraz
  temat „Jak sprawdzić konkretne wymagania klienta?” w centrum pomocy.
  Pozostające granice: to ręczne obserwacje, nie automatyczna analiza pokrycia
  testami; archiwalne deklaracje nie są ponownie weryfikowane przez historię.
  Nie wykonano przeglądarkowego odbioru wizualnego w czasie wynajmu.
- Vast.ai nietknięty. Gemma, inferencja, trening i ciężkie kontrole nadal
  czekają na jawne potwierdzenie końca wynajmu przez właściciela.

## 2026-09-13 — dokumenty przekazania zlecenia podczas aktywnego wynajmu

- Zrealizowano lekki odcinek procesu Upwork: instrukcje klienta PL/EN, szkic
  wiadomości EN i checklista właściciela, oparte na aktualnym zatwierdzonym
  wydaniu python-web-v1. Brak wywołania Qwena, ComfyUI, kontenerów, pobierania
  modeli, przeglądarki czy ingerencji w usługi i procesy Vast.ai.
- Nowy read-only endpoint /api/package-runs/{id}/handoff, kontroler panelu
  Budowa i testy, instrukcje dołączone do wydania ZIP, handoff.json z osobnymi
  checksumami dokumentów. Kandydat bez odbioru nie dostaje instrukcji wydania.
  Odczyt nie tworzy artefaktów, nie zmienia statusu ani nie wysyła klientowi plików.
- Wspólna walidacja zapisu wydania dla gotowości, replay i pobierania:
  aktualny test, dokładne źródła i odebrana próba, SHA raportu/wydania, tożsamość
  uruchomienia i typu artefaktu. Dodano kontrolę kształtu i profilu raportu.
  Testy potwierdziły blokadę po uszkodzeniu źródeł/raportu/wydania lub nowszym
  niezaliczonym teście. Dokumenty nie pobierają prywatnych opisów i promptów.
- Pierwszy zestaw: 39 passed / 2.74 s. Rozszerzona regresja z panelem klienta
  i uwagami: 72 passed / 14.34 s, izolowana SQLite, wyłącznie atrapy modeli
  i runnera. Node: 5 passed / ok. 12 ms, symulowany DOM/API. node --check dla
  delivery-handoff.js i build.js oraz git diff --check: OK.
- Uzupełniono centrum pomocy, DELIVERY_HANDOFF.md, dokumentację Upwork,
  fabryki i indeks. EXECUTION.md teraz jawnie wskazuje bieżącą blokadę wynajmu
  przed historycznymi zgodami. Jedna próba patcha dokumentacji odrzucona przez
  błędny kontekst nagłówka; poprawiona bez utraty istniejących danych.
- Granice: nie wykonano rzeczywistego odbioru wizualnego ani uruchomienia
  instrukcji klienta na Windows/macOS. Instrukcja jest dla profilu, nie stanowi
  testu wymagań klienta ani audytu źródeł. Stare pobrane ZIP-y nie zmieniają się;
  nowe bajty ZIP-a obejmują dokumenty, SHA źródeł pozostaje osobną sumą.
  Gemma/porównania/trening nadal wstrzymane do decyzji właściciela.

## 2026-09-13 — ponownie aktywny wynajem Vast.ai, prace modelowe wstrzymane

- Właściciel poinformował, że GPU jest znowu wynajmowane i nie wolno ruszać
  wynajmu. Zaktualizowano nadrzędne AGENTS; poprzednia zgoda na obciążenie
  przestaje obowiązywać do kolejnego jawnego potwierdzenia.
- Przerwano wyłącznie własne pobieranie `ollama pull gemma4:31b` przez Ctrl+C.
  Nie usuwano częściowych wag. Nie uruchomiono inferencji Gemmy ani porównania
  modeli i nie rozpoczęto treningu. Nie zatrzymywano Vast.ai, Docker, Ollamy
  ani hosta w odpowiedzi na tę informację.
- Przed nową informacją zakończono test integracji ComfyUI i zwolniono jego
  nieużywaną pamięć przez /free po sprawdzeniu pustej kolejki. Usługa pozostała
  uruchomiona. Nie powtarzać takich operacji podczas bieżącego wynajmu.
- Przygotowano compare_local_models.py (4naprawy,12decyzji), dokumentację
  MODEL_COMPARISON.md i profil ustawień Gemmy. Testy porównywarki/adaptera/
  katalogów:47passed/0.93s, bez uruchamiania modeli. Pobranie/ocena/ewentualne
  przypisanie Gemmy do ról pozostają jawnie niewykonane, nie oznaczone sukcesem.

## 2026-09-13 — grafika powiązana z zadaniem i odbiór właściciela

- Dodano model MediaGeneration i migrację addytywną, stały adapter lokalnego
  ComfyUI, API właściciela, panel /os/media, linki z zadań, wyszukiwarkę i pomoc.
  Artefakty zawierają obraz/raport/hash i zachowują przypisanie do projektu.
  Wspólny slot DB z Qwenem, UUID przed POST, brak automatycznego ponawiania,
  kontrola PNG i usuwanie metadanych; osobny odbiór bez zamykania zadania.
- Nie uruchamiano Qwena do deterministycznego grafu i walidacji. Brak pobrań
  modeli/nodes, publikacji lub zmian prawdziwych statusów i projektów.
- Sandbox zatrzymał pierwszy TestClient bez wyniku: przerwano tylko własne
  testy i powtórzono po zgodzie poza sandbox. Naprawiono też fixture lifespan:
  main.engine wskazuje izolowaną bazę testową, nie aplikacyjną.
- Testy wykryły kolejność pomocy i licznik linków oraz niezatwierdzone zadanie
  w fixture blokady GPU; poprawiono. Końcowa regresja94passed/3.77s,
  node --check i git diff --check OK. Jedna próba apply_patch odrzucona przez
  niedokładny kontekst; poprawiona bez nadpisania zastanych zmian.
- Chrome prywatny bez GPU, wszystkieAPIatrapy: /tmp/ai-media-browser-nk3uqafw,
  passed sesja/podgląd/odbiór/jednoPOST/tekst/390+768px/jasny+ciemny.
  Po kontroli zrzutu poprawiono również odświeżanie podpisu odbioru obrazu.
- Pierwszy realny pilot integration-check-4uq7b6sa nieudany: starsze ComfyUI
  nie widziało wag. Dodano kontrolę nazw modeli przed wysłaniem i rozróżnienie
  jawnego odrzucenia400 od niepewnego transportu. Brak wyniku nie był sukcesem.
- Po odczycie argv/pustej kolejki i zgodzie zatrzymano wyłącznie PID2790142
  ComfyUI bez konfiguracji modeli; uruchomiono aktualny launcher na8188.
  Nie restartowano innych usług/hosta. Następny pilot integration-check-wh4upiem:
  passed,18.402s, obraz w artefakcie izolowanego zadania, status niezmieniony.
  PNG obejrzany przez asystenta, zgodny z opisem; raport automatyczny niemodyfikowany.
- Pozostające granice: bez publikacji klientowi, automatycznego składania
  obrazów do aplikacji i bez scheduler'a wszystkich procesów GPU; cache modeli
  ComfyUI może pozostać po ukończeniu. Niepewna utracona historia wymaga diagnostyki.
- Właściciel dodał Gemma4 31B do oceny. Zweryfikowano oficjalną kartę Google
  i lokalny wariant Ollama gemma4:31b (Q4_K_M,20GB). Ocena/instalacja dopiero
  po domknięciu tego etapu; modelu produkcyjnego Qwen nie zmieniano.

## 2026-09-13 — pierwsza rzeczywista generacja ComfyUI, bez dodatkowych instalacji

- Właściciel potwierdził start ComfyUI i dopuścił potrzebne modele/nodes.
  Najpierw zweryfikowano istniejący Z-Image Turbo i oficjalny lokalny szablon.
  Nie było potrzeby pobierania wag, rozszerzeń ani używania płatnych API/Qwena.
- Dodano check_comfyui_generation.py: jeden stały graf10natywnych węzłów,
  768×512,8kroków,seed20260913,limit300s; własny proces8189 i katalog Linux.
  Kontrola aktywności istniejącego ComfyUI/Ollama, bez ich zatrzymywania.
  To test inferencji, nie sandbox bezpieczeństwa ani scheduler GPU.
- Próba przeszła: 22.079s od wysłania do odbioru, 25.856s łącznie;
  własny proces zakończony. Raport/log/graf/PNG: comfyui/generation-check-lsrce_nu.
  SHA256 PNG cca1e19ed018d9e573c10fe741d0c88504e84b46840bd819d53ba2f59bfe8fe5.
  Po automatycznej walidacji asystent obejrzał obraz: niebieska szklana kula,
  jasny postument, spójny wynik zgodny z opisem; surowy raport pozostawiono bez zmian.
- Zapisano workflowUI w config/comfyui-workflows oraz w katalogu workflow
  użytkownika ComfyUI; nie zastąpiono jego otwartego płótna ani nie dodano
  zadania do jego kolejki. Weryfikacja UI na razie statyczna, generacja przez API.
- Pierwsze testy skryptu/launchera:19passed/0.40s; git diff --check OK.
  Po dodaniu testu parametrów eksportowanego workflow:20passed/0.40s,
  git diff --check OK, findmnt ponownie potwierdził Windows tylko do odczytu.
  Dokumentacja COMFYUI.md
  opisuje dowody, obsługę i ograniczenia. Nie zmieniano DB/statusów, Windows,
  innych usług ani danych klientów. Integracja z realizacją zleceń pozostaje do budowy.

## 2026-09-13 — współdzielone wagi Windows w lokalnym ComfyUI

- Po potwierdzeniu właściciela dodano config/comfyui-model-paths.yaml oraz
  argument launchera. Wyłącznie katalogi wag; bez custom_nodes, kopiowania,
  pobierania, zapisu na Windows, zmian partycji lub rozruchu. is_default:false
  zachowuje domyślne katalogi na Linuksie. AGENTS precyzuje zgodę na ten odczyt.
- Launcher kontroluje źródło/miejsce/ro istniejącego magazynu; odmawia użycia
  zapisywalnej partycji. Brak montowania jest raportowany, bez automatycznego
  podłączania dysku. Nie restartowano aktywnego ComfyUI ani procesów użytkownika.
- Odczyt Safetensors bez ładowania tensorów: FLUX Klein Base4B fp8
  4089498488B/305tensorów; qwen_3_4b8044982048B/398; flux2-vae336213556B/251.
  Bez sprawdzania pochodzenia wag/pełnych checksum; to nie test generowania.
- Realny check_comfyui_installation --run --shared-models: passed, 3nazwy
  widoczne w API,0cloud nodes,pusta kolejka,własny proces na8189 zakończony.
  Raport comfyui/install-check-8fbyrre0/report.json; logSHA256
  61b4c3fe668706fef4d8c2bede485a6e9b16638bd13b035b64160b20bcd8c95a.
- Testy10passed/0.21s,git diff --check OK. Zaktualizowano COMFYUI.md.
  Generowanie obrazu oraz integracja z zadaniami firmy pozostają niewykonane.

## 2026-09-13 — odnalezienie istniejących modeli na Windows, tylko odczyt

- Właściciel zaproponował współdzielenie istniejących wag z drugim dyskiem,
  zachowując Windows jako osobny uruchamialny system. Po jawnej zgodzie
  narzędzia podłączono wyłącznie /dev/nvme0n1p4 przez udisksctl z opcją ro.
  findmnt potwierdził ntfs3,ro,nosuid,nodev pod /media/marcin/Windows.
- Ograniczone wyszukiwanie nazw plików modeli (bez wykonywania kodu Windows)
  odnalazło /media/marcin/Windows/Users/kusmi/Desktop/Comfy UI/models.
  Nazwy wskazują m.in. SDXL, Z-Image, Qwen Image/Edit, FLUX Klein, Wan i LTX.
  To identyfikacja nazw, nie weryfikacja wag, kompletności, licencji lub inferencji.
- Brak zapisu na Windows, zmian EFI/bootloadera/partycji/fstab/autostartu,
  formatowania, kopiowania lub pobierania modeli. Nie zmieniono jeszcze
  konfiguracji wyszukiwania modeli ComfyUI. Partycja pozostaje podłączona
  tylko do odczytu na tę sesję. Dawny zakaz używania Windows został wyjątkiem
  wyłącznie dla uzgodnionego odczytu magazynu modeli, nie dla plików projektu
  ani zapisu nowych modeli na NTFS.

## 2026-09-13 — skrót ComfyUI na pulpicie

- Dodano /home/marcin/Pulpit/ComfyUI.desktop z własną ikoną SVG i uprawnieniem
  wykonywania. Poprawna składnia desktop-file-validate.
- open_comfyui.py: lokalna kontrola gotowości, start przez istniejący launcher,
  blokada flock dziedziczona przez serwer, log i otwarcie przeglądarki po starcie.
  Brak drugiego procesu przy kolejnym kliknięciu; obcy zajęty port nie jest
  zwalniany ani jego proces zatrzymywany. Brak automatycznego generowania.
- GIO metadata::trusted nieobsługiwane także poza sandbox: ewentualne
  zatwierdzenie skrótu należy do pulpitu użytkownika. Nie zmieniono globalnych
  ustawień zaufania. Nie otwierano przeglądarki użytkownika podczas testów.

## 2026-09-13 — lokalne ComfyUI, bez płatnej chmury

- Właściciel ponownie wykluczył płatne modele chmurowe i zaproponował ComfyUI.
  Nie podłączono kluczy, płatnych usług ani danych klientów. Sprawdzono oficjalne
  źródła: ComfyUI obsługuje lokalne modele, ale także API nodes, które wyłączamy.
- Oficjalne ComfyUI0.35.0 commit19e1058f4c445ef74047e77a23f9ca7684c1e4b6
  zainstalowano w ai-company-workspaces/comfyui, z osobnym venv. Pierwszy git
  clone nieudany przez DNS sandbox; po zgodzie udany. Instalacja zależności
  z PyPI/oficjalnego indeksu PyTorch: sukces, pip check bez konfliktów.
  Snapshot config/comfyui-environment.lock.txt. Brak restartów i zmian sterowników.
- start_comfyui.py: tylko127.0.0.1:8188, przypięty commit, custom/API nodes
  wyłączone, tryb HF offline. To nie izolacja sieciowa ani pełny sandbox.
- Realny test check_comfyui_installation.py na8189: passed, RTX5090 widoczna,
  HTTP interfejsu oraz system_stats/object_info/queue działają;660natywnych
  węzłów,0cloud nodes,pusta kolejka. Własny proces zakończony. Raport
  ai-company-workspaces/comfyui/install-check-ux8bpgyj/report.json. Ostrzeżenia
  torch.jit/ustawień serwera/opcjonalnego OpenGL_accelerate, brak błędów startu.
- Testy launcher + role evaluation + training_data:50passed/1.10s.
  Dokumentacja: docs/organization-os/COMFYUI.md. **Bez pobranych wag,
  generowania modelu, automatycznego adaptera do projektów i zmiany postępu.**
  Kandydat pierwszej próby: FLUX.2 Klein4B, licencja Apache2.0 według producenta;
  nie deklarowano zmierzonej jakości/wydajności ani licencji wszystkich składników.
- Z wcześniejszej części tury: przygotowano zamrożone12syntetycznych przypadków
  decyzji4ról, skrypt evaluate_qwen_roles i blokadę ich rodzin/promptów w treningu.
  100testów roli/repair/training przeszło2.04s. Pomiar modelu NIE uruchomiony;
  prace przekierowane na pytanie o modele i lokalne multimedia. Nie utożsamiać
  zaliczonych testów programu z oceną jakości odpowiedzi modelu.

## 2026-09-13 — poprawki pojedynczych plików i plan porównania modeli według ról

- Dodano wewnętrzny python-web-repair-v1: schemat changes,1–2 istniejące
  pliki, brak test_app.py, nowych/usuwanych/pustych/niezmienionych plików.
  Walidacja podwójnych kluczy, ścieżek, kompletności i limitu32000znaków
  złożonego wyniku. Składanie wyłącznie danych w pamięci, bez hostowego
  wykonania kodu. Baza pochodzi z odrzuconej wersji powiązanej checksumą
  instrukcji; po inferencji ponownie sprawdzane są stan i zakres zadania.
- Nowe automatyczne cykle korzystają z tego profilu; starsze (pełne źródła
  i locked-test-schema.v1) pozostają zgodne. Ręczne API poprawek nie rozszerza
  dozwolonych pól ani uprawnień. Artefakt poprawki wiąże profil z inferencją.
- Zachowano pełny złożony wynik dla istniejącego odbioru/paczek. Surowy JSON
  zmiany ma oddzielny artefakt i SHA256. metrics.assembly zawiera zmienione
  i zachowane pliki, checksumy bazy/testów oraz ID surowej odpowiedzi.
  Nie udajemy, że całe złożone źródło to nowa odpowiedź modelu. Nieprawidłowy
  patch zapisuje dowód invalid_file_repair, bez nowej paczki i TaskAttempt.
- Historia Qwen w work.js pokazuje zmienione pliki, dane dowodu oraz przyczynę
  odrzucenia; rozróżnia złożony wynik od surowej odpowiedzi. node --check OK;
  w tej turze nie wykonano wizualnego odbioru zmienionego panelu.
- Testy izolowane:55passed/2skipped początkowo,121/3 po integracji,47/2 dla
  diagnostyki,124passed/3skipped/9.16s po testach zgodności starszych cykli
  i zmiany zakresu podczas inferencji. Testy obejmują odrzucenie zmian testów,
  puste/niezmienione/obce pliki, duplikaty JSON, za duży wynik, historię
  surowej odpowiedzi, brak częściowej paczki, idempotencję i stare dekodery.
- Realny pilot application-delivery-pilot-nsfhme9i:43.01s, końcowo
  needs_attention. Qwen poprawił tylko index.html w11.562s/840tokenów,
  zachowując3inne pliki. Pozostał pusty discount=; druga odpowiedź była
  nieprawidłową poprawką. Na tym etapie brak szczegółowego surowego dowodu
  porażki — ta obserwacja doprowadziła do dodania jego zapisu.
- Realny pilot application-delivery-pilot-r0hqrhcw:47.11s,limit_reached.
  Poprawki HTML12.001s/1098tokenów iapp.py11.346s/822tokeny. Wszystkie
  odpowiedzi miały faktycznie zmienione pliki i zachowane testy, lecz API
  nadal zwracało200zamiast400dla pustego discount=. Nie odebrano rezultatu.
- Doprecyzowano ogólną instrukcję napraw HTTP: sprawdzić parser przed
  walidacją, bo może odrzucać puste parametry. Nie zmieniono testów ani
  kryteriów na korzyść modelu. Nie zwiększono limitów/praw/dostępu Qwen.
- Pilot application-delivery-pilot-d1qoyzrn:44.15s,passed. Początkowa generacja
  22.173s/2902tokeny; poprawki wyłącznie app.py9.603s/892tokeny oraz
  9.724s/896tokenów. Dwa nieudane testy, potem zaliczony zestaw z14niezależnymi
  próbami HTTP i kontrolami HTML oraz izolacji. Testy, README iHTML zachowane.
  Źródła końcowe przeczytano: parser keep_blank_values=True i rozróżnienie
  braku/pustej wartości. Nie wykonano Chrome dla tej wersji. Powstał ZIP
  kandydata, owner_accepted=false,published=false, postęp testowego zadania0.
  Raport SHA256:a8958c3d271f6b76c5da1fa2f497ec24e68a8234c6e33d743c80ef25b373cd68.
  Wszystkie3serie są syntetyczne w osobnych bazach; nie modyfikowano zadania45
  ani paczki5. Sukces jednej powtarzanej specyfikacji nie jest benchmarkiem
  ogólnej jakości ani skuteczności treningu.
- Właściciel zaproponował porównanie Qwen/QLoRA i dobór według funkcji.
  Zweryfikowano raport smoke-bui0t39x:3kroki,4krótkie przykłady arytmetyczne,
  production_ready=false,quality_improvement_measured=false. Wyjaśniono,
  że QLoRA to metoda dostrajania, nie drugi model. Sprawdzono dokumentację
  PEFT kwantyzacji. Dodano MODEL_ROLE_EVALUATION.md: baza vs baza+adapter
  w tym samym runtime/kwantyzacji, oddzielne role i niezależne kryteria,
  jakość przed szybkością, bez automatycznej promocji. Porównanie właściwego
  adaptera firmowego NIE zostało wykonane; adapter taki jeszcze nie powstał.
  Nie zmieniono routingu, modeli Ollamy, wag ani zbiorów treningowych.
- Zaktualizowano AUTOMATIC_QUALITY,APPLICATION_FACTORY,QWEN_TRAINING.
  Raporty i źródła zachowano w Linux workspace, sprzątane były wyłącznie
  własne kontenery/katalogi wykonania. Brak restartów hosta/usług i zmian Windows.
  Kontrola końcowa:lista runnera pusta,Ollama models=[],overviewHTTP200/0.045812s.

## 2026-09-13 — pełne pliki Qwen, niezależny odbiór i blokada testów w dekoderze

- Przejście z małych funkcji do świeżej aplikacji: syntetyczny kalkulator
  wyceny z rabatem, osobna baza i zadanie, rzeczywisty Qwen oraz dotychczasowy
  runner. Bez zmian prawdziwego zadania45/paczki5 i bez publikacji/odbioru.
  Zastane scripts/check_application_delivery.py oraz test pilota wykorzystano
  ponownie, bez fabrykowania ukończenia analizy lub projektu klienta.
- application_profile.py: jawny SOURCE_SCHEMA czterech wymaganych i dwóch
  opcjonalnych plików. local_inference przekazuje go tylko dla profilu aplikacji.
  Doprecyzowano zwięzłość instrukcji, bez usuwania wymagań i zwiększania
  budżetu4096. Nie zmieniono modelu/digestu, konfiguracji ani wag Qwen.
- Pierwszy przebieg application-delivery-pilot-hkopdgg3:40.12s, porażka
  truncated_output, bez częściowej paczki. Po zmianie schematu/instrukcji
  application-delivery-pilot-brypj4_z:36.67s, passed dla dziewięciu testów autora
  i 13 niezależnych prób API. Utworzono ZIP kandydata, owner_accepted=false.
  Późniejszy przegląd wykazał pominięte file://, użycie innerHTML oraz
  discount= traktowane jak brak parametru. Wcześniejszy sukces nie jest
  pełnym odbiorem; nie zmieniano historycznego raportu ani kandydackiego ZIP.
- Rozszerzono niezależny tester pilota do14 prób HTTP oraz tekstowych kontroli
  HTML (innerHTML, file:). Te kontrole są specyficzne dla tego briefu, nie są
  pełnym audytem JS/wyglądu i nie potwierdzają działania ostrzeżenia file://.
  Zwykła konfiguracja testera aplikacji nie otrzymała tych szczególnych prób.
- application-delivery-pilot-g_f5v8jo:99.27s, porażka nowej kontroli file://.
  Dwie poprawki Qwen zmieniły zamrożone test_app.py; kontrola nie uruchomiła
  testów zmienionego zestawu. Powtórzone źródła zakończyły cykl needs_attention.
- application_quality.py: nowe cykle zapisują repair_decoder=locked-test-schema.v1.
  JSON schema zawiera const z oryginalnym test_app.py; sprawdzana jest jego
  suma i limit schematu16KB. Nie podmieniamy odpowiedzi modelu po generacji.
  Niezależna kontrola checksumy po odpowiedzi nadal obowiązuje, w tym dla
  dostawcy ignorującego schema. Starsze cykle zachowują swój dekoder.
- application-delivery-pilot-dk2rs007:83.65s. Const zadziałało: testy zachowane,
  pierwsza poprawka zaliczyła wcześniejszą tekstową kontrolę HTML. Kolejny
  test wykazał HTTP200 zamiast400 przy pustym discount=. Druga poprawka
  powtórzyła źródła; needs_attention, brak nowego ZIP i odbioru. Raport SHA256:
  382b05bf42654807b17cf53b710992bfad9690cc38880180d1b53092720aef61.
- Dodano failure_feedback: przyczyny errors przed ogólnym logiem, ograniczona
  końcówka testów, zachowana pełna wersja w PackageRun. Dane programu nadal
  niezaufane. Nie zastępuje to diagnozy ani nie podnosi uprawnień Qwen.
  application-delivery-pilot-fn_4i71j:58.17s, własne10testów OK, niezależna
  kontrola innerHTML FAIL; model powtórzył źródła. Cykl needs_attention, nie
  oznaczono go jako sukces. Raport SHA256:
  213cab68a6eaaffc9025068472b7e1dd185d3cbead4a7168fa01915d595eff5f.
  Nie jest to ślepy benchmark: w trakcie zmieniano proces/kryteria, więc
  nie wyliczamy skuteczności modelu z tych pięciu prób.
- scripts/check_delivery_browser.py: oddzielny loopback, syntetyczne ID/token,
  istniejąca opaque ramka i PreviewRunner, osobny profil Chrome bez GPU.
  Tylko raporty z workspace Linux; brak czytania prawdziwych zadań/zapisów
  PackageRun. Pliki Pythona tylko w kontenerze, JS tylko w ramce, najwyżej8
  żądań podglądu. Report hash jest lokalnym powiązaniem, nie produkcyjną
  checksumą paczki. Offline testy walidacji ścieżek i przyczyn porażek dodano.
- Browser delivery-browser-pdoppak_:passed, na wcześniejszym kandydacie brypj4_z:
  kliknięcie8×322,rabat10→2318.40; pusty rabat pominięty przez formularz→2576.00;
  ujemne godziny zablokowane przed requestem; parentDOM/storage/externalfetch
  niedostępne, zamknięcie usuwa ramkę. Trzy kontenery, cleanup potwierdzony.
  Raport SHA256:516c902f220f1b66a7c2e1b70ca9e14e87b25f06a85717c041cbf5f406367f49.
  Ten pozytywny audyt nie usuwa braków znalezionych w pełnym kontrakcie.
- Powtórzenie końcowej wersji skryptu, delivery-browser-wz8dwkb3:passed,
  3requesty/3cleanup, jawne flagi blokady sieci i syntetycznego powiązania.
  SHA256:515a446371755d97a09259161d4c041f256312285b70e87eb07d6349d678e172.
  Po tym przebiegu lista kontenerów runnera także pusta.
- Regresje:25passed/3skipped przed zmianą dekodera; następnie27/3,47/3,48/3;
  szerszy końcowy przebieg104passed,3skipped/7.67s. Pominięte próby wymagają
  jawnego opt-in realnego modelu/kontenerów. git diff --check i py_compile OK.
  Sandbox nie ma dostępu do lokalnego Ollama/Dockera; rzeczywiste próby
  wykonano po eskalacji, bez obchodzenia ograniczeń.
- Kontrola końcowa przed powtórzeniem raportowania przeglądarki: kontenery
  runnera brak, Ollama models=[], overviewHTTP200/0.041454s. Nie restartowano
  serwera, usług, hosta ani nie dotykano Windows. Usunięto tylko własne
  tymczasowe kontenery/katalogi wykonania/profil Chrome; raporty, źródła,
  testowe bazy oraz ZIP zachowano w Linux workspace.
- Dokumentacja APPLICATION_FACTORY, AUTOMATIC_QUALITY i QWEN_TRAINING
  zaktualizowana. Nie trenowano ponownie i nie dopisywano tych odpowiedzi do
  approved train/holdoutu. Następny krok: wąska poprawka konkretnych plików
  i kontrola rzeczywistej zmiany, zamiast kolejnej pełnej regeneracji.

## 2026-09-13 — oddzielna ocena bazowego Qwena przed dostrojeniem

- Dodano zamrożony datasets/qwen/evaluation/repair-suite-001.json: cztery nowe
  rodziny (CSV, suma przedziałów, query formularza, średnia ruchoma), autorskie
  kontrakty, wadliwy kod i testy ustalone PRZED inferencją. Hash suite:
  fb5f375568d738d238d8f5a9cc5a33923b82cea1150780d884835bab7a7ce41d.
  To jawny syntetyczny zestaw regresyjny, nie prywatny końcowy holdout.
- scripts/evaluate_qwen_repairs.py uruchamia po jednej próbie modelu,
  najpierw potwierdza realną porażkę kodu wejściowego, następnie niezmienione
  testy poprawki w istniejącym runnerze. Bez --run nie uruchamia modelu.
  Nie eksportuje przykładów SFT, nie trenuje, nie czyta klientów ani zadań.
  Niepełna infrastruktura ma pass_rate=null, a nie pozorny wynik jakości.
- scripts/qwen_evaluation_catalog.py sprawdza hash; prepare_training_data.py
  blokuje rodziny oceny i dokładne briefy (również z innym wrapperem) w train
  oraz validation. Brak/zmiana katalogu blokuje walidację. Kontrola nie wykrywa
  wszystkich parafraz i nie zastępuje przeglądu rodzin przez recenzenta.
- Sandbox: repair-evaluation-pw_lwtq9 zakończone na etapie baseline
  infrastructure_error,0assessed,bez inferencji. Po eskalacji pełna seria
  repair-evaluation-49tzsib6:45.374s,4/4passed,24 metody unittest plus przypadki
  parametryczne. Model bazowy qwen3.8:27b i przypięty digest bez zmian,
  temperature0.2,context16384,num_predict1200,threads8,thinkfalse,timeout90s.
  Bez kolejnych prób i dostrajania po wyniku. Przeczytano wszystkie cztery
  poprawki; brak odczytu testów i efektów ubocznych poza czystymi obliczeniami.
- Osiem kontenerów z ograniczeniami istniejącego runnera, brak sieci/GPU
  w gościu, testy przed/po i kontrola sprzątania zaliczone. Zaufana atrapa
  HTTP nie stanowi aplikacji wygenerowanej przez model. Kontenery tymczasowe
  usunięto wyłącznie po własnych ID/etykietach; źródła i raporty zachowano.
- Surowy raport SHA-256:
  e86c0c20a93fc10f6994708d40e276685da28c6c9b5ec8d6c1689e8a3295d6f6.
  Kopia JSON datasets/qwen/evaluation/baseline-001.json (inne formatowanie):
  1a37f1f4802bee6680b079fcb4dc725a8f81cab3ed4fc8f91b7f76f004884be2.
  Test archiwum sprawdza źródła, suite, hashe testów, rzeczywiste wiadomości,
  raporty przed/po i licznik. Podczas przyszłego porównania trzeba odtworzyć
  te same wiadomości, nie logi z innymi czasami. Porównywarka adaptera nie
  została jeszcze wdrożona; obecny evaluator jest przypięty do bazy.
- Kontrole:79passed/1.58s dla pierwszego zestawu; końcowy szerszy przebieg
  w sandboxie zawiesił się przy testach TestClient. Odczytano dokładną
  tożsamość i zakończono tylko własny pytest PID2596212 (nie serwer).
  Powtórzenie poza sandboxem:105passed/2.37s, z diagnostyką timeoutu30s.
  Nie zaliczamy wcześniejszego przerwanego przebiegu. git diff --check OK.
- Docker lista runnera pusta, Ollama models=[], overview HTTP200/0.043015s.
  Nie zmieniano rzeczywistej bazy, statusów, modeli, usług i dysku Windows.
  Zaktualizowano dokumentację danych i QWEN_TRAINING.md. Nadal12train,
  0validation,0odebranych SFTtest; osobno4próby oceny. Baza już zalicza te
  małe ćwiczenia, więc wynik nie dowodzi korzyści z QLoRA. Następna ocena
  powinna objąć trudniejsze, wieloplikowe realizacje i zgodność API/UI.

## 2026-09-13 — Qwen naprawia kod do zbioru specjalizacji, niezależne testy

- Dodano scripts/draft_repair_examples.py: trzy autorskie syntetyczne kontrakty,
  wadliwe fixture i niezależne testy zapisane przed inferencją. Bez --generate
  nie uruchamia modelu ani kontenera. Qwen może dostarczyć tylko solution.py;
  brak hostowego exec/import wygenerowanego kodu. Stały model/digest, JSON
  schema, max1200 tokenów/90s, jedna propozycja na przypadek, przerwanie po
  niepowodzeniu, brak automatycznego zatwierdzania i treningu.
- Wykorzystano istniejący ContainerRunner bez zmiany jego konfiguracji:
  przypięty obraz, runc, brak sieci/GPU, read-only, non-root, seccomp/AppArmor,
  1 CPU/512MiB/64PID/45s. Zaufana atrapa HTTP umożliwia użycie istniejącego
  harnessu; nie jest aplikacją klienta ani rezultatem Qwena.
- Pierwsza próba repair-drafts-tl7vh2sa w sandboxie zakończyła się ValueError
  przed wynikiem runnera i inferencją (0 kandydatów). Po eskalacji wykonano
  repair-drafts-hhdqqsrn:15.543s,3/3 kontrole pozytywne. Przegląd źródła
  wykazał brak walidacji items w paginacji mimo kontraktu; test również nie
  obejmował tego warunku. Nie przyjęto tej pierwszej partii do zbioru.
- Dodano test_invalid_items bez osłabiania kontraktu. Druga seria
  repair-drafts-gzqzpcrx,synthetic-repair.v2:14.763s,3/3. W każdej parze
  wadliwa wersja miała rzeczywiste FAIL, poprawiona zaliczyła testy.
  Łącznie 13 metod unittest plus przypadki parametryczne/własności:
  paginacja5,format czasu3,deduplikacja5. Źródła drugiej serii przeczytano;
  poprawki są ogólne, bez introspekcji testów, importów i efektów ubocznych.
  Qwen sam dodał brakującą walidację; jego trzech końcowych odpowiedzi nie
  edytowano. Nie są to testy UI, pełnych aplikacji ani skuteczności QLoRA.
- datasets/qwen/repair-batch-001.jsonl:3 train/repair approved przez
  assistant-independent-code-review. Dowód JSON zawiera pełne przed/po,
  testy, źródła, sumy i kontrolę izolacji. Jego SHA-256:
  770d8a3cf7f977188cba05a6c5909b7646c86d43aaf3b0cf06b5565204fc3b1c.
  Raport surowy drugiej serii SHA-256:
  0ef9bc7394f673e026a93927555b9ef60f5561e5cc98f125a1fd668e2a8626c5.
  Sam zbiór SHA-256:
  962a25312f16a2ad8a0135bd2653d85e4066704659338261745ee0203e4b626c.
- Testy narzędzi:65passed początkowo,85passed po rozszerzeniu,końcowo
  90passed/2.07s (laboratorium, dane, propozycje, Ollama, jakość, QLoRA smoke
  bez GPU, runner). Weryfikują także powiązanie odebranych źródeł, testów,
  raportów i hashy oraz brak automatycznego odbioru. git diff --check OK.
  --require-ready zwraca oczekiwany kod2: mały zbiór, brak walidacji/holdoutu.
- Łącznie z poprzednią partią:12 approved train,0 validation,0 test.
  To przygotowanie danych, nie wdrożenie modelu firmowego ani aktualizacja
  wag. Zaktualizowano README zbioru i QWEN_TRAINING.md.
- Obie rzeczywiste serie usunęły wyłącznie własne 12 tymczasowych kontenerów
  i katalogi wykonania. Źródła i raporty zachowano; docker ps z etykietą
  runnera jest pusty. Ollama /api/ps:models=[], overview HTTP200/0.045366s.
  Bez zmian produkcyjnej bazy/zleceń, usług, modeli, sterowników i Windows.

## 2026-09-13 — pierwsze odebrane przykłady specjalizacji z pomocą Qwena

- Dodano scripts/draft_training_examples.py: dziewięć autorskich syntetycznych
  przypadków, oczekiwane decyzje określone przed inferencją, schematy odpowiedzi,
  stały lokalny model/digest, bez narzędzi, bazy klientów i automatycznego odbioru.
  Wszystkie nowe propozycje mają split=train i review=pending. Bez --generate
  skrypt nie uruchamia modelu. Zapisuje również niezaliczone odpowiedzi.
- Pierwsza próba w sandboxie nie miała dostępu do lokalnego socketu; po
  eskalacji wykonano serię drafts-76k45nv8,74.065s,8/9 kontroli format/decyzja.
  Rzeczywisty przegląd wykazał dodatkowo angielski język mimo instrukcji,
  niepełny acceptance_case licznika oraz zbyt wczesny plan uploadu. Przy zmianie
  checksumy model sugerował sensowne ponowne testy, lecz wybrał niezgodne
  WAIT_FOR_EVIDENCE zamiast RETEST. Wyników nie dopisano do zatwierdzonego zbioru.
- Instrukcja synthetic-specialization.v2 doprecyzowuje język, CLARIFY,
  kompletność przypadków i pierwszeństwo RETEST. Nie zmieniono oczekiwanych
  etykiet ani produkcyjnych instrukcji agentów. Dodano testy wychwyconych braków.
- Druga seria drafts-h53mwtj4,46.935s,9/9 kontroli. Przeczytano wszystkie wyniki.
  Cztery odpowiedzi dopracowano: skończoność liczb, Unicode i jednoznaczne
  wejścia testowe, pytanie o obowiązkowy POST zamiast przesyłania plików w URL,
  wiązanie dowodów z checksumą zamiast samym tagiem. Pięć zachowano treściowo.
- datasets/qwen/specialization-batch-001.jsonl:9 approved przez niezależny od
  lokalnego Qwena przegląd asystenta. Nie jest to zatwierdzenie właściciela,
  klienta lub gotowości aplikacji. Raport przeglądu i jego hash przypisano
  każdemu rekordowi; surowe odpowiedzi pozostały nienaruszone w workspace.
  Test zbioru weryfikuje hash dokumentu dowodowego i kontrakty odpowiedzi.
- Końcowy zestaw testów:63passed/1.22s (dane, propozycje, QLoRA smoke bez GPU,
  jakość modelu i adapter Ollamy). git diff --check bez błędów. Kontrola
  arytmetyki i Unicode dotyczy referencji w przykładach, nie wykonania aplikacji.
- --require-ready zwraca oczekiwany kod2:9train,0validation,0test, brak wymaganej
  liczebności. Nie obniżano progów, nie eksportowano do trenera, nie trenowano
  na tych przykładach i nie wdrażano testowego adaptera QLoRA. To kuracja danych,
  nie niezależny benchmark ani dowód większych kompetencji modelu.
- Dokumentacja formatu i planu zaktualizowana. Brak zmian zadań produkcyjnych,
  usług, sterowników, płatności i konfiguracji modeli. Trening kodowania/napraw
  nadal wymaga osobnych sprawdzonych przykładów oraz niezależnego holdoutu.

## 2026-09-13 — instalacja odrębnego środowiska QLoRA za zgodą właściciela

- Utworzono /home/marcin/ai-company-workspaces/qwen-training/venv (Python3.12),
  zainstalowano Unsloth2026.9.4 z kołami binarnymi i zależnościami, bez zmian
  .venv aplikacji. Pip report w workspace, wersje w config/qwen-training.lock.txt.
  pip check: brak konfliktów. Importy Unsloth/TRL/PEFT/bitsandbytes poprawne,
  ostrzeżenia o deprecated ustawieniach PyTorch zachowane w wyniku kontroli.
- Kontrola sterownika tylko odczyt:595.84, RTX5090 CC12.0. Pierwszy odczyt
  i preflight z sandboxa nie miały dostępu do CUDA. Po eskalacji kontrola
  preflight-_wvy8hio/report.json przeszła: PyTorch2.12.1+cu130, około29.8GiB
  wolnego VRAM. Nie zmieniono sterownika, usług, Dockera, Windows ani Vast.ai.
- DNS PyPI był zablokowany w sandboxie; pobrania uruchomiono po jawnej zgodzie
  narzędzia. Przypięto checkpoint unsloth/Qwen3.8-27B-unsloth-bnb-4bit,
  rewizja8aa5f05d26b7205477066e1449e0af13f762a299, metadata license Apache-2.0.
  Pobieranie oddzielnych plików safetensors/tokenizera; obecny GGUF nietknięty.
- Dodano scripts/qwen_qlora_smoke.py: osobna kontrola zasobów, download,
  tokenizacja i ograniczona próba 3 kroków rank4. Wymusza inne środowisko,
  lokalny snapshot bez remote-code, limit czasu, syntetyczną arytmetykę,
  skończony loss, zmianę parametrów i oddzielny adapter NOT-FOR-PRODUCTION.
  Próba techniczna nie omija bramki właściwego zbioru danych firmy.
- tokenize-62dz154g/report.json:passed, cztery sekwencje33–35tokenów, bez
  obcinania przy limicie256. W tej kontroli nie aktualizowano wag.
- Testy danych i smoke:33passed; z test_model_quality:39passed/0.90s.
  Dokumentacja instalacji i granic w QWEN_TRAINING_SETUP.md, odnośnik w planie.
  Z testami lokalnej inferencji i adaptera Ollamy:60passed/2.32s.
- download-79f0srus/report.json:passed, pobranie8plików w345.458s, około22GB.
  Całe środowisko qwen-training około27GB (bez wspólnego cache pip).
- Pierwszy smoke-xwpm_lql:IncompleteSnapshotError przed ładowaniem modelu;
  kontrola local snapshot oczekiwała również niepobieranego .gitattributes.
  Poprawiono skrypt: lokalny odczyt używa tej samej allowlisty co download.
  Nie pobierano dodatkowego kodu i nie usuwano raportu nieudanej próby.
- Drugi smoke-bui0t39x/report.json:passed. Qwen3.8-27B w trybie text_only,
  QLoRA rank4,19 922 944 trenowalnych parametrów,3kroki, max_length256,
  cztery niezależne od zbiorów firmy przykłady dodawania. Bez danych klientów.
  Cały przebieg73.532s, trainer51.2587s, finite_loss=true, średni loss3.167386.
  Zmiana parametru lora_B potwierdzona przez porównanie przed/po.
  Szczytowa alokacja torch22 005 573 632B (około20.5GiB); odczyt nvidia-smi
  podczas próby22 764MiB całkowitego użycia GPU. Bez OOM.
- Unsloth zgłosił brak opcjonalnej szybkiej ścieżki uwagi i użył implementacji
  PyTorch; nie instalowano dodatkowych kompilowanych rozszerzeń/sterowników.
  Tokeny EOS/BOS konfiguracji modelu dopasowano w pamięci do tokenizera;
  zachowano tokenizer przy eksporcie. Źródłowy checkpoint bez nadpisywania.
- Zapisano adapter-NOT-FOR-PRODUCTION/adapter_model.safetensors i konfigurację.
  SHA256:8e88c6b4d9d310ceaf8ca66faab8fbd6039f5cafc4c1b5e4c42f5cea2d8fdda2.
  Nie scalono wag, nie podłączono do Ollamy lub agentów i nie oceniano
  poprawy jakości. Lossy z trzech różnych próbek nie są dowodem poprawy;
  production_ready=false i quality_improvement_measured=false.
- Proces próby zakończył się kodem0. GET organization-os/overview po próbie:
  HTTP200,0.047s. Brak zmian prawdziwych zadań i danych aplikacji.
  Następny etap to zatwierdzony zbiór i trening specjalizacji z odłożoną oceną,
  a nie wykorzystanie tego testowego adaptera przy płatnych zleceniach.

## 2026-09-13 — format i kontrola zbioru treningowego Qwen

- Dodano offline scripts/prepare_training_data.py: wersjonowany JSONL,
  pochodzenie/prawa/prywatność, role rozmowy, odbiór i referencje dowodów.
  Dla kodu/napraw wymagany typ dowodu independent_test. Kontrola metadanych
  nie potwierdza prawdziwości dowodów i nie wykonuje wskazanego kodu.
- Kontrola duplikatów ID, kluczy JSON, par rozmowy, normalizowanych promptów
  i rodzin między train/validation/test. Parafrazy i semantyka wymagają
  dodatkowego przeglądu. Nie ma automatycznego pobierania rozmów klientów.
- Eksport tylko po wszystkich odbiorach i liczebności 200/25/50; trzy osobne
  pliki wiadomości, archiwum rekordów, manifest i hashe. Nowe katalogi wyłącznie
  w Linux workspaces, bez nadpisywania. Nie uruchamia trenera ani nie zmienia wag.
- Sześć syntetycznych kandydatów w datasets/qwen/seed-candidates.jsonl,
  wszystkie pending, jawna demonstracja formatu, nie niezależny holdout.
  Kontrola --require-ready poprawnie zwróciła kod 2, export_ready=false,
  brak odbiorów i niewystarczającą liczebność wszystkich trzech części.
- Testy początkowo 25 passed/2 failed: test błędnie oczekiwał pustego tmp_path,
  w którym wspólna fixture tworzy test.db. Poprawiono porównanie stanu katalogu
  przed/po, bez usuwania fixture. Dodano testy eksportu, symlinków, granic
  ścieżki i podmienionego raportu. Wynik z test_model_quality: 35 passed/0.78s.
- Dokumentacja formatu, ograniczeń i komend w datasets/qwen/README.md;
  zaktualizowany plan QWEN_TRAINING.md. Bez GPU/inferencji/pobrań/treningu,
  zmian .venv, usług, prawdziwych zadań i danych produkcyjnych. To moduł
  przygotowania danych; niezależny odbiór, większy zbiór, tokenizacja i trening
  pozostają do wykonania.

## 2026-09-13 — plan QLoRA i przygotowanie niezależnego pilota aplikacji

- Właściciel preferuje dostrojenie Qwena. Dodano QWEN_TRAINING.md: zakres
  pierwszego adaptera, izolowane środowisko, sprawdzone dane, podział po
  rodzinach problemów, holdout, porównanie z bazą i warunki wdrożenia/wycofania.
  Sprawdzono dokumentację Unsloth Qwen3.8 i PEFT. Deklarowane 24 GB VRAM
  dla QLoRA traktujemy jako przesłankę, nie lokalnie potwierdzoną wykonalność.
  Odczyt metadanych wykazał brak bibliotek treningowych w .venv aplikacji.
  Nie instalowano pakietów, nie pobierano checkpointu i nie uruchomiono treningu.
- Przed zmianą kierunku przygotowano scripts/check_application_delivery.py,
  tests/test_application_delivery_pilot.py i tests/application_pilot_checks.py:
  syntetyczne zlecenie kalkulatora rabatowego, oddzielna baza, 13 niezależnych
  prób HTTP, testy w runnerze i istniejący ograniczony cykl napraw. Tester
  nie pochodzi od modelu. Prawdziwe zadanie #45 i paczka #5 bez zmian.
- Testy lokalne: 1 passed/1 skipped; powiązany zestaw generowania, jakości,
  poprawek i runnera: 29 passed/3 skipped. Nie są to wyniki realnej inferencji.
- Realny pilot w sandboxie nie dotarł do udokumentowanego generowania.
  Przy kontroli Ollama nie miała załadowanego modelu; brak raportu końcowego.
  Po identyfikacji dokładnej komendy zakończono tylko własny proces pytest
  PID 2377093 sygnałem TERM. Wrapper zakończył się z kodem dziecka -15.
  Katalog application-delivery-pilot-hxwq464s zachowany. Przyczyna zatrzymania
  próby nie została rozstrzygnięta; nie zaliczamy jej jako sukcesu ani błędu Qwena.
  Ponowienie pełnego pilota pozostaje do wykonania. Nie restartowano usług,
  hosta, Dockera ani nie zatrzymywano cudzych procesów.

## 2026-09-13 — diagnoza jakości Qwena zamiast niezweryfikowanego treningu

- Właściciel zezwolił na ewentualną zmianę/pobranie modelu. Najpierw wykonano
  odczyt GPU, RAM, lokalnych metadanych Ollamy i kontrolowane próby.
  RTX 5090: 32607 MiB VRAM; około 30 GiB RAM. Model: qwen3.8:27b,
  27.3B Q4_K_M, istniejący digest zachowany. Nie pobrano zamiennika,
  nie trenowano i nie zmieniono wag, globalnej konfiguracji ani modeli na dysku.
- Sprawdzono źródła producenta Qwen3.8-27B i dokumentację structured outputs
  Ollamy. Architektura qwen35 w GGUF nie oznacza modelu Qwen3.5. Początkowo
  parametry rodziny porównano z kartą 3.5, potem potwierdzono je na karcie 3.8.
  Qwen3-Coder:30b sprawdzono jako kandydata, bez twierdzenia, że jest lepszy.
  Źródła i decyzje: docs/organization-os/MODEL_QUALITY.md.
- Adapter local_ollama przyjmuje nazwane, serwerowe profile próbkowania oraz
  schemat JSON (limit wielkości, zakaz zewnętrznych $ref). Nadal stały loopback,
  przypięty digest, brak narzędzi, limit czasu i wyjścia oraz keep_alive=0.
  Domyślna temperatura 0.2 bez zmiany. Próbne ustawienia .7/top_p .8/top_k20/
  presence1.5/repeat1.0 nie zostały globalnie włączone. Nie dodano API do
  przekazywania arbitralnych parametrów z promptu użytkownika.
- Produkcyjna analiza Upwork przekazuje do Ollamy schemat ScopeResult z Pydantic,
  zamiast samego format=json. Dotychczasowy walidator spójności pozostaje.
  scope_decoder=json-schema.v1 w snapshotach wymusza odnowienie starych
  zakolejkowanych przebiegów; poprzednie wyniki pozostają zachowane. Brak
  automatycznej akceptacji, nowych praw ani uruchamiania kodu klientów.
- Nowy scripts/check_model_quality.py: trzy syntetyczne przypadki (pytania,
  8*322, CRM poza profilem z instrukcją próbującą zmienić decyzję), trzy
  warianty, sekwencyjnie, bez prawdziwej bazy i danych klientów. --recheck
  ponownie ocenia zapisane odpowiedzi bez inferencji i nadpisywania raportu.
- Pierwsza seria: model-quality-lxh14xd7/report.json w Linux workspaces.
  Pierwotny licznik 5/9 był częściowo błędny: test odrzucał „walucie”.
  Dodano obsługę odmiany i testy Unicode; test jednostkowy ujawnił też błędne
  liczenie cyfr w escape JSON, naprawiono ocenę na zdekodowanym tekście.
  Przeliczenie tych samych odpowiedzi: baseline 2/3 (za dużo exclusions),
  sampling 3/3, schema 3/3. Raport pierwotny zachowany bez zmian.
- Powtórki schema: model-quality-s7cwkpwn/report.json, 6/6. Razem 9/9 na
  trzech powtarzanych przypadkach — nie benchmark wszystkich kompetencji.
  Odpowiedzi przeczytano: pytania krótkie, brak zmyślonego podatku, poprawne
  2576, odrzucenie obowiązkowych funkcji poza profilem. Sformułowania pytań
  nadal mogą być nieoptymalne; format nie dowodzi pełności analizy.
- Rzeczywisty pilot ścieżki API: upwork-scope-pilot-ot6lzslq/report.json,
  1 passed/14.64 s; model 14.104 s, 1311/151 tokenów. Poprawne UNSUPPORTED
  z PostgreSQL/Stripe/kontami/e-mail/hostingiem. TaskAttempt awaiting_review,
  postęp0, brak odbioru i generowania kodu. Wszystko w izolowanej bazie.
- Testy: początkowo45 passed/1 skipped; test Unicode początkowo1 failed/15 passed,
  następnie naprawiony. Zestaw po zmianach: 167 passed/4 skipped w12.01s,
  w tym kontrakt dekodera, nieaktualny snapshot, izolacja/role/pakiety,
  Upwork, sesje, aplikacje, testy jakości i pomoc. git diff --check zaliczony.
- Dwa odczyty metadanych i pierwsze uruchomienie prób zablokowała piaskownica;
  po jawnej zgodzie wykonano lokalne połączenia. Pusty katalog przerwanej próby
  model-quality-pxnak_20 zachowany. Bez obchodzenia uprawnień.
- Dokumentacja: MODEL_QUALITY.md, UPWORK.md, indeks. Pozostaje potrzeba
  szerszych testów kodowania w runnerze oraz przyszłego doboru modelu do roli.
  Nie uczymy na niezweryfikowanych odpowiedziach; ewentualny trening wymaga
  zatwierdzonego zbioru i oddzielnych testów. Zlecenia #45/paczka#5, systemowe
  procesy, Vast.ai, Docker, partycje, Windows i prawdziwe dane bez zmian.

## 2026-09-13 — specjalizacje agentów działowych i kontrolowany lokalny Qwen

- Rozszerzono istniejące 72 tożsamości w 12 działach, bez nowej bazy agentów
  i bez uruchamiania 72 modeli. `department_profiles.py` określa misje,
  dane wejściowe, rezultaty i granice sześciu ról. Cztery role wykonawcze
  korzystają ze wspólnego Qwena na żądanie; kierownik i kontroler pozostają
  rolami koordynacji. Nie wdrożono autonomicznego kierownika ani niezależnego
  drugiego modelu odbierającego wynik. Końcowy odbiór pozostaje właścicielski.
- Pakiety istniejących delegacji zawierają profil działu i jego instrukcję
  systemową. Wersja `department-specialization.v2` jest objęta checksumą.
  Zmienione instrukcje wymagają nowego pakietu dla gotowego zadania;
  zachowane są stare artefakty, wyniki i odebrane zadania. Nie zmieniono
  reguł izolacji kodu, uprawnień, akceptacji ani kontraktu analizy Upwork.
- Usunięto konflikt narzuconego ogólnego raportu z krótkim formatem zadania
  dla profili działowych. Granice bezpieczeństwa nadal nadrzędne wobec briefu.
  Marketing nie udaje źródeł internetowych; finanse nie zgadują kwot/prawa;
  tester tekstowy nie deklaruje uruchomienia testów; Linux bez zmian hosta.
- `/os/work?teams=1`, wyszukiwarka „Agenci działów”: specjalizacje,
  liczba przypisanych zadań, stany ostatnich wykonań i odbiorów, zadania działu,
  blokady oraz link do właściwego projektu/formularza. Stany to rejestr,
  nie heartbeat procesów; nie przypisujemy pracy modelu kierownikowi.
- Owner-only GET `/api/agent-teams/{id}/work` ma paginację 20 rekordów,
  no-store i nie uruchamia modelu. Odczyty nie zmieniają danych. Agregaty
  nie wczytują prywatnej treści wyników. Panel odświeżany na żądanie.
- Lokalny Qwen użyty do ograniczonej konsultacji projektu i zagrożeń:
  `/tmp/qwen-runner-draft-tly_vh7g/draft.json`, 15.974 s, 277 tokenów wejścia,
  381 wyjścia. Raport odczytano; uwzględniono wersjonowanie, niepewne stany
  i rozdzielenie wyniku od odbioru. Wygenerowanego kodu nie uruchamiano na hoście.
- Nowy jawnie uruchamiany `scripts/check_department_agents.py` sprawdza
  rzeczywisty model na syntetycznym zadaniu finansowym w osobnej bazie.
  Raporty zachowano w `/home/marcin/ai-company-workspaces/`:
  - `department-agent-pilot-4w4auic3/report.json`: 18.975 s, 801/737 tokenów.
    Test transportu zaliczony, lecz ręczny przegląd odrzucił długi raport
    i fałszywą deklarację limitu 120 słów. Pierwotny test był zbyt słaby.
  - `department-agent-pilot-ep2x0sh6/report.json`: 16.161 s, 822/369 tokenów;
    zaostrzony test NIEZALICZONY (166 słów zamiast najwyżej 120).
  - `department-agent-pilot-6t5tvnkz/report.json`: 15.593 s, 867/274 tokenów;
    NIEZALICZONY (130 słów). Doprecyzowano krótkie pytania w profilu.
  - `department-agent-pilot-4_bbs8dj/report.json`: 14.790 s, 873/184 tokenów;
    test słów/pytań/niezmyślonych kwot zaliczony, ALE przegląd wykrył 12
    pytań zamiast maksymalnie 6. Dodano brakującą asercję liczby pytań.
    Próbki nie uznano za pełny sukces jakościowy; nie ponawiano kolejnego
    przebiegu modelu po tej asercji. Znany problem zgodności pozostaje jawny.
  Żadnego wyniku pilota nie odebrano; zadania pozostawały in_progress/0%.
  Sam test pilota nie jest uniwersalnym walidatorem briefów produkcyjnych.
- Testy deterministyczne obejmują profile wszystkich działów i cztery etapy,
  niezmienność historii, stany Qwen/odbioru, paginację, brak mutacji i RBAC.
  Wstępne zestawy: 56 passed/1 skipped, następnie 99 passed/1 skipped.
  Szerszy zestaw początkowo 149 passed/4 skipped/1 failed: wcześniejszy test
  pomocy zabraniał każdego query string. Dopuszczono wyłącznie bezpieczny
  wewnętrzny link `/os/work?teams=1`. Końcowo 150 passed/4 skipped w 11.67 s.
  Pominięcia dotyczą prób wymagających jawnego uruchomienia zasobów.
- Chrome `check_work_browser.py` zaliczony, również po zmianach: profile,
  zadania działu, paginacja, escapowanie tekstu, brak automatycznej inferencji,
  wcześniejsze funkcje Upwork/plików/testów, mobilność i 36 wariantów palet.
  API symulowane, GPU przeglądarki wyłączone, bez realnych zapisów.
  `node --check work.js` i `git diff --check` zaliczone.
- Zaktualizowano AGENT_TEAMS.md i centrum pomocy. Nie modyfikowano ręcznie
  STATUS.md, realnych zadań (w tym #45), paczki #5 ani danych klientów.
  Bez publikacji/komunikacji Upwork, wydatków, treningu, instalacji modeli,
  restartów hosta, zmian Vast.ai/Docker/sieci i dostępu do dysku Windows.

## 2026-09-13 — priorytet Upwork i nadzorowana kwalifikacja lokalnym Qwenem

- Zgodnie z nowym priorytetem właściciela dodano `/os/upwork`: ręcznie wklejone
  ogłoszenie, kryteria, uwagi, źródło, lista zleceń, analiza i przejście do
  konkretnego projektu. Konta klientów prywatnych/płatności odłożono. Zwykłe
  logowanie właściciela hasłem NIE zostało jeszcze wdrożone: obecna sesja
  działa nadal. Nie przedstawiamy jej jako nowego konta email/hasło.
- Nowe owner-only API `/api/upwork-orders` wykorzystuje WorkOrder/Project/Plan/Task,
  istniejące delegacje, instrukcje i LocalInference, bez nowej bazy/migracji
  i bez drugiej kolejki. Metadane źródła w brief JSON; realizacja pod istniejącym
  `web-platforms.business`. Cztery zadania pozostają niezakończone, poza starą
  automatyczną kolejką. Zapis i przygotowanie analizy mają idempotencję/transakcję.
- URL dopuszcza wyłącznie HTTPS upwork.com/www.upwork.com bez portu/loginu;
  jest zapisywany jako tekst, NIE pobierany. Brak integracji konta Upwork,
  scrapingu, wysyłania ofert, obietnic ceny/terminu, przyjęcia umowy i publikacji.
- Widoczne linki w Command i Spatial, wynik wyszukiwarki, temat pomocy oraz
  otwieranie wskazanego projektu przez `/os/work?project=ID` (tylko odczyt).
  Nowy panel używa wspólnej sesji i nie dokłada pola kolejnego tokena.
- Qwen wykorzystano jako pomocnika, nie samodzielnego autora akceptującego kod.
  Krótka konsultacja `scripts/qwen_runner_assist.py --upwork-review`:
  `/tmp/qwen-runner-draft-x333cwc5/draft.json`, 17.005 s, 273 tokeny wejścia,
  498 odpowiedzi. Wdrożono m.in. ocenę dopasowania, wyłączenia i przypadki
  odbioru. Idempotencję egzekwuje kod, nie sugerowana obietnica w instrukcji.
- Właściciel ponownie zażądał kontroli parametrów i halucynacji. Rzeczywisty
  pilotaż na syntetycznym CRM poza profilem wykazał poprawne UNSUPPORTED,
  ale rozwlekłą, zapętloną odpowiedź. Sam test obecności słów przeszedł
  (1 passed / 33.54 s), mimo że ręczny przegląd odrzucił jakość tekstu.
  Raport: `ai-company-workspaces/upwork-scope-pilot-_af69y7i/report.json`.
  Nie potraktowano tego jako dobrego wyniku ani odebranego zadania.
- Poprawka: kontrakt `upwork-scope.v1`, wymuszony JSON, limit 3200 znaków,
  ograniczone pola/listy i kontrola duplikatów oraz podstawowej spójności.
  Zła odpowiedź daje `scope_contract_invalid` i nie tworzy TaskAttempt.
  SUPPORTED nie dopuszcza otwartych pytań; UNSUPPORTED nie tworzy zakresu
  do wykonania ani negocjacji usunięcia wymagań. W drugim pilotażu model
  sugerował opcjonalność obowiązkowych funkcji — poprawiono instrukcję
  i walidację, zamiast bezkrytycznie akceptować poprawny JSON.
- Instrukcja jest objęta checksumą pakietu; jej zmiana zatrzymuje stare
  wykonanie jako stale. Limit analityka: min(konfiguracja,1536 tokenów).
  Zachowano 16384 kontekstu, max 8 wątków, 180 s, temperaturę 0.2,
  think:false, pin digest i brak narzędzi. Profil kodu ma niezmieniony budżet.
  Niższa temperatura i walidacja nie dowodzą braku halucynacji — ocena
  biznesowa nadal wymaga kontroli, a kod rzeczywistych testów.
- Pilotaże po poprawkach, każdy na osobnej testowej bazie i bez kodu/kontraktów:
  `upwork-scope-pilot-cnch42rk` 1 passed / 15.03 s (model 14.517 s, 151 tokenów);
  `upwork-scope-pilot-x27ckvzn` 1 passed / 13.51 s (model 12.972 s, 131 tokenów);
  końcowy `upwork-scope-pilot-f6avkxzn` 1 passed / 14.24 s
  (model 13.717 s, 1025 wejścia / 152 odpowiedzi). Przeczytano raporty.
  Wynik końcowy: krótka ocena UNSUPPORTED, bez kodu, powtarzania i pomijania
  obowiązkowych wymagań. Żadnej analizy nie odebrano automatycznie.
- Testy: początkowo 61 passed / 1 failed (kolejność tematów pomocy);
  zachowano Start jako pierwszy temat. Następnie 84 passed / 3.78 s;
  89 passed, 1 skipped / 4.73 s; 109 passed, 3 skipped / 7.20 s.
  Końcowy zestaw: **125 passed, 3 skipped / 7.84 s**. Skip to pilotaże
  opt-in modelu/Dockera, uruchamiane osobno. Weryfikowano RBAC, replay,
  rollback, powiązania etapów, kolejkę, odrzucanie złych odpowiedzi,
  zmianę instrukcji, generowanie, poprawki, sesje i pomoc.
- Chrome `check_work_browser.py`: początkowo dwie nieaktualne asercje
  (liczba tematów 10→11; tytuł projektu zawiera prefiks #200) — poprawione.
  Końcowo zaliczone: formularz Upwork, replay po symulowanym 503, jedna
  inferencja, bezpieczny tekst/JSON, odświeżenie bez ponownego startu,
  przejście do właściwego projektu, 1440/390 px i wcześniejsze funkcje.
  API symulowane, bez GPU i zapisów produkcyjnych. Node --check trzech
  skryptów i git diff --check zaliczone.
- Dokumentacja: UPWORK.md, centrum pomocy, indeksy, LOCAL_INFERENCE.md.
  Nie zmieniano ręcznie STATUS.md, prawdziwego zadania #45 ani jego paczek.
  Nie restartowano hosta/usług/Dockera, nie używano Windows, nie uruchamiano
  wygenerowanego kodu na hoście i nie wykonywano działań wobec klientów.

## 2026-09-13 — wspólna sesja właściciela i rozróżnienie kodu klienta

- Po zgodzie na dalszą budowę wdrożono wcześniej zgłoszone usprawnienie:
  jedno logowanie w górnym pasku zamiast ponownego wklejania tokena przy
  przechodzeniu między panelami. Sesja obejmuje pulpit/Spatial, realizację,
  budowę/testy, historię, odbiór, publikacje i podgląd klienta właściciela.
- POST/GET/DELETE /api/owner-session; losowy identyfikator, hash w pamięci,
  HttpOnly/SameSite Strict cookie Path=/api, bezwzględne 8 godzin i limit 32.
  HTTPS Secure; wyjątek HTTP wyłącznie kanoniczny loopback. Kontrola Origin,
  X-Owner-Origin, Sec-Fetch-Site i CSRF przy mutacjach. Token API nie jest
  zapisywany w cookie ani browser storage. Restart/rotacja tokenów unieważnia
  sesje. Magazyn jednego procesu, nie rozwiązanie wieloworkerowe.
- require_owner przyjmuje sesję tylko bez jawnego Authorization. Błędny lub
  pusty nagłówek, worker i klient nie uzyskują dostępu przez fallback.
  Zachowano jednorazowy Bearer i dotychczasowe uprawnienia API. Nowe adaptery
  fetch są jawne, nie zastępują globalnego fetch i nie używają sesji klienta.
- Po odtworzeniu sesji tylko formularze odczytu otwierają dane automatycznie.
  Publikacja, odbiór, wykonanie modelu i testów nadal wymagają działania.
  Wylogowanie unieważnia serwerową sesję i powiadamia karty przez BroadcastChannel;
  nie udaje anulowania już przyjętych operacji. Restart --reload może wymagać
  kolejnego logowania podczas dalszego rozwijania kodu.
- W trakcie właściciel zgłosił użycie swojego tokena w /client. Wyjaśniono
  różnicę i poprawiono komunikat: brak dostępu nie dowodzi wygaśnięcia tokena
  właściciela, ponieważ klient potrzebuje osobnego kodu projektu. Lokalny
  /client ma bezpośredni link do /os/client-preview. Osobny serwer klienta
  nie otrzymał tras, skryptów ani katalogu właściciela.
- Wykorzystano lokalnego qwen3.8:27b do przeglądu ryzyk i proponowanych testów:
  scripts/qwen_runner_assist.py --owner-session-review, 19.65 s,
  356 tokenów wejścia/766 wyjścia. Raport /tmp/qwen-runner-draft-pvm6wmji/draft.json.
  Odpowiedzi nie wykonano jako kodu; zweryfikowano m.in. TTL, restart, role,
  origin, limit sesji i wylogowanie. Nie przekazywano sekretów ani danych klienta.
- Testy: początkowo 56 passed / 6.86 s; szersza regresja paneli 86 passed /
  12.98 s; autoryzacja i sesje 24 passed / 0.81 s; końcowe auth/session/help/
  navigation 51 passed / 1.39 s. Node --check siedmiu zmienionych skryptów
  i git diff --check bez błędów.
- Chrome check_work_browser zaliczony, w tym przejście po jednym logowaniu
  do work/build/history/review/publishing/owner-preview, brak Bearer w żądaniach
  sesji, ukryte pola tokena i wylogowanie. Poprzednie scenariusze zachowane.
- Pierwsze wywołanie check_client_browser nie podało wymaganego --output
  (kod 2); poprawiono wywołanie. Następnie stara asercja demo „zero żądań”
  wykryła nowy, prawidłowy odczyt statusu sesji. Dodano osobną atrapę tego
  odczytu (401), pozostawiając kontrolę braku operacyjnych żądań demo.
  Powtórny test zaliczony: workflow, historia, publikacje, mobile, bezpieczny
  tekst, odrzucenie spóźnionej odpowiedzi po wylogowaniu.
  Zrzuty: /tmp/ai-client-session-check-BJmzdT. Testy Chrome bez GPU, API atrapami.
- Dokumentacja OWNER_SESSION.md, instrukcje pomocy, indeks oraz EXECUTION.md
  zaktualizowane razem z funkcją. Brak zmian rzeczywistych projektów, paczek,
  publikacji, procesów wynajmu, hosta czy sieci. Serwera nie restartowano ręcznie.

## 2026-09-13 — widoczny panel klienta i wyszukiwarka nawigacji

- Na prośbę właściciela dodano pole „Znajdź stronę lub funkcję” w nawigacji
  pulpitu, Spatial, realizacji, budowy, odbioru, publikacji, historii i pomocy
  właściciela. Siedem paneli ma też stały odnośnik „Panel klienta ↗” bez JS.
- Katalog 13 stron odróżnia wejście klienta, podgląd właściciela, publikacje
  z kodami oraz historię. Wyszukiwanie po słowach i synonimach, bez polskich
  znaków, uwzględnia również „klijenta” i „spartial”. Ctrl/Command+K, strzałki,
  Enter, Tab i Escape; stan pusty, zamknięcie i ponowne otwarcie kliknięciem.
- Bez zmian autoryzacji, baz, zadań i publikacji. Żadne zapytanie nie trafia
  do API, modelu ani storage; wejścia renderowane przez textContent. Osobny
  serwer klienta nie udostępnia katalogu ani jego zasobów. Nie jest to
  wyszukiwanie danych rzeczywistych projektów.
- Testy: 59 passed w 7.12 s (navigation_search, help_center, client_portal,
  shared_appearance, command_center, spatial_page). Chrome check_work_browser
  zaliczony: 1440/390 px, pozycja wyników, literówki, polskie znaki, brak
  wyników/iniekcji, klawiatura i rzeczywiste przejście do formularza klienta
  z pulpitu i Spatial. Wcześniejsze scenariusze pomocy, budowy, napraw i palet
  również zaliczone. API operacyjne były atrapami, GPU wyłączone.
- Pomoc pierwszego projektu i dokumentacja NAVIGATION_SEARCH.md/HELP_CENTER.md
  zaktualizowane. Właściciel ponowił preferencję oszczędzania zewnętrznego
  modelu i wykorzystania lokalnego Qwena do większych prac; przy tej gotowej
  zmianie nawigacji nie uruchamiano dodatkowej inferencji ani treningu.

## 2026-09-13 — pierwsze centrum pomocy właściciela i klienta

- Po zgodzie właściciela dodano `/os/help` (10 instrukcji) oraz `/client/help`
  (7 instrukcji), z wyszukiwaniem lokalnym, stałymi odnośnikami, drukowaniem
  przez przeglądarkę i wspólnymi paletami. Treść jest renderowana na serwerze;
  instrukcje pozostają czytelne bez JS i bez tokena.
- Przycisk Pomoc dodano w ośmiu głównych widokach: command, spatial, work,
  build, review, publishing, client-history i client. Budowa ma także
  odnośniki bezpośrednio wyjaśniające naprawy i „Wydanie wstrzymane”.
- Przejrzano aktualne UI oraz kontrakty: panel klienta używa czasowego kodu,
  publikowanych treści i decyzji. Nie przedstawiono kont e-mail, płatności,
  transferu ZIP, hostingu czy czatu jako już działających. Instrukcje rozróżniają
  automatyczne testy/naprawy, odbiór właściciela i publikację klientowi.
- Osobna aplikacja klienta udostępnia tylko jego katalog i neutralne zasoby
  help.js/help.css. Nie ma w nim tematów Qwena ani odnośników właściciela.
  Help nie odczytuje danych operacyjnych. Brak inferencji i zapisów projektów.
- Pierwszy test Chrome wykrył konflikt fokusu: przeglądarka po początkowym
  otwarciu fragmentu zmieniała aktywny element. Dodano przywrócenie fokusu
  na summary po load. Powtórny pełny check_work_browser.py zaliczony:
  wyszukiwanie bez polskich znaków, brak wyników/iniekcji HTML, odnośniki,
  stan po drukowaniu, sześć wariantów palet pomocy, telefon, treść bez JS
  oraz wcześniejsze scenariusze realizacji/testów/poprawek i 36 kontroli motywów.
  Przeglądarka miała wyłączone GPU, API operacyjne były atrapami.
- Pytest: test_help_center, test_client_portal, test_shared_appearance,
  test_command_center, test_spatial_page — 48 passed w 6.79 s.
  Końcowy test_help_center — 16 passed w 0.36 s.
  Node --check help.js i git diff --check bez błędów.
- Dokumentacja: HELP_CENTER.md i indeks docs/README.md. Katalog pomocy jest
  redagowany i aktualizowany razem z funkcjami, nie synchronizowany samoczynnie.
  Nie zmieniano zadania 45, paczki 5, bazy operacyjnej, konfiguracji hosta,
  usług ani kontenerów. Istniejący serwer --reload obsłużył nowe trasy.

## 2026-09-13 — automatyczne wykrywanie, naprawa Qwen i ponowne testy

- Na polecenie właściciela wdrożono rzeczywisty cykl testy → automatyczna
  diagnoza logu → poprawka Qwen → nowa paczka → ponowne testy. Nie ogranicza się
  do zatrzymania po błędzie. Jeden start pozwala wykonać do dwóch poprawek
  i trzech zestawów testów, bez formularzy pomiędzy kolejnymi wersjami.
- Nowe owner-only API application-quality i przycisk „Testuj i napraw
  automatycznie” w /os/build. Historia pokazuje wszystkie testy, poprawki i
  paczkę końcową. Odświeżenie i zatrzymanie są dostępne podczas wykonania;
  wylogowanie usuwa dane/token, ale nie udaje anulowania rozpoczętej operacji.
- Bazowe test_app.py i polityka testów/modelu są przypięte w niezmiennym
  raporcie. Zmieniony plik testów nie trafia do runnera jako podstawa sukcesu.
  Qwen otrzymuje oryginał, wcześniejsze źródła i log błędu jako niezaufane dane.
  Przy poprawce tworzone jest nowe ID paczki; stara pozostaje niezmieniona.
- Cykl korzysta z istniejących LocalInference, PackageRun, Artifact i odbiorów.
  Automatyczne odrzucenie zapisuje automated_qa / automatic_test_feedback,
  nie fałszywe potwierdzenie właściciela. Automatyczna akceptacja w tym trybie
  jest zabroniona. Wynik „passed” oznacza zaliczenie konkretnego zestawu,
  nie pełny odbiór biznesowy, audyt wyglądu ani publikację klientowi.
- UUID poszczególnych operacji są deterministyczne. Odzyskanie po przerwaniu
  po zapisie modelu nie odrzuca ponownie próby i nie powiela inferencji.
  Blokada fcntl per baza/zadanie zapobiega równoległym cyklom na tym hoście.
  Brak nowego demona: restart serwera może wymagać wznowienia z historii.
  Deadline 15 min, kontrola zapasu na operację, limit prób, kontrola polityki,
  powtarzających się źródeł i prośba o stop. Niepewna infrastruktura pozostaje
  blokadą, a nie poleceniem dla modelu, by obchodził izolację lub zmieniał hosta.
- Próba prawdziwa: scripts/check_revision_pilot.py --automatic,
  /home/marcin/ai-company-workspaces/automatic-quality-pilot-f_1bsb4b.
  W osobnej bazie celowo zmieniono mnożenie na dodawanie w kopii kalkulatora.
  Pierwszy test failed → jedna poprawka rzeczywistego qwen3.8:27b → kolejny
  test passed. Inferencja 30.892 s, 6051 tokenów wejścia i 2998 wyjścia. Bazowy
  plik testów identyczny. Niezależny dodatkowy GET /api/estimate dla 8 i 322
  zwrócił 2576.0. Pilot 1 passed w 33.12 s. Raport i repaired-candidate.zip zachowane.
  Nie poprawiano kodu ręcznie pomiędzy niezaliczonym a zaliczonym testem.
  Oba kontenery testów posprzątane; kontrola końcowa nie wykazała pozostałych
  kontenerów z etykietą ai-company.package-runner. Produkcyjne zadanie 45,
  paczka 5 i działający kalkulator nie zostały zmienione.
- Testy lokalne: początkowo 27 passed / 1 skipped, następnie 139 passed / 2 skipped;
  po rozszerzeniu przypadków deadline/polityka/stop/brak postępu końcowo
  143 passed / 2 skipped w 14.65 s. Dwa opt-in prawdziwe piloty pomijane w regresji;
  opisany wyżej automatyczny pilot wykonany oddzielnie. Zero niezaliczonych
  testów regresji; błąd kalkulatora w pilocie był celowym wejściem testowym.
  Po dodatkowym ograniczeniu limitu także w warstwie usługi: 13 passed,
  1 skipped w 1.85 s; końcowe git diff --check bez błędów.
- Chrome check_work_browser.py zaliczony: start/retry 503 z tym samym UUID,
  historia test→poprawka→test, tekst zamiast HTML, wylogowanie i wcześniejsze
  funkcje/palety 36 wariantów. API symulowane, bez zapisów do realnych projektów.
  node --check i git diff --check zaliczone. Zaktualizowano zależność skryptu
  check_application_browser.py o nowy asset; w tej turze nie uruchamiano tego
  osobnego testu na produkcyjnym kalkulatorze.
- Dokumentacja AUTOMATIC_QUALITY.md i odnośniki w APPLICATION_FACTORY.md oraz
  APPLICATION_REVISIONS.md; build.js?v=6. Bez instalacji modeli, treningu,
  płatnych usług, publikacji, restartu hosta/Docker/Uvicorn, ingerencji
  w Vast.ai lub dysk Windows.

## 2026-09-13 — czytelna gotowość aplikacji do wydania

- Przejrzano istniejącą ścieżkę testy → odbiór → ZIP. Bramka była w backendzie,
  ale interfejs oferował przygotowanie wydania przed wyjaśnieniem blokad.
  Dodano owner-only, read-only GET package-runs/{id}/delivery-readiness.
- Wydzielono wspólną walidację kandydata bez tworzenia archiwum przy odczycie.
  Gotowość sprawdza ten sam raport i źródła oraz approved_result co wydanie:
  aktualny/najnowszy test i dokładne powiązanie odebranej próby ze źródłami.
  Niespójny istniejący raport wydania blokuje gotowość. Nic nie jest naprawiane
  ani akceptowane przez samo wywołanie GET.
- /os/build pokazuje „Sprawdź gotowość do przekazania”, powód blokady i kroki
  odbioru. Przycisk pobrania zatwierdzonego wydania pojawia się po zaliczeniu
  kontroli; błąd kolejnego odczytu chowa go ponownie. Przy zapisie/pobraniu
  backend nadal ponownie sprawdza stan. Kandydat, odbiór właściciela,
  pobranie i publikacja klientowi pozostają rozdzielone. build.js?v=5.
- Testy kontrolują brak zapisów przy odczycie, odmowę bez uprawnień, brak
  wykonania, niepewny test, brak odbioru, gotowość po odbiorze, istniejące
  wydanie, uszkodzony zapis i utratę gotowości po nowym niezaliczonym teście.
  Zestaw początkowy: 38 passed, 1 skipped w 7.32 s; szersza regresja:
  130 passed, 1 skipped w 12.75 s. Pominięty wyłącznie opt-in rzeczywisty pilot.
- Chrome check_work_browser.py: zaliczone brak odbioru → gotowość → błąd503,
  tekst zamiast HTML w komunikacie, wcześniejszy formularz poprawek i 36
  kombinacji wyglądu. API symulowane; bez zapisów prawdziwych zleceń.
  node --check i git diff --check zaliczone. Dokumentacja APPLICATION_FACTORY.md.
- Bez inferencji Qwen (deterministyczne reguły wydania nie wymagają modelu),
  nowych kontenerów, publikacji, zmian kalkulatora/zadania45/paczki5,
  restartów, ingerencji w Vast.ai ani dysk Windows.

## 2026-09-13 — wersjonowane poprawki aplikacji przez Qwen

- Po potwierdzeniu właściciela, że kalkulator liczy, wdrożono przepływ
  zgłoszenie poprawki → Qwen → nowa paczka → opcjonalne testy → odbiór.
  Nie odrzucono ani nie zaakceptowano rzeczywistego zadania 45/paczki 5.
- Dodano owner-only API application-revisions oraz formularz i historię
  w /os/build. Opis, oczekiwany rezultat, dowody i świadome potwierdzenie
  wiążą zgłoszenie z konkretną checksumą najnowszej próby awaiting_review.
  Dotychczasowe źródła pozostają niezmienne. Zgłoszenie jest raportem Artifact,
  bez nowej tabeli i bez równoległego systemu zadań.
- Wspólną logikę odbioru wydzielono do result_review.apply_review. Odrzucenie
  próby, przygotowanie instrukcji, kolejka i zapis zgłoszenia są atomowe;
  błąd wycofuje całość. UUID zgłoszenia i deterministyczny UUID testów chronią
  przed podwójnym wykonaniem przy ponowieniu żądania. Nie ma autoakceptacji.
- Poprawka profilu kodu przekazuje Qwenowi pełne wcześniejsze źródła oraz
  uwagi. Kontekst tej próby zwiększany o 16384, do maks. 32768; bazowa
  konfiguracja niezmieniona. Wyjście 4096 tokenów, 8 wątków, timeout 180 s.
  Bez treningu, nowego modelu, dowolnych narzędzi czy wykonywania kodu na hoście.
- Pierwszy rzeczywisty pilot (revision-pilot-i822etu8) został odrzucony przez
  niezależną asercję wymaganej poprawki UI mimo zaliczonych testów technicznych.
  Przyczyna w fixture: źródła kalkulatora połączono z opisem innego projektu.
  Uzupełniono opis zadania i delegacji wyłącznie w kopii testowej. Zachowano
  raport nieudanej próby; nie traktujemy samych testów modelu jako odbioru.
- Ponowny pilot: /home/marcin/ai-company-workspaces/revision-pilot-5mygos79.
  Rzeczywisty qwen3.8:27b: 30.909 s, 4961 tokenów wejścia i 3084 wyjścia.
  Nowa paczka o checksumie
  05851625c307f24f9bfbcd7d6fda2d5a9fbb181e8b65c144b01ba0ed5fd0e303,
  test_state=passed, awaiting_review, accepted=false. Raport i ZIP w katalogu
  pilota. Osobna baza pytest; brak mutacji produkcyjnego kalkulatora.
  Sprawdzono testy kontenerowe i obecność tekstu „Obliczanie” w źródłach,
  nie deklarujemy pełnego przeglądarkowego odbioru poprawionego interfejsu.
- Regresja: 130 passed, 1 skipped (opcyjny pilot) w 12.70 s; prawdziwy
  pilot oddzielnie 1 passed w 32.16 s. Chrome check_work_browser.py zaliczony:
  formularz, ponowienie po 503 z tym samym UUID, tekst zamiast HTML, historia
  wersji i czyszczenie przy wylogowaniu oraz wcześniejsze 36 wariantów wyglądu.
  Ten test UI używa symulowanego API. node --check i git diff --check OK.
- Po pilocie brak pozostawionych kontenerów ai-company.package-runner.
  Dodatkowo check_application_browser.py z prawdziwym API i runnerem potwierdził
  działanie dotychczasowego kalkulatora po zmianie panelu: 8 × 322 = 2576 zł,
  dane ujemne → 400, izolacja ramki i czyszczenie przy wylogowaniu. Zapisano
  wyłącznie raporty podglądu 17–19, każdy z cleanup_confirmed=true; status
  zadania i źródła niezmienione. Nie jest to test UI nowej wersji z pilota.
  Bez restartu hosta, Docker, Uvicorn, zmian usług Vast.ai i dysku Windows.
  Dokumentacja: docs/organization-os/APPLICATION_REVISIONS.md i odnośnik
  w APPLICATION_FACTORY.md. Zasoby panelu z nową wersją cache build.js?v=4.

## 2026-09-13 — poprawka kontraktu źródeł podglądu po próbie właściciela

- Właściciel nadal widział formularz bez obliczeń. Zapis 9 pokazywał tylko
  GET /, bez /api/estimate. Przyczyna: GET workspace-packages/{id} zwraca
  package_summary, czyli metadane bez content. Broker pobierał z nich app.js
  i style.css. Wcześniejsza fixture testu przeglądarkowego błędnie zawierała
  treści, przez co nie wykryła różnicy względem prawdziwego kontraktu API.
- POST package-runs/preview dla GET / zwraca teraz assets z treścią tylko
  app.js/style.css zweryfikowanej paczki. Zwykły GET nadal zwraca metadane.
  Broker sprawdza checksumę oraz obecność wymaganych treści i zgłasza błąd
  zamiast cicho tworzyć nieaktywną stronę. Podniesiono wersje zasobów do
  application-preview.js?v=2 i build.js?v=3, aby odświeżyć cache przeglądarki.
- Test przeglądarkowy przechodzi teraz przez pełne endpointy FastAPI przez
  TestClient: prawdziwa serializacja, autoryzacja, walidacja i middleware.
  Zaufany tymczasowy serwer i losowy token działają tylko w procesie testowym.
  Bez lifespan/seeda i bez uruchamiania wygenerowanego Pythona na hoście.
- Dodano regresję kontraktu metadane kontra assets. Trzy zestawy backendowe:
  17 passed w 1.17 s. Pełna próba w Chrome zaliczona: wykonania 10 (strona),
  11 (8 × 322 → HTTP 200 i widoczne „Łączny koszt: 2576 zł”), 12 (ujemne dane
  → HTTP 400 i komunikat). Wszystkie trzy cleanup_confirmed=true. Zaliczono
  izolację DOM/storage, odmowę zewnętrznego fetch i POST oraz logout.
  Nie zmieniono źródeł paczki 5 ani odbioru zadania 45.
- Końcowy szerszy zestaw regresji: 65 passed w 8.07 s. Przebieg w sandboxie
  zawiesił się bez wyników; po kontroli dokładnej komendy zakończono wyłącznie
  własny pytest PID 2282400 (SIGINT nieskuteczny, następnie SIGTERM). Ponowienie
  poza sandboxem zakończyło się powodzeniem. Nie dotykano serwera ani innych
  procesów. node --check i git diff --check również bez błędów.

## 2026-09-13 — działający podgląd kalkulatora i regresja kliknięcia

- Zgłoszenie właściciela: po otwarciu index.html z dysku przycisk Oblicz
  nie działał dla 8 godzin i stawki 322. Inspekcja oryginalnej paczki 5
  potwierdziła bezwzględne /app.js i zależność od serwera /api/estimate.
  Poprzednie 19 testów jednostkowych i smoke HTTP nie obejmowały kliknięcia
  formularza. Nie zmieniono wstecznie paczki, raportów ani odbioru zadania 45.
- Dodano przycisk „Otwórz aplikację w izolacji” w /os/build. Wyświetla
  rzeczywisty HTML z aplikacji i źródła JS/CSS tej samej paczki w ramce
  o nieprzezroczystym origin. Token właściciela pozostaje w rodzicu.
  Nowy POST /api/package-runs/preview uwierzytelnia właściciela, weryfikuje
  checksumę, UUID i stałą ścieżkę GET / lub /api/nazwa?parametry.
- PreviewRunner używa tej samej izolacji Docker (runc, nonroot, read-only,
  network none, bez GPU/socket/portów hosta, 1 CPU/512 MiB), ale własnego
  zaufanego harnessu. Każde żądanie tworzy i usuwa kontener; brak sesji,
  zapisu i POST. Proces aplikacji nie jest importowany ani wykonywany na hoście.
  Globalny slot, raport i niepewne sprzątanie korzystają z PackageRun.
  `previewed` to wykonanie HTTP, nie zaliczenie testów ani akceptacja.
- Historia zachowuje 30 ostatnich wykonań testowych i 5 podglądów, więc
  kolejne obliczenia nie wypychają przycisku paczki z historią testów.
  Ustawiono 30 żądań na otwarcie, 120 na paczkę, ograniczone ścieżki i
  odpowiedź do 12 KB. Zamknięcie ramki ignoruje spóźnione odpowiedzi,
  nie udaje natychmiastowego anulowania kontenera.
- Qwen wykonał krótką kontrolę komunikacji i propozycję scenariuszy:
  11.469 s, 429 tokenów wyjścia, 1446 wejścia, wynik
  /tmp/qwen-runner-draft-l2awdapi/draft.json. Uwagi poddano weryfikacji:
  sugestie o deadlocku handshake, konieczności allow-same-origin i błędzie
  kolejności version/close nie były poprawne. Nie osłabiono origin na ich
  podstawie. Przydatne scenariusze odmowy zewnętrznych URL, POST i starego
  kontekstu uwzględniono w kontroli. Nie wykonywano kodu z odpowiedzi modelu.
- Pierwsze próby przeglądarkowe nie przeszły: narzędzie nie obsługiwało
  OOPIF (osobnego procesu ramki Chrome). Po poprawce testu znaleziono
  rzeczywisty problem submit: sandbox bez allow-forms blokował zdarzenie
  formularza mimo działającego skryptu. Dodano allow-forms, zachowując CSP
  form-action none, connect-src none, brak allow-same-origin i top-navigation.
  Wykonania 2–5 potwierdzają jedynie GET strony; nie są dowodem sukcesu UI.
- Pełny test scripts/check_application_browser.py przeszedł po poprawce:
  paczka 5, SHA-256 a009a02fbcc8ade890057747b15380b509e664873d14f3ca8514f67b764c68f6;
  wykonanie 6: GET /; wykonanie 7: GET /api/estimate?hours=8&rate=322,
  HTTP 200 {total:2576.0}, widoczny tekst „Łączny koszt: 2576 zł”;
  wykonanie 8: ujemne godziny, HTTP 400 i widoczny komunikat błędu.
  Test sprawdził też niedostępność parent.document i localStorage, odmowę
  fetch do zewnętrznego URL i POST oraz usunięcie ramki po wylogowaniu.
  Tymczasowy zaufany serwer panelu używał losowego tokena testowego; backend
  aplikacji wykonywał się w rzeczywistych kontenerach, a ich raporty zapisano
  w bazie bez zmiany statusu lub odbioru zadania.
- Backend: 126 testów zaliczonych (12.16 s przed końcową korektą opisów
  i grupowania historii; końcowy powtórny wynik: 126 passed w 12.08 s). check_work_browser.py
  również zaliczony: dotychczasowe scenariusze, 36 kombinacji palet/stron,
  mobilność, logout i statyczny sandbox. node --check trzech nowych/zmienionych
  plików JS oraz git diff --check bez błędów.
- Potwierdzono przez działający serwer 8000 nową wersję /os/build. Kontrola
  docker ps --all --filter label=ai-company.package-runner nie wykazała
  pozostawionych kontenerów. Nie restartowano hosta, Dockera ani cudzych usług.
- Dodano wyraźne ostrzeżenie o file:// do instrukcji nowo pobieranych ZIP
  i kontraktu kolejnych generacji Qwen. APPLICATION_FACTORY.md dokumentuje
  korzystanie, limity i różnicę między podglądem a hostingiem. Stary plik
  index.html nadal nie jest samodzielną aplikacją offline. To ograniczony
  profil bezstanowy, nie uniwersalne wdrożenie ani środowisko wrogiego kodu.

## 2026-09-13 — pliki Qwen, izolowane testy i wydania aplikacji

- Na jawne zlecenie właściciela uruchomiono pierwszy ograniczony proces
  budowy aplikacji. Wykorzystano istniejące Task, delegacje, LocalInference,
  paczki Artifact i odbiór właściciela. Nie tworzono równoległej roadmapy.
- Profil python-web-v1: Qwen zwraca wyłącznie JSON z app.py, test_app.py,
  index.html, README.md i opcjonalnymi style.css/app.js. Dopuszczony tylko
  etap wykonawcy. Walidacja odrzuca duplikaty JSON, ścieżki wychodzące poza
  paczkę, nadpisanie harnessu, puste/brakujące pliki i nadmiarowe polecenia.
  Zapis źródeł, próby modelu i pochodzenia jest atomowy. Sam zapis nie wykonuje kodu.
- Rozszerzono UI Centrum realizacji o generowanie źródeł i opcjonalne
  automatyczne uruchomienie testów po ich zapisie (jawny checkbox).
  Nowy /os/build dostępny z głównego pulpitu i realizacji: wybór wersji,
  potwierdzenie wykonania, historia, tekstowe logi, odzyskanie slotu i ZIP.
  Zachowane motywy, powrót, token tylko w pamięci karty, CSP i oddzielny klient.
- Qwen wykonał dwa zadania wykonawcze: szkic harnessu (13.036 s, 1058 tokenów),
  następnie kompletną aplikację z testami (111.254 s, 2998 tokenów, 949 wejścia).
  Draft harnessu: /tmp/qwen-runner-draft-l46q7ko2/draft.json. Przed integracją
  niezależnie poprawiono brak limitów logu, możliwość sukcesu przy zerze testów,
  importy, obsługę HTTP i zakończenie procesów. Nie wykonano szkicu na hoście.
- Obraz już lokalny: python:3.10-slim,
  sha256:bef522938ef068e9fe7c1f078b1eb929cf32bbb2047b8e67723996c1e050e6e9.
  Zweryfikowano brak wolumenów obrazu, dostępne seccomp i AppArmor. Bez pull,
  instalacji zależności, zmiany demona, sterowników, sieci hosta i usług Vast.ai.
- Kontener: lokalny Docker/runc, UID/GID 65534, network none, no-new-privileges,
  cap-drop ALL, read-only root i źródła, tmpfs 32 MiB, 1 CPU, 512 MiB RAM,
  brak dodatkowego swap, 64 PID, ograniczenia plików/logów, alarm 35 s wewnątrz
  i transport do 45 s. Bez GPU, docker.sock, portów, repozytorium i sekretów.
  Granice kontenera nie wystarczą dla celowo wrogiego kodu/kernel exploitów.
- Addytywna tabela package_runs: UUID i konkretny checksum paczki, rezerwacja
  jednego slotu, raport testowy, stan niepewnego sprzątania, max 3 próby wersji.
  Nie ma blokady SQLite podczas programu. Sprzątanie dotyczy wyłącznie losowej
  nazwy i zgodnej własnej etykiety; brak ogólnego kill/prune. Dane tymczasowe
  usuwane, oryginalne źródła pozostają w SQLite i pobieranych paczkach.
- Udany znany canary: 4 testy (non-root, brak socketu Dockera, brak zapisu
  źródeł, brak sieci zewnętrznej), health, HTML i odmowa dostępu do źródeł.
  Wszystkie dziesięć kontroli profilu pozytywne. Własny kontener usunięty.
- Próby negatywne: zawieszony test przerwany po 15 s, exit 1; plik bez testów
  również exit 1. Obie próby niezaliczone zgodnie z oczekiwaniem; kontenery
  usunięte. Ostatnie docker ps z własną etykietą zwróciło pusty wynik.
- Rzeczywisty pilotaż: projekt #5 „Pilotaż fabryki aplikacji — kalkulator
  zakresu”, zadanie #45, generowanie #2, paczka #5, wykonanie testów #1,
  raport #7. Pierwszy etap nowego pilota świadomie skonfigurowano jako builder
  z kompletną specyfikacją wejściową. Nie fabrykowano odbioru poprzednika.
  Pierwsza próba inicjalizacji zatrzymała się przed modelem: opis i delegacja
  nie były jeszcze zsynchronizowane; transakcja wycofana, skrypt poprawiony.
- Qwen wygenerował kalkulator hours × rate, lokalne API, interfejs i 19 testów.
  19 testów, health, HTML i testy ścieżek przeszły w prawdziwym kontenerze.
  Suma paczki a009a02fbcc8ade890057747b15380b509e664873d14f3ca8514f67b764c68f6.
  Wynik nadal awaiting_review, bez sztucznego 100% i bez akceptacji klienta.
  ZIP kandydata zapisano w /home/marcin/ai-company-workspaces/candidate-vmq0lxsm/application-candidate.zip.
  /api/ps po zakończeniu zwróciło models:[]; model wyładowany.
- Wydanie: osobny artefakt po odbiorze dokładnie tych źródeł przez właściciela.
  Wymagany najnowszy pozytywny test w aktualnym profilu; późniejsza porażka,
  zmiana profilu lub odrzucony/niespójny wynik blokuje pobranie wydania.
  ZIP zawiera sources/, delivery.json, test-report.json i instrukcję.
  Rozróżnia akceptację właściciela/klienta i wdrożenie. Rzeczywistego pilota
  nie odebrano automatycznie; ścieżkę zatwierdzonego wydania sprawdzono na
  izolowanej bazie z testową decyzją, nie na danych właściciela.
- Testy: pierwszy zestaw 41 passed / 1 failed — zastany test oczekiwał starego
  dialogu na /os, choć obecnie jest na /os/review; poprawiono trasę testu,
  zachowując kontrolę treści i braku sekretów. Następnie 68 passed / 8.77 s,
  szerszy zestaw 122 passed / 11.79 s. Testy generowania i kontenerów mają
  atrapy adapterów; nie wywołują modelu/Dockera podczas pytest.
- Chrome check_work_browser.py: źródła, retry po 503 z tym samym UUID,
  wersja paczki, pokazanie wyniku i escapowanie logów, czyszczenie tokena,
  mobilne granice, delegacje/odbiór, wcześniejszy podgląd i 36 palet — zaliczone.
  API tego testu symulowane, GPU Chrome wyłączone. Nie jest to odbiór wizualny
  aplikacji napisanej przez Qwen. node --check work.js/build.js i git diff
  --check bez błędów.
- Dokumentacja: APPLICATION_FACTORY.md oraz aktualizacje indeksu, WORKBENCH,
  EXECUTION, LOCAL_INFERENCE i ARCHITECTURE. STATUS.md nie edytowano ręcznie.
  Brak wdrożenia produkcyjnego, wysyłania klientom, płatności, pobierania modeli,
  zmian Windows i automatycznego wykonywania kolejnych zadań bez odbiorów.

## 2026-09-13 — zakończony wynajem, rzeczywista inferencja Qwen

- Właściciel jawnie zakończył ograniczenie zasobów Vast.ai. Zaktualizowano
  AGENTS.md i dokumentację wykonania. Bez restartu hosta/Docker, zatrzymywania
  cudzych procesów, instalacji modeli, treningu, płatnych usług i dysku Windows.
- Odczyt GPU: RTX 5090, 32607 MiB VRAM, około 995 MiB zajęte przed próbą.
  Ollama ma lokalny tag qwen3.8:27b (27.3B, Q4_K_M), przypięty digest
  22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643.
  Nazwy lokalnego tagu nie przedstawiamy jako oficjalnej wersji Qwen.
  Pierwszy odczyt GPU nie działał w sandboxie; powtórzony z uprawnieniem działał.
- Nowy loopback-only adapter Ollamy: zweryfikowany tag, stream, brak narzędzi,
  bez sekretów/chmurowych API i przekierowań. Własny proces transportu
  z limitem 180 s, max 32000 znaków, odrzucenie urwanego wyniku. Model
  po odpowiedzi wyładowywany przez keep_alive:0; nie zabijamy demona.
- Addytywna tabela local_inference_runs, owner-only API i historia. Rezerwacja
  jednego slotu bez blokowania SQLite podczas generowania. Deduplikacja UUID
  i pakietu. Kontrola aktualności delegacji przed/po odpowiedzi, Emergency Stop,
  historia ponowień, brak automatycznego retry. Niepewny transport blokuje slot;
  odzyskanie wymaga potwierdzenia bezczynności, a po awarii serwera także deadline.
  Token konkretnego wykonania odrzuca spóźnione odpowiedzi poprzedniej próby.
- Odpowiedź trafia do istniejącego TaskAttempt awaiting_review i artefaktu
  REPORT z checksumami, modelem i metrykami. Zadanie nie jest automatycznie
  ukończone i nie otrzymuje procentów za sam tekst. Runner kodu nadal nieaktywny.
- Centrum realizacji: rzeczywisty przycisk Qwen, historia, odczyt wyniku,
  anulowanie oczekującego wpisu i jawne przygotowanie retry bez uruchomienia.
  Stara kolejka symulacyjna zachowana i wyraźnie oddzielona. Treść renderowana
  przez textContent; czyszczenie po wylogowaniu, token tylko w pamięci karty.
- Rzeczywista krótka próba: 16.144 s, 149 wygenerowanych tokenów. Zawierała
  nadmierną deklarację jakości, więc nie traktowano jej jako odbioru produktu.
- Utworzono jeden autoryzowany wewnętrzny projekt #4 „Pilotaż Qwen — standard
  odbioru działu jakości”, cztery zadania, istniejące role i delegacje. Pierwszy
  etap #41: pierwsza próba odrzucona (brak TaskAttempt); oddzielna diagnoza
  potwierdziła truncated_output przy 1536 tokenach. Nie ukryto niepowodzenia.
- Zwiększono limit odpowiedzi do 4096 i kontekst do 16384, nadal 8 wątków
  i timeout 180 s. Jedno jawne retry z zachowaną historią: 21.098 s,
  769 tokenów wejścia, 1423 generowania, done_reason stop. Run #1, TaskAttempt
  #2, checksum 3629a498c49fb5ab7ccab9afeb2169f316aeb2a815b0555d619e3fe30a27757a.
  Stan awaiting_review, odbiór merytoryczny niewykonany. Po próbie /api/ps
  zwróciło models:[], czyli brak załadowanych modeli w chwili kontroli.
- Testy izolowane bez modelu: wcześniejsze 25 passed; przy rozbudowie retry
  1 failed / 26 passed (błędne umiejscowienie fragmentu testu, NameError),
  poprawiono. Szerszy zestaw 96 passed / 11.62 s, po odzyskiwaniu 97 passed /
  11.55 s. Testy obejmują owner/worker, odseparowanie klienta, limity, slot,
  historię, brak wykonania kodu, aktualność instrukcji i istniejące odbiory.
- Chrome check_work_browser.py zaliczony: nowe kliknięcie Qwen i historia,
  związanie checksum, retry bez automatycznego startu, renderowanie tekstu,
  poprzednie delegacje/odbiór, pliki/podgląd i 36 wariantów palet/stron.
  Test miał atrapę API i wyłączone GPU, bez rzeczywistych zapisów z przeglądarki.
- Instrukcja: docs/organization-os/LOCAL_INFERENCE.md; skrypty próby i
  pilotażu mają jawny charakter, nie są schedulerem ani procesem w tle.
  Nie edytowano ręcznie wygenerowanego docs/STATUS.md.
- Końcowa kontrola ochrony przed spóźnioną odpowiedzią: 14 passed / 1.24 s.
  Pierwszy łączony przebieg kontroli zawisł w sandboxie bez wyjścia; przerwano
  tylko własną sesję testową, powtórzono z dozwolonym uprawnieniem. Osobne
  git diff --check i node --check dla work.js przeszły bez błędów.

Rejestr zmian wykonanych przez asystenta. `STATUS.md` pozostaje raportem
generowanym z zadań; ten plik dokumentuje prace, weryfikację i ograniczenia.
Nie wpisujemy tu tokenów, danych klientów ani zawartości ich projektów.

## 2026-09-13 — Centrum dowodzenia i operacyjne szablony działów

- Na prośbę właściciela przebudowano domyślne `/os`: stała nawigacja,
  przegląd, karty działów, realizacja i decyzje. Kule właściciela oraz Brain
  zachowują księżyce i otwierają osobne menu. Natywna warstwa dialogowa
  zapobiega przesłanianiu menu przez kulę. Palety neutralna/zielona/niebieska
  i motywy jasny/ciemny są wspólne z dotychczasowymi narzędziami.
- Poprzedni pulpit zachowano pod `/os/legacy`, Spatial pod `/os/spatial`.
  Przed zmianą utworzono archiwum źródeł UI w
  `docs/ui-archives/before-command-gAFYLo/interface.tar.gz`; pełny spis
  odczytany poprawnie, suma SHA-256 w README obok. Pierwszy podgląd spisu
  przez head zamknął potok; nie był to błąd tworzenia archiwum.
- Nowe `/os/review` i `/os/publishing` udostępniają istniejące funkcje
  odbioru/paczek i publikowania klientowi bez wyszukiwania ich w scenie.
  Poprawiono odnośniki Centrum realizacji, historii oraz menu Spatial.
  Zachowano kontrolę owner-only w API i izolację oddzielnej aplikacji klienta.
  Dodano CSP same-origin, zakaz osadzania w ramkach i awaryjnego wysyłania
  formularza bez JavaScript. Szkielet strony w Centrum realizacji jest
  widoczny dla projektów webowych, nie dla zleceń finansów lub wiedzy.
- Dwanaście istniejących działów otrzymało misję, wejście, wynik i bezpośrednią
  akcję kierującą do prawdziwego liścia. Parametr `unit` wybiera opcję
  formularza dopiero po autoryzowanym odczycie; nie wykonuje POST.
- Nowe zlecenia dostają cztery etapy właściwe dla działu: finanse tworzą
  zestawienie, wiedza instrukcję, marketing ofertę, technologia funkcję itd.
  To deterministyczne szablony planu, nie deklaracja wykonania przez AI.
  Zapisane przy zadaniu kryterium jest przenoszone do delegacji oraz pakietu
  instrukcji; nie jest ponownie wyliczane z aktualnego szablonu katalogowego.
  Historycznych projektów, delegacji, wag i statusów nie zmieniano.
- Interfejs: cztery odczyty API z limitem 8 s, odświeżanie widocznej karty
  co 30 s, brak nakładania odczytów. Jawne błędy, zachowanie ostatniej
  struktury, brak fałszywego 0 przy błędzie, textContent dla danych API.
  Puste miejsce przyszłych mediów z warstwą czytelności; bez pobierania
  obrazów/filmów, nowego WebGL, zależności i stałej pętli renderowania.
- Weryfikacja backendu: najpierw 34 passed (1.55 s), następnie 83 passed
  (9.65 s); końcowy rozszerzony zestaw 114 passed (16.52 s), sekwencyjnie,
  wyłącznie na izolowanych bazach. Zawiera wszystkie 12 szablonów,
  kryteria w delegacjach, idempotencję, kontrolerów, odbiór, kolejkę próbną,
  uprawnienia klienta i zachowane kontrakty stron.
  Po dodaniu CSP: dodatkowe 30 passed (6.39 s) i ponowny check command
  zaliczony z ochroną nagłówków aktywną.
- Check command: 6 motywów, obie kule (rzeczywiste kliknięcia), Escape/fokus,
  wybór działu, wyszukiwanie, powrót, mobile, błędy API, tekst XSS,
  reduced-motion, dedykowany odbiór i publikacje, preselektor formularza.
  Pierwsza asercja XSS nie uwzględniała aktywnego filtra wyszukiwania;
  poprawiono fixture (wyczyszczenie filtra) i kontrola została zaliczona.
- Check work: pierwszy przebieg wykrył mobilny przycisk poniżej 44 px.
  Poprawiono CSS, ponowna kontrola zaliczona: formularz, retry, przydziały,
  pliki, sandbox podglądu, raporty, odbiór, 36 kombinacji palet i stron.
- Check client zaliczony: workflow, decyzje, materiały, historia, publisher
  pod nowym adresem, czyszczenie po wylogowaniu i brak interpretacji HTML.
  Kontrole przeglądarkowe: prywatny Chrome z wyłączonym GPU; operacje
  narzędzi na atrapach API, bez prawdziwych tokenów i zapisów produkcyjnych.
  Zrzuty nowego pulpitu/telefonu/działu/menu obejrzane w
  `/tmp/ai-command-check-bY3QzH`. Kontrole składni JS i git diff --check OK.
- Dokumentacja: COMMAND_CENTER.md, indeks dokumentów i instrukcja archiwum.
  Nie modyfikowano generowanego STATUS.md ani zastanych zmian użytkownika.
- Właściciel dopuścił warunkowe zatrzymanie Vast.ai, gdyby wymagały tego
  zasoby. Ta praca tego nie wymagała: brak zmian usług wynajmu, Docker,
  hosta, GPU, partycji Windows, inferencji i treningu. Symulacja lokalnego
  modelu pozostaje symulacją; autonomiczne wykonanie i izolowany runner
  są nadal osobnym etapem, a nie ukrytą funkcją nowego pulpitu.

## 2026-09-13 — audyt zerowego postępu i fundamenty 12 działów

- Właściciel zgłosił prawie same zera na pulpicie. Odczyt SQLite w trybie
  read-only: 40 zadań, 27 bez projektu (10 COMPLETED, 15 PENDING,
  1 IN_PROGRESS, 1 BLOCKED). Pozostałe zadania są w trzech liściach drzewa.
  Same pliki tworzone podczas prac nie wpływały na procent zadań.
- Rozszerzono kontrakt drzewa o measurement_state, progress_note, źródło
  agregacji, niepełne pokrycie dzieci i zadania rodzica poza średnią dzieci.
  Bez zmiany wag lub starego liczbowego wyniku; brak dowolnej normalizacji
  historycznych statusów i bez automatycznego uznawania plików za ukończenie.
- Dodano liczniki całej gałęzi. Stare bezpośrednie liczniki pozostają dla
  kompatybilności. Pulpit nie pokazuje już braku zadań tylko dlatego, że
  znajdują się one w podobszarze, a nie bezpośrednio na dziale.
- Pulpit i Spatial odróżniają brak pomiaru („—”) od zmierzonego 0%.
  Szczegóły tłumaczą źródło liczby i ograniczenia. Menu właściciela pokazuje
  liczbę zadań bez projektu i informację, że nie jest to pełny audyt firmy.
- Do istniejących kluczy 12 działów dołączono kuratorowany inwentarz
  fundamentów w repozytorium, następny krok i po 3 kryteria gotowości.
  Sprawdzana jest wyłącznie obecność wskazanych plików; nie liczymy z niej
  procentów i nie twierdzimy, że plik testu oznacza zaliczenie testów.
  To metadane istniejącego drzewa, nie nowa roadmapa lub osobna punktacja.
- Nie przypisano automatycznie 27 historycznych zadań: wymagają sprawdzenia
  zakresu i dowodów, odróżnienia prób od rzeczywistych prac oraz uniknięcia
  podwójnego naliczania. Brak takiej migracji jest jawnie opisany.
- Testy: 19 passed w 0.73 s — puste gałęzie, pełne/niepełne pokrycie,
  liczniki potomków, prace na rodzicu, nieprzypisana historia i stare API.
- Check Spatial zaliczony, w tym fundamenty/kryteria, poddrzewo, powrót,
  zoom, połączenia, motywy, mobile i błędy API. Własny Chrome bez GPU;
  render programowy, tylko odczyt danych. Zrzut fundamentów obejrzany
  w /tmp/ai-department-check-UsiWFU.
- Pierwszy zrzut złapał animację otwierania w połowie. Dodano oczekiwanie
  końca animacji i powtórzono kontrolę Spatial; zaliczona, końcowy zrzut czytelny.
- Pierwsza kontrola składni spatial.js była uruchomiona jako CommonJS;
  błąd importu trybu narzędzia, nie aplikacji. Poprawna kontrola
  node --input-type=module --check zaliczona; zwykły JS i diff --check też.
- Dodano DEPARTMENT_MEASUREMENT.md i odnośnik README. Bez zmiany prawdziwych
  zadań/statusów, inferencji, nowych usług, restartów, Docker, Windows
  ani ingerencji w procesy wynajmujących Vast.ai.

## 2026-09-13 — trwała kolejka próbna bez inferencji

- Właściciel potwierdził: prace obciążające CPU/GPU dopiero po jego informacji
  o zakończeniu wynajmu. Zakres tej zmiany: kod i lekkie testy symulacyjne.
- Dodano addytywną tabelę local_model_jobs, owner-only API kolejki i sekcję
  Centrum realizacji. Przygotowana instrukcja może trafić do kolejki próbnej;
  przycisk uruchamia najwyżej jedną stałą odpowiedź symulacyjną.
- Ochrona UUID/wersji paczki, jeden globalny slot, FIFO, do 50 pozycji
  oczekujących/trwających, bez auto-retry i bez blokady zapisu bazy podczas
  odpowiedzi adaptera. Walidacja zakresu przed i po próbie, limit odpowiedzi,
  odrzucanie pustego/NUL/niepoprawnego UTF-8, stałe kody błędów bez sekretów.
- Nie dodano adaptera HTTP ani możliwości włączenia live w API; aplikacja
  zawsze używa FixtureProvider. Testy przekazują własne atrapy. Kontrakt
  adaptera nie jest sandboxem. Obsługa TimeoutError nie oznacza jeszcze
  aktywnego deadline'u dla przyszłego rzeczywistego modelu.
- Odpowiedź pozostaje w historii symulacji, nie trafia do TaskAttempt/Artifact
  ani odbioru rzeczywistego zadania. Nie zmienia statusu/postępu/zgód/kolejki
  Task i nie odblokowuje następnego etapu. Jedna próba na wersję instrukcji.
- Anulowanie tylko oczekującej pozycji. Running po awarii pozostaje blokadą
  do diagnostyki; brak automatycznego odzyskania slotu i ryzyka podwójnego startu.
- API niedostępne dla workerów i klientów, także na osobnym app.client_main.
  Widok czyści historię przy wylogowaniu i wyświetla wynik jako tekst.
- Testy: 27 passed w 2.41 s; końcowa regresja kolejki, delegowania,
  odbioru i stron: 49 passed w 3.54 s. Wszystkie bazy izolowane.
- check_work_browser.py zaliczony z nową symulacją oraz dotychczasowym
  importem/odbiorem, tekstami z tagami, mobilnym formularzem i 36 wariantami
  wyglądu. Wszystkie API symulowane; własny Chrome bez GPU.
  Wyniki kontroli w /tmp/ai-queue-browser-G0QbBD.
- Dokumentacja LOCAL_MODEL_QUEUE.md, WORKBENCH.md, AGENT_HANDOFF.md,
  DELIVERY_SPRINT.md. Składnia JS i git diff --check poprawne.
- Nie uruchomiono Ollamy, inferencji, treningu, runnera kodu, nowych usług
  lub kontenerów. Bez zmian prawdziwych zadań dla testów, restartów hosta/Docker,
  odczytu sekretów, ingerencji w Windows i procesy wynajmujących Vast.ai.

## 2026-09-13 — wspólne wejścia i instrukcje dla lokalnego modelu

- Zgłoszenie: Spatial ma łatwiej dostępne funkcje niż pulpit; potrzebne
  przyspieszenie prac i udział lokalnego Qwen w konkretnych zadaniach.
- Wyrównano stałe skróty /os i Spatial: realizacja, historia, podgląd klienta.
  Dodano podgląd klienta także do menu właściciela w zwykłym pulpicie.
- Wykorzystano istniejące wersjonowane delegacje i instrukcje. Nowy odczyt
  owner-only `/api/tasks/{id}/agent-packets/{packet_id}/prompt` zwraca
  wiadomości system/user i tekst do skopiowania, bez kontaktu z modelem.
  Kontroluje aktualność i integralność zakresu przed eksportem; zawiera
  odebranego poprzednika, uwagi do poprawy oraz uczciwe wymagania dowodów.
- Centrum realizacji: przycisk „Pokaż prompt dla Qwen / lokalnego modelu”.
  Wynik nadal przechodzi istniejący ręczny import oraz osobny odbiór.
  Nie dodano autonomicznego wykonania ani nie przedstawiono eksportu jako treningu.
- Odczyt lokalnej listy modeli: qwen3.8:27b, 17 GB. Brak inferencji, zmian
  wag lub nowych pobrań. Pierwsza próba odczytu zablokowana przez sandbox;
  odczyt po zgodzie udał się. Nie czytano konfiguracji sekretów.
- Testy: 29 passed w 6.72 s (instrukcje, uprawnienia, nieaktualny kontekst,
  brak zapisów eksportu, parytet wejść pulpitu/Spatial, decyzje klientów).
  check_work_browser.py zaliczony: również nowy prompt i wcześniejszy
  import/odbiór, 36 wariantów wyglądu, mobilny widok i bezpieczeństwo tekstów.
  API wyłącznie symulowane, własny Chrome bez GPU. Składnia JS sprawdzona.
- Dokumentacja AGENT_HANDOFF.md i nowy DELIVERY_SPRINT.md: mierzalne wyniki,
  wąski przepływ zamiast równoczesnego uruchamiania wszystkich działów.
  Następne uruchomienie inferencji wymaga określenia rezerwy CPU/RAM/GPU
  niezależnej od najemców; niskie bieżące obciążenie nie jest taką rezerwą.
- Bez restartów, inferencji, kontenerów, zmian prawdziwych danych dla testów,
  ingerencji w Windows lub wynajem Vast.ai. Dwa wyszukania podały nieistniejące
  ścieżki (app/llm*, nazwa skryptu); odnaleziono istniejące moduły w services.

## 2026-09-12 — czytelne wejścia właściciela i decyzje klientów

- Zgłoszenie właściciela: nieczytelne wejście do historii i mylący kod
  wykonawcy przy próbie obejrzenia panelu klienta ze Spatial.
- Spatial: stałe skróty pod górnym paskiem do historii `/os/clients`
  i nowego `/os/client-preview`, również dostępne w menu właściciela.
- Podgląd właściciela używa istniejącego tokenu właściciela, nie kodu klienta.
  Lista publikacji i wejście do konkretnej publikacji z historii.
  Nie zapisuje nawigacji klienta, nie pozwala wysłać decyzji za niego.
  Przykład bez logowania jest jawnie oznaczony DEMO i nie tworzy rekordów.
- Dodano decyzje o etapach publikacji: accepted / changes_requested,
  jawne potwierdzenie, komentarz, wersja SHA-256 i snapshot etapu.
  Zmiana wersji blokuje nieaktualne wysłanie. UUID zapewnia idempotencję;
  ograniczenie unikalności chroni jeden odbiór etapu na wersję i kod.
- Addytywna tabela client_stage_feedback i osobne API decyzji klienta /
  odpowiedzi właściciela. Kod klienta sprawdzany pod kątem ważności/cofnięcia;
  właściciel odpowiada przez swoją chronioną historię. Odpowiedź nie jest
  nadpisywana. Historia decyzji jest paginowana.
- Klient widzi własną decyzję i odpowiedź przy etapie oraz w historii.
  Zapis decyzji nie zmienia Task, postępu, zgód, finansów ani pracy agentów.
  Nie jest dowodem tożsamości ani podpisem klienta. Osobny app.client_main
  udostępnia tylko API klienta, nie podgląd ani endpointy właściciela.
- Testy izolowane: najpierw 49 passed (17.08 s), następnie 60 passed
  (17.79 s) dla panelu, feedbacku, workflow, uprawnień i stron/nawigacji.
- check_client_browser.py zaliczony: workflow, telefon, zachowanie wyboru,
  teksty z tagami, spóźniona odpowiedź po wylogowaniu, publikowanie,
  wysłanie decyzji i odpowiedź właściciela, demonstracja bez kodu,
  rzeczywisty tryb podglądu na symulowanych publikacjach bez POST.
  Wszystkie API w tej przeglądarce były symulowane; Chrome bez GPU.
  Zrzuty `/tmp/ai-client-review-xkty7b`; obejrzano demo oraz formularz decyzji.
- Sprawdzono składnię JS i git diff --check. Jeden odczyt rg wskazał
  nieistniejącą ścieżkę spatial.js; ustalono poprawną app/static/spatial/.
  Dokumentacja CLIENT_PORTAL.md uzupełniona o wejścia, granice i API.
- Bez odczytu sekretów, zmian prawdziwych zadań/klientów dla testów,
  inferencji, modeli, nowych kontenerów, usług, restartów hosta lub Docker.
  Procesy Vast.ai i dysk Windows pozostały nietknięte.

## 2026-09-12 — workflow klienta i historia właściciela

- Wymagania: menu workflow po lewej dla klienta, widoczna budowa projektu
  oraz historia projektów i podgląd aktywności po stronie właściciela.
- Przebudowano `/client`: sidebar Workflow/Materiały/Do odbioru, połączone
  karty etapów, wybór etapu, szczegół zakresu/rezultatu/kryteriów/uwag,
  nawigacja poprzedni/następny. Na telefonie menu przechodzi nad treść;
  brak przewijania wnętrz małych kart. Wspólne palety i tryb jasny/ciemny.
- Rozszerzono jawny kontrakt Milestone o stabilny key, description,
  deliverable, acceptance_criteria, review_note oraz blocked. Stare publikacje
  działają z pustymi nowymi polami. Nie dodano automatycznego dostępu klienta
  do Task/Artifact/Agent. Brak treści daje jawny stan pusty, nie fikcyjny postęp.
- Formularz publikacji właściciela ma edytor etapów i odczyt istniejącej
  publikacji do edycji. Każdy rezultat to opublikowany tekst/opis, nie uruchomiona
  aplikacja lub automatyczny zrzut kodu. Odbiór klienta nadal nie jest zapisywany.
- Dodano stronę właściciela `/os/clients`, wejścia z menu właściciela,
  formularza publikacji i Centrum realizacji. Lista udostępnionych projektów,
  wcześniejsze wersje publikacji, cofnięte/wygasłe dostępy i zdarzenia
  nawigacyjne. Historia wewnętrznych zleceń pozostaje również w `/os/work`.
- Addytywne tabele client_publication_revisions i client_portal_activity,
  rejestrowane przez istniejący Base.metadata.create_all. Publikacja i rewizja
  zapisują się w jednej transakcji. Dla dawnych publikacji baseline przy
  pierwszej zmianie; brak wymyślonej historii sprzed wdrożenia.
- Aktywność klienta: zamknięta lista otwarć projektu/workflow/etapu/materiałów/
  odbiorów. Zakres z kodu, etap z serwerowej publikacji, kontrola jej daty,
  ważności i cofnięcia kodu. Bez IP, klawiszy, haseł, dowolnych opisów i tokenów.
  Klient otrzymuje informację przed otwarciem panelu. Zdarzenie to sygnał
  przeglądarki, nie dowód przeczytania lub tożsamości człowieka.
- Maksymalnie jeden zapis aktywności na 2 s i ostatnie 1000 zdarzeń na kod;
  starsze zdarzenia nawigacji są usuwane zgodnie z jawnym limitem. Wersje
  publikacji nie są usuwane. Polling odczytu nie produkuje aktywności.
  Zgłoszenia best-effort, bez fałszywego wskaźnika obecności online.
- Historia owner-only z paginacją: 30 dostępów, 30 rewizji, 50 zdarzeń.
  Osobny app.client_main nadal nie wystawia stron, skryptów i API właściciela.
  Konta z hasłem i płatności pozostają przyszłą funkcją; nie udajemy ich kodem.
- Pierwszy patch odrzucony przez narzędzie (dwie operacje tego samego pliku);
  ponowiono poprawnie. Pierwsza regresja: 25 passed, 2 failed — stare testy
  oczekiwały braku nowych pól w JSON. Dopasowano oczekiwania do rozszerzonego
  kontraktu i dodano test starych snapshotów. Następnie 41 passed.
- Końcowa regresja: 84 passed w 13.67 s, wyłącznie izolowane bazy/tokeny.
  Testy obejmują role i dwóch odbiorców, wersje, baseline, cofnięcie, atomowość,
  limity treści, throttling, limit 1000 zdarzeń i paginację.
- Nowy check_client_browser.py (dwa przebiegi): menu po lewej, workflow,
  materiały/odbiór, zachowanie wyboru i zakładki po aktualizacji/reorder,
  390/768 px, błędy API, treści z tagami, opóźniona odpowiedź po logout,
  historia właściciela; drugi przebieg także wczytanie/edycja/publikacja etapów.
  Zaliczony; wszystkie API symulowane, bez prawdziwych zapisów.
- Obejrzano zrzuty jasnego workflow, wersji telefonicznej i historii właściciela
  w `/tmp/ai-client-workflow-WOnvBW`. Własny Chrome z wyłączonym GPU.
- Składnia trzech JS, kompilacja Pythona i git diff --check zaliczone.
  Dokumentacja CLIENT_PORTAL.md i WORKBENCH.md uaktualniona.
- Końcowy check_work_browser.py także zaliczony: istniejące delegacje,
  instrukcje/odbiór, formularz zlecenia, paczki, eksport, podgląd i 36 wariantów
  wyglądu pozostały sprawne po dodaniu nawigacji do historii klientów.
- Nie odczytywano sekretów, nie zmieniano prawdziwych statusów/zgód/klientów
  w celu testów. Bez treningu/inferencji, kontenerów, wydatków, restartów
  hosta/Docker, zmian sieci, dysku Windows i procesów wynajmujących Vast.ai.

## 2026-09-12 — instrukcje, import wyników, odbiór i rozdzielenie paneli

- Po potwierdzeniu działającego dostępu właściciela dodano kolejny odcinek
  realizacji: wersjonowana instrukcja delegowanego etapu → rzeczywisty wynik
  dostarczony ręcznie → istniejący odbiór właściciela → bramka kolejnego etapu.
- Nowe usługi/API agent_packets wykorzystują Artifact i TaskAttempt; nie ma
  równoległej bazy, migracji ani uruchomionego wykonawcy. Przygotowanie niczego
  nie wykonuje. Import jest oznaczony owner-import, nie jako sesja agenta.
- Profil roli, aktorzy, brief, kryterium, odebrany poprzednik i uwagi do poprawy
  tworzą instrukcję z SHA-256. Przy imporcie następuje ponowna walidacja stanu,
  delegacji, działu, aktorów i kontekstu. Wynik, próba, potwierdzenie i audyt są
  transakcyjne. Identyczne ponowienie nie tworzy kolejnej próby.
- Odrzucenie nie usuwa historii; poprawka dostaje nową instrukcję i próbę.
  Import nie ustawia postępu 100%, zgody ani kolejki. Akceptacja używa starego
  mechanizmu odbioru wersji; nie udaje działania niezależnego kontrolera AI.
- /os/work otrzymał okno instrukcji, pobieranie JSON, opis pochodzenia wyniku,
  formularz importu i odbiór z dowodami. Teksty przez textarea/textContent,
  brak sekretów w localStorage, czyszczenie formularzy, pauza odświeżania podczas
  otwartego okna, kontrola wersji przy decyzji. Zwiększono wersje cache zasobów.
- Na dodatkowe wymaganie właściciela sprawdzono istniejący portal klienta:
  osobna aplikacja ASGI już istnieje, ale tylko czasowy podgląd publikacji.
  Kont z hasłem ani płatności nadal nie ma. Dodano CLIENT_ACCOUNTS_PLAN.md:
  rozdział uprawnień, klient widzi własne zamówienia, dostęp do opłaconego
  zakresu przypisany kontu, a nie token właściciela. Operator i model sprzedaży
  do wyboru przed integracją; brak rzeczywistych płatności i publicznego wdrożenia.
- Dokumentacja AGENT_HANDOFF.md, WORKBENCH.md i CLIENT_PORTAL.md uaktualniona.
- Weryfikacja: pierwsze 30 testów instrukcji/delegacji/odbioru zaliczone.
  Szersza regresja 172 passed w 6.24 s na izolowanych bazach (w tym klient,
  workbench, artefakty, podgląd, eksport i istniejący mechanizm wykonania).
- Chrome check_work_browser.py: import, odbiór, przejście do etapu 2, wiązanie
  wersji, tekst z tagami bez wykonania, okno na 390px i czyszczenie — zaliczone;
  wcześniejszy formularz, paczki, izolowany podgląd i 36 wariantów wyglądu także.
  API w przeglądarce jest atrapą; nie zmieniano prawdziwych statusów użytkownika.
- Kontrola składni JS i Python zaliczona. Bez inferencji, GPU, kontenerów,
  treningu, restartu usług, operacji na dysku Windows i zmian procesów Vast.ai.

## 2026-09-12 — wznowienie budowy

### Stan zastany i poprzedni zakończony krok

- Zachowano istniejącą aplikację FastAPI, SQLite, pulpit `/os` oraz lokalne zmiany.
- Dodano przekazywanie wyników agentów do odbioru właściciela: wynik operacji
  nie oznacza już automatycznie ukończenia zadania.
- Odbiór kontroluje identyfikator próby i SHA-256, zapisuje uzasadnienie,
  wskazane dowody i audyt. Odrzucenie pozwala na kolejną próbę bez kasowania historii.
- Poprzednia weryfikacja: 407 testów zaliczonych; kontrola składni JS i diff bez błędów.
- Odbiór jest ręcznym potwierdzeniem, nie automatyczną oceną jakości produktu.

### Rozpoznanie środowiska i ograniczenie Vast.ai

- Sprawdzono dostępność Docker, bwrap i narzędzi systemowych.
- Odczyt listy obrazów i identyfikatora lokalnego `python:3.10-slim` wykonano
  za zgodą po odmowie dostępu przez sandbox. Nie uruchomiono kontenerów.
- Zapoznano się z oficjalną dokumentacją izolacji Docker (odnośniki w dokumentacji wykonawcy).
- Właściciel potwierdził aktywny wynajem GPU na Vast.ai. Priorytet bezwzględny:
  brak restartów hosta/usług, zatrzymywania kontenerów, użycia GPU, inferencji,
  treningu, zmian sieci i konfiguracji wynajmu.
- Dalsze prace: kod i niewielkie sekwencyjne testy bez GPU i bez Dockera.
  Uruchomienie rzeczywistego wykonawcy wymaga osobnego bezpiecznego okna.

### Bieżący krok

- Budowa wersjonowanych paczek plików projektu jako artefaktów zadań:
  walidacja ścieżek i rozmiarów, sumy kontrolne, pobieranie ZIP oraz audyt.
- Paczka nie jest uruchamiana ani wdrażana; nie podnosi procentu ukończenia.
- Wyniki weryfikacji zostaną dopisane po testach.

### Implementacja paczek

- Dodano serwis `workspace_packages`: walidacja tekstowych plików, niezmienne
  artefakty, odczyt z kontrolą integralności i deterministyczny ZIP.
- Dodano trzy endpointy właściciela: zapis, manifest i pobranie. Brak endpointu
  uruchamiającego i brak powiązania z automatycznym przejęciem zadania.
- Autoryzacja poprzedza odczyt treści żądania; limit strumienia JSON 8 MiB,
  limit plików 1 MiB. Pobieranie wyłącza cache i sniffing MIME.
- Dodano instrukcję użytkowania i zasady ochrony wynajmu w `EXECUTION.md`.
- Pierwszy test: 35 zaliczonych, 1 niezaliczony. Wykryto różnicę serializacji
  UTC między świeżo zapisanym artefaktem a odczytem z SQLite. Naprawiono
  normalizację daty, bez zmiany danych bazy.

### Wynik weryfikacji i przekazanie

- Powtórzony sekwencyjny zestaw: `test_workspace_packages.py`,
  `test_result_acceptance.py`, `test_organization_os_api.py`, `test_execution_api.py`:
  **52 passed in 2.30s**. Testy używały tymczasowych baz, bez GPU i kontenerów.
- `git diff --check`: bez błędów białych znaków.
- Dodano `AGENTS.md`, aby ograniczenie Vast.ai i obowiązek dokumentowania
  obowiązywały również w następnych sesjach.
- Nie restartowano hosta, Docker ani usług wynajmu. Nie wykonywano inferencji,
  treningu, pobierania modeli/obrazów ani operacji na kontenerach klientów.
- Funkcja dostępna przez API i Swagger, jeszcze bez formularza na pulpicie `/os`.
- Do wykonania: panel paczek/odbioru, niezależne kryteria testów, zatwierdzanie
  konkretnej paczki do uruchomienia i izolowany runner. Próba kontenerowa
  pozostaje odłożona do bezpiecznego okna uzgodnionego z właścicielem.

## 2026-09-12 — panel paczek i odbioru w `/os`

- Przeczytano `AGENTS.md`, sprawdzono istniejący JS, szablon oraz kontrakty
  odbioru i paczek. Zachowano dotychczasowy pulpit i dwa centra sterowania.
- W menu złotej kuli dodano **Paczki projektów i odbiór wyników**. Osobny
  moduł JS i arkusz CSS obsługują modalne, responsywne okno właściciela.
- Dodano stronicowaną listę paczek do istniejącego API: autoryzacja właściciela,
  powiązanie z zadaniem, kontrola integralności, maks. 50 pozycji na stronę,
  brak treści plików w odpowiedzi listy i wyłączony cache.
- Panel umożliwia zapis paczki JSON, przejrzenie manifestu i pobranie ZIP.
  Kod nie jest wykonywany. Akceptacja próby agenta pozostaje osobną operacją.
- Formularz odbioru pokazuje wynik jako tekst i wysyła konkretny identyfikator
  próby oraz checksum; wymaga uzasadnienia, dowodów i świadomego potwierdzenia.
- Dodano blokowanie podwójnych operacji, timeout, obsługę konfliktów, błędów
  autoryzacji, pustych danych i spóźnionych odpowiedzi po zamknięciu panelu.
- Token pozostaje wyłącznie w otwartym panelu. Zamknięcie i opuszczenie strony
  czyszczą token oraz prywatne wyniki; żądania nie śledzą przekierowań.
- Po odebraniu wyniku pulpit odświeża stan. Formularz nie jest nadpisywany
  przez automatyczne odświeżanie drzewa.
- Weryfikacja: **42 testy Python zaliczone w 2.13 s**, **8 testów kontrolera
  JS zaliczonych** (Node, symulowane DOM/fetch). Kontrola składni obu skryptów
  oraz `git diff --check` bez błędów. Początkowy `node --test` raportował cały
  plik jako jeden test; bezpośrednie uruchomienie pliku potwierdziło 8 scenariuszy.
- Testy używały tymczasowej bazy, bez modeli, GPU, kontenerów i zmian usług
  wynajmu. Nie wykonywano prawdziwych decyzji właściciela ani zapisów paczek
  do jego roboczej bazy.
- Ograniczenia: wybór zadania przez ID; brak automatycznego uruchamiania paczek,
  brak związania odbioru próby z konkretną paczką; brak wizualnego testu
  przeglądarkowego. To funkcjonalny panel, nie nowy silnik sceny 3D.

## 2026-09-12 — rozpoznanie spowolnienia pulpitu

- Po zgłoszeniu właściciela przejrzano renderowanie okien, połączeń SVG,
  animacje CSS i sposób pobierania danych. Bez zmian kodu aplikacji.
- Dwa zwykłe odczyty lokalnego API (nie benchmark): `/overview` 200 w 4.471 ms,
  `/tree` 200 w 59.378 ms. Sandbox początkowo blokował połączenie; powtórzono
  odczyty za zgodą poza sandboxem. Nie uruchamiano dodatkowego serwera.
- Kod na każdym `pointermove` przebudowuje wszystkie linie SVG, przeplata
  odczyty geometrii z modyfikacjami DOM. Nie ogranicza tych operacji do jednej
  aktualizacji na klatkę. To kandydat na przyczynę szarpania przy przeciąganiu.
- Co 30 sekund `renderTree` odtwarza wszystkie okna nawet bez zmian danych.
  Jednocześnie działają animowane, filtrowane linie, szerokie rozmycia tła,
  rozmycia okien, cienie i animacje obu kul.
- Czasy API nie wskazują w tej próbce na wielosekundową zwłokę backendu.
  Prawdopodobne obciążenie warstwy renderowania wymaga potwierdzenia profilem
  w przeglądarce; nie zmierzono FPS i nie przypisano winy procesom Vast.ai.
- Linux już hostuje aplikację. Zmiana opakowania przeglądarkowego na desktop
  sama nie usuwa kosztu algorytmu rysowania ani nie gwarantuje płynności.
- Kolejne możliwe poprawki: trwałe elementy SVG, grupowanie odczytów geometrii,
  jedna aktualizacja na klatkę, aktualizowanie tylko zmienionych okien i
  zatrzymanie animacji niewidocznych pod panelem/na nieaktywnej karcie.
- Ochrona wynajmu zachowana: brak benchmarków, GPU, inferencji, kontenerów,
  restartów lub zmian usług. W tym kroku zapisano tylko raport diagnostyczny.

## 2026-09-12 — przebudowa Studio i panel klienta

### Zakres i decyzje właściciela

- Właściciel zlecił przebudowę, płynność, motyw jasny/ciemny, usunięcie
  zasłaniania menu przez Brain i osobny panel klienta.
- Przekazał referencję futurystycznego pulpitu. Przyjęto cofnięte, przygaszone
  okna nieaktywne i kolorowy, czytelny pierwszy plan. Nie kopiowano stockowego
  obrazu ani znaku wodnego do aplikacji.
- Dopuszczono użycie GPU do grafiki; zaktualizowano `AGENTS.md`. W tym etapie
  żadne testy GPU nie były potrzebne. Wynajem pozostaje chroniony.
- Właściciel potwierdził samodzielne kontynuowanie pracy. Nie zmienia to
  wymagań sandboxa ani uprawnień do zewnętrznych publikacji/zobowiązań.

### Implementacja

- Przeczytano kod, uprawnienia i ograniczenia repozytorium. Sprawdzono MDN
  dotyczące cyklu renderowania, natywnej warstwy UI i ograniczania ruchu.
- Zastąpiono arkusz i kontroler sceny. Okna pozostają w DOM według klucza,
  a tylko zmieniona zawartość jest aktualizowana. Stan otwarcia jest zachowany.
- Linie SVG pozostają w DOM, relacje są deduplikowane. Ruch myszy trafia do
  jednej aktualizacji na klatkę; geometria czytana jest grupowo.
- Usunięto stałe animacje oraz rozmycia całych warstw. Polling nie pracuje
  na ukrytej karcie, ma timeout i nie nakłada żądań. Częściowa awaria API
  zachowuje dostępne dane i pokazuje ostrzeżenie.
- Menu właściciela i Brain używają natywnego dialogu ponad sceną. Dodano
  skrót właściciela w pasku, aby duże okna nie odcinały dostępu do sterowania.
- Dodano przywracanie układu, zamknięte okna w dolnej liście, filtrowane
  powiadomienia działów i responsywny układ. Efekt głębi jest CSS, nie WebGL.
- Dodano wspólny motyw ciemny/jasny dla pulpitu, odbioru, publikacji i klienta;
  tylko preferencja motywu trafia do localStorage.
- Dodano `ClientShare`, chronione operacje właściciela, wygasające i odwoływalne
  kody klienta oraz jawnie publikowane snapshoty. Kod jawny zwracany jest
  tylko przy utworzeniu; baza przechowuje hash. Nie utworzono rzeczywistego
  dostępu klienta ani przykładowych danych w roboczej bazie.
- Dodano `/client` i zarządzanie publikacją w menu właściciela. Klient widzi
  wyłącznie przygotowaną treść. Brak automatycznej publikacji wewnętrznych danych.
- Przygotowano `app.client_main:app` jako osobną powierzchnię ASGI bez
  wewnętrznych endpointów. Nie uruchomiono nowej usługi ani portu. Starego
  `app.main` nie wolno traktować jako bezpiecznej usługi publicznej.

### Kontrole i ograniczenia

- Pierwsza zbiorcza łatka odrzucona przez `apply_patch` (podwójna operacja na
  tym samym pliku). Podzielono ją i zastosowano; odrzucona łatka nie zmieniła plików.
- Regresja po pierwszej przebudowie: 42 testy Python i 8 testów JS zaliczonych.
- Po dodaniu klienta: 59 testów Python zaliczonych w 3.11 s.
- Krótki Chrome headless z osobnym profilem i `--disable-gpu`: potwierdzono
  12 okien, 22 unikalne połączenia, zachowanie tożsamości DOM, menu ponad Brain,
  panel odbioru, oba motywy i brak poziomego przepełnienia przy szerokości 390px.
- Rozszerzony test wykazał zbyt wczesną asercję czyszczenia kodu po `close()`:
  zdarzenie dialogu jest asynchroniczne. Dodano oczekiwanie na ten stan.
  Powtórzenie zaliczone: dodatkowo 20 zdarzeń ruchu planuje jedną klatkę,
  działa dialog publikacji, wylogowanie klienta i bezpieczne renderowanie
  tekstu zawierającego HTML. Dane demonstracyjne klienta były symulowane
  wyłącznie w osobnym kontekście przeglądarki.
- Zrzuty robocze: `/tmp/ai-company-ui-check-5pmAdO/`; obejrzano pulpit jasny,
  ciemny i warstwę menu. To nie pomiar FPS ani obietnica płynności na każdej konfiguracji.
- Zamknięto tylko własne procesy Chrome testu. Nie restartowano systemu,
  Docker ani wynajmu. Nie instalowano bibliotek/obrazów, nie używano modeli,
  nie zmieniano sieci, DNS, zapory ani portów.
- Dokumentacja: `STUDIO.md`, `CLIENT_PORTAL.md`, aktualizacja indeksu i zasad.
  Końcowe wyniki regresji zostaną dopisane po kontroli osobnego modułu klienta.

### Końcowa regresja

- **72 testy Python zaliczone w 3.63 s**: panel klienta (w tym osobna aplikacja
  bez wewnętrznych tras), paczki, odbiór, Organization OS oraz wykonawca.
- **8 testów kontrolera JS zaliczonych**, kontrola składni nowych skryptów
  i `git diff --check` bez błędów.
- Udokumentowane pozostałe prace: wdrożenie klienta z HTTPS/gateway i limitami
  prób, konta klientów/MFA, czat/odbiór klienta, mocniejszy silnik przestrzenny
  jeśli pomiary uzasadnią jego koszt. Te funkcje nie są przedstawiane jako gotowe.
- Ostatni test Chrome zaliczony: dodatkowo potwierdzono, że po aktywacji
  drugiego okna pierwsze wraca do swojej poprzedniej pozycji. Zapisano zrzut
  aktywnego okna i obejrzano mobilny panel klienta na danych symulowanych.

## 2026-09-12 — Spatial lab: kamera sterowana kółkiem i hybryda 3D

### Zakres wykonany

- Po akceptacji właściciela zbudowano osobny `/os/spatial`, zachowując cały
  dotychczasowy `/os` i jego operacje. Dodano link w narzędziach pulpitu.
- Przeczytano zasady repozytorium i stan zastanych zmian; nie scalano ani nie
  kasowano kopii, nie zmieniano danych produkcyjnych ani statusów zadań.
- Sprawdzono oficjalną dokumentację Three.js i wersję npm. Zainstalowano
  lokalnie jedną przypiętą zależność, Three.js 0.186.0, bez lifecycle scripts.
  Zachowano lockfile i licencję. Moduły są kopiowane przez jawny build do
  lokalnych statycznych zasobów — przeglądarka nie kontaktuje się z CDN.
- Rzeczywiste obiekty WebGL: dwie kule, pierścienie, światła, metaliczne
  materiały, wytłaczane ramy. HTML okien przez CSS3DRenderer współdzieli kamerę.
  Nie deklarujemy pełnego 3D compositora: HTML pozostaje nad canvasem.
- Trzy działy z API: strategy, platform, ai-automation. Ich procenty, statusy,
  kryteria/podpunkty i odpowiedzialność nie są fikcyjnymi danymi pokazowymi.
  Połączenia Brain i zależności są warunkowane danymi oraz deduplikowane.
- Kółko nad sceną steruje kamerą; kółko nad treścią okna przewija tylko treść.
  Dodano nawigację przyciskami i klawiaturą, większy pierwszy plan, ograniczone
  przeciąganie z podążającymi liniami, dzwonki, zwijanie, modal szczegółów,
  ukrywanie/przywracanie okien oraz reset sceny.
- Menu właściciela i Brain są oddzielne, w natywnym dialogu ponad obiektami.
  Działają odczyt powiadomień i następnego ruchu; operacje administracyjne
  mają uczciwe odnośniki do pełnego pulpitu. Brak uruchamiania wykonawców.
- Wspólny motyw jasny/ciemny, układ 390px, ograniczenie ruchu, brak ciągłego
  renderowania w spoczynku, limit pixel ratio 1.5, odświeżanie danych 30 s
  na widocznej karcie. Tryb lekki CSS3D/SVG po braku/utracie WebGL.
- Błędy importu i brak API od początku mają komunikaty oraz drogę powrotu;
  częściowe błędy API nie usuwają poprawnie pobranych okien.

### Kontrole, nieudane próby i korekty

- Npm view oraz npm install w sandboxie: EAI_AGAIN. Powtórzono po systemowej
  zgodzie na sieć, pomyślnie. Nie zmieniano DNS ani konfiguracji hosta.
- Pierwszy build vendor oczekiwał plików `.min.js`, których r186 nie zawiera:
  ENOENT. Poprawiono build na rzeczywiste moduły `.js`; ponowny build zaliczony.
  Moduły razem zajmują około 2 MB, bundling/minifikacja pozostaje dalszą optymalizacją.
- Pierwsza kontrola składni wykryła dodatkowy nawias w obliczeniu kamery.
  Poprawiono; kontrola modułów i `git diff --check` przechodzą.
- Trzy jednostkowe testy JS: interpolacja/granice, jednostki kółka,
  połączenia tylko z faktycznych przypisań. Wszystkie zaliczone.
- Pierwszy mały przebieg Python: **5 passed**. Końcowa regresja API,
  klienta, paczek, odbioru, wykonawcy i nowej strony: **73 passed w 2.30 s**.
- Istniejący kontroler odbioru: **8 testów JS zaliczonych**.
- Chrome w sandboxie nie utworzył DevToolsActivePort. Powtórzono z właściwą
  zgodą poza sandboxem, w prywatnym profilu, nadal z GPU wyłączonym.
- Testy kółka dwukrotnie zgłosiły timeout asercji. Poprawiono aktywację strony,
  odsunięto punkt od brzegu i dodano oczekiwanie na klatki CSS3D/compositora
  oraz diagnostykę zdarzeń. W kolejnych pełnych przebiegach kółko działało.
- Przy jednej nieudanej próbie sprzątanie profilu Chrome zgłosiło Directory
  not empty. Włączono ignorowanie błędu sprzątania wyłącznie tego tymczasowego
  profilu, bez przeszukiwania ani zatrzymywania innych procesów.
- Rozszerzony test początkowej awarii API nie otrzymał wstrzykniętego mocka
  przed nawigacją. Dodano `Page.enable` do klienta CDP; ponowny test zaliczony.
- Końcowy Chrome: 3 trwałe okna; kamera reaguje na prawdziwe zdarzenie kółka;
  wewnętrzny scroll nie przesuwa kamery; drag aktualizuje koniec linii;
  powiadomienia, menu, minimalizacja/maksymalizacja/zamykanie/reset działają;
  oba motywy, 390px, reduced motion, brak pętli w spoczynku, częściowy i początkowy
  brak API sprawdzone. WebGL uruchomiony przez **SwiftShader, GPU wyłączone**;
  utrata kontekstu przełącza na działający wariant CSS3D.
- Zrzuty `/tmp/ai-spatial-check/`: obejrzano ciemną i jasną scenę, aktywne
  okno, wersję WebGL i mobilną. To kontrola wizualna/zachowania, nie benchmark
  FPS ani potwierdzenie jakości identycznej z referencyjnymi stronami.

### Bezpieczeństwo i dalszy zakres

- Nie restartowano hosta, Docker, Uvicorna ani wynajmu; nie zatrzymywano
  cudzych procesów. Nie uruchamiano modeli, treningu, kontenerów ani płatności.
- Zamykano wyłącznie Chrome utworzony przez skrypt testowy. UI testy nie
  używały tokenów właściciela i nie wykonywały mutacji API. Dane błędów były
  symulowane wyłącznie we własnym kontekście przeglądarki.
- Dokumentacja: `docs/organization-os/SPATIAL.md`, aktualizacja indeksu.
  Dalsze etapy: odbiór kierunku wizualnego, profilowanie rzeczywistego
  stanowiska, optymalizacja pakietu JS i ewentualne przeniesienie 12 działów.

## 2026-09-12 — Spatial 02: głębia, 12 działów i ruchome centra sterowania

### Wykonane zmiany

- Rozwinięto `/os/spatial` do pełnych 12 działów pobieranych z istniejącego
  drzewa API. Nie tworzono nowych danych, statusów ani deklaracji postępu.
- Zastąpiono krótką scenę długą trasą dokumentu ze sceną przypiętą podczas
  przewijania. Kamera oddala się pomiędzy działami i ponownie zbliża do
  wybranego okna. Zmierzona szerokość pierwszego okna rośnie około 3.04 razy
  między przeglądem a zbliżeniem w testowej rozdzielczości.
- Okna pozostają równoległe do ekranu, bez ukośnej rotacji tekstu. Dodano
  numery rozdziałów, nawigację przez wszystkie działy i przejście do katalogu.
- Kule Właściciel i Brain przemieszczają się z widoku całej organizacji
  do narożnych pozycji pomocniczych podczas zbliżenia. Ich menu animuje się
  od klikniętej kuli/przycisku: otwarcie 320 ms, zamknięcie 200 ms.
  Natywny dialog pozostaje ponad sceną; Escape zamyka menu, a reduced motion
  pomija animację. Nie dodano ciągłej pętli renderującej w spoczynku.
- Dodano katalog działów z wyszukiwaniem, przejściem do sceny i przeglądaniem
  faktycznych podpunktów drzewa. Dane są nadal odświeżane co 30 sekund na
  widocznej karcie; istniejące `/os` i panel klienta pozostają dostępne.
- Obsługa kółka rozdziela przewijanie zawartości okna, nawigacji i dokumentu.
  W zbliżeniu ograniczono widoczne linie do istotnych relacji, zachowując
  ich aktualizowanie przy przesuwaniu obiektów.
- Dokumentacja użytkowa: `docs/organization-os/SPATIAL.md` i `docs/README.md`.

### Weryfikacja i korekty podczas pracy

- Regresja Python (strona, klient, paczki, odbiór, API organizacji i wykonawcy):
  **73 passed w 2.36 s**. Początkowy przebieg w sandboxie utknął; przerwano
  wyłącznie własną sesję testową, ponowienie po zgodzie poza sandboxem przeszło.
- **6 testów JS ruchu** oraz **8 testów JS kontrolera odbioru** zaliczonych.
  Pierwszy test geometrii wykrył `-0` zamiast `0`; znormalizowano współrzędne.
- Rozszerzony Chrome sprawdził 12 okien, długi dokument, przybliżenie,
  rzeczywiste macierze prostych okien, ruch obu kul i animację menu,
  katalog/podpunkty, drag i linie, przyciski okien, oba motywy, widok mobilny,
  reduced motion, trwałość DOM, zatrzymanie renderowania i awarie API/WebGL.
  Końcowy pełny przebieg zaliczony; zrzuty: `/tmp/ai-spatial-check-v2/`.
- Surowe zdarzenia CDP `mouseWheel` powodowały nieregularne błędy scrolla;
  diagnostyka wykazała między innymi zdarzenia `cancelable: false`.
  Uporządkowano centralną obsługę kółka i zmieniono test na pełne gesty myszy
  `Input.synthesizeScrollGesture`. Poprawiono też oczekiwanie na ustalenie
  pozycji sticky oraz punkt wejściowy poza viewportem w jednej próbie.
- Korekta katalogu: usunięto podwójny odstęp kotwicy wynikający z jednoczesnego
  scroll-padding i scroll-margin. Po korekcie test przejścia do katalogu przeszedł.
- Po końcowym teście usunięto zbędny drugi handler kółka na treści okna
  i dopasowano jednostkę PAGE do wysokości treści. Kontrola składni modułu
  i `git diff --check` przeszły; pełny test przeglądarkowy dotyczył stanu
  bezpośrednio przed tym porządkowaniem (ścieżka pixel pozostaje taka sama).

### Ograniczenia i ochrona środowiska

- Chrome działał w osobnym profilu z wyłączonym GPU; WebGL przez SwiftShader.
  To test funkcjonalny, nie pomiar FPS na fizycznym GPU ani test iPhone'a.
- Nie restartowano hosta, Uvicorna, Dockera ani usług Vast.ai. Nie zatrzymywano
  procesów wynajmujących, nie uruchamiano modeli/treningu ani płatności.
- Brak mutacji danych operacyjnych i publikacji zewnętrznych. Rozbudowane menu
  nie nadaje agentom dodatkowych uprawnień. Moduły vendor nadal wymagają
  przyszłej optymalizacji pakietowania; nie zmieniano zależności w tym etapie.

## 2026-09-12 — funkcjonalność: centrum realizacji i pierwszy przepływ do plików

### Cel i zakres

Właściciel zaakceptował początkowy wygląd i poprosił o priorytet dla działającego
systemu. Przejrzano istniejące wykonanie, zadania, odbiór i paczki. Potwierdzono,
że odpowiedź LLM nie stanowi kompletnego runnera aplikacji. Zamiast aktywować
inferencję na zasobach Vast.ai połączono przyjęcie zakresu z istniejącymi
projektami, zadaniami i źródłami do pobrania.

### Zmiany

- Nowe `/os/work`: dostęp właściciela, formularz celu/odbiorców/ograniczeń/
  kryteriów, wybór aktywnego liścia drzewa, lista zleceń, zadania i artefakty.
  Odnośniki dodane do menu Właściciela i Brain; oba dotychczasowe pulpity zachowane.
- `work_orders` wiąże UUID żądania i hash briefu z istniejącymi projektem,
  planem oraz czterema zadaniami. Atomowy zapis i audyt; unikalny UUID zapobiega
  duplikatom przy ponowieniu, inny brief z tym UUID daje 409.
- Etapy: specyfikacja, implementacja, testy, odbiór/przekazanie. Stały szablon,
  nie wynik orkiestratora AI. Role są proponowanymi wykonawcami, nie sesjami modeli.
  Zadania startują niezatwierdzone, z postępem 0 i bez `queued_at`.
- Jawna akcja przygotowania strony tworzy paczkę `index.html`, `styles.css`,
  `brief.json`, `README.md` przez istniejący magazyn źródeł. Własny lokalny
  szablon, treści escapowane, bez JS/sieci/inferencji/instalacji. ZIP dostępny
  przez chronione API. Nie podnosi postępu ani nie oznacza odbioru produktu.
- Nowe API wyłącznie Owner, odczyty no-store, paginacja listy; UI nie zapisuje
  tokena, nie podąża za redirectami, czyści dane po wylogowaniu/pagehide.
  CSP blokuje inline i natywne wysyłanie formularza (ochrona przed query string
  z treścią w razie niedziałającego JS). Formularz nie odświeża się automatycznie.
- Naprawiono migrację kolejki: backfill `queued_at=created_at` tylko przy
  dodaniu kolumny. Wcześniej każde otwarcie repozytorium mogło zakolejkować
  świadomie wstrzymane zadania. Test sprawdza brak zakolejkowania nawet po
  samej zgodzie Owner i dwukrotnym ponowieniu migracji.
- Dokumentacja: `docs/organization-os/WORKBENCH.md`, indeks dokumentacji.
  `docs/STATUS.md` nie edytowano ręcznie.

### Testy i poprawione błędy

- Pierwszy test backendu: **14 passed, 2 failed**. Błąd nazw metody w nowych
  testach (`list_queued` zamiast istniejącej `list_ready`); poprawiono testy.
- Następna regresja: **89 passed w 3.06 s**.
- Po korekcie migracji rozszerzona regresja (centrum, kolejka, repozytorium,
  task API, paczki, odbiór, klient, wykonanie, drzewo, Spatial):
  **126 passed w 4.34 s**. Wszystkie dane testowe w izolowanych bazach.
- Istniejące **8 testów JS odbioru** i **6 testów JS ruchu** zaliczone;
  `node --check` nowego kontrolera i `git diff --check` bez błędów.
- Przy przeglądzie kontrolera poprawiono pobieranie FormData przed blokowaniem
  pól; formularz z disabled polami nie dostarczałby danych. Poprawiono też
  identyfikator istniejącego schematu paczki dla przycisku pobierania.
- Nowy `scripts/check_work_browser.py`: pierwszy przebieg wystartował formularz
  przed wykonaniem defer; dodano oczekiwanie na pełne załadowanie. Kolejny
  wykrył nieescaped newline w JS danych testowych; poprawiono surowy literał.
- Końcowy Chrome: **zaliczony** formularz, ponowienie po 503 z tym samym UUID,
  cztery zadania, przygotowanie paczki, bezpieczne wyświetlanie tekstu z HTML,
  brak overflow przy 390px, motyw, wylogowanie i brak tokenów w web storage.
  API całkowicie symulowane w osobnej karcie; bez produkcyjnych zapisów.

### Granice i kolejny etap

- Zlecenia nie uruchamiają workera. Brak kontrolowanego zwalniania do kolejki,
  inferencji, automatycznych zależności, runnera/testów produktu i publikacji.
  W tej iteracji działający rezultat to zapisany zakres, powiązana praca i ZIP
  szkieletu, nie autonomicznie ukończona aplikacja.
- Następny priorytet: wykonawca konkretnej wersji w wydzielonych zasobach,
  ograniczona kolejka, testy i dowody przed odbiorem. Uruchomienie obciążenia
  modelu/kontenerów wymaga osobnego uzgodnienia wobec aktywnego wynajmu.
- Nie zmieniano GPU, Dockera, sieci ani procesów wynajmujących. Chrome tylko
  własny profil i wyłączone GPU. Nie uruchamiano modeli, pobierania zależności,
  treningu ani płatności; nie wykonano testowych zleceń w produkcyjnej bazie.
- Starsze read API aplikacji nie jest przez ten etap globalnie zabezpieczone;
  nie wystawiano aplikacji do internetu. Nowa tabela jest rejestrowana przez
  istniejący startowy create_all; nie usuwano danych ani nie nadpisywano zmian użytkownika.

## 2026-09-12 — kontrola paczek i trwałe dowody przed odbiorem

### Wykonane

- Dodano ograniczony analizator `app/services/package_checks.py`: integralność
  źródeł, podstawowy profil HTML, lokalne href/src i fragmenty ID, składnia JSON.
  Korzysta ze standardowych parserów, bez wykonywania paczki, shell, inferencji,
  przeglądarki produktu, nowych zależności lub połączeń zewnętrznych.
- Raport ma listę kontroli, problemów i ostrzeżeń oraz jawne ograniczenia.
  `code_executed=false`, `product_accepted=false`; status zadania i procent
  nie zmieniają się. Profil nie jest pełnym walidatorem, audytem ani testem E2E.
- Limity: 400 wyników, 10000 znaczników HTML na plik, 128 poziomów JSON;
  limity istniejącego magazynu paczek pozostają bez zmian. Brak obsługiwanych
  dokumentów lub osiągnięcie limitu nie może oznaczać pełnego zaliczenia.
- Nowe chronione Owner API tworzy i odczytuje raporty powiązane z zadaniem
  oraz konkretną paczką/SHA-256. Wynik zapisany w istniejącym `Artifact`
  typu `TEST_RESULT`, bez nowej tabeli; własna suma i atomowy audyt.
  Ponowny odczyt weryfikuje źródło oraz zgodność raportu z tą wersją.
- `/os/work`: przycisk „Sprawdź pliki”, czytelny raport z problemami najpierw,
  ograniczenia, identyfikatory i suma źródła; przy zapisanych raportach
  „Otwórz raport kontroli”. Dane raportu wyświetlane jako tekst, nie HTML.
  Wylogowanie czyści też treść raportu; wynik konfliktu integralności nie
  pozostawia raportu widocznego jako świeżo zweryfikowanego.
- Dokumentacja `PACKAGE_CHECKS.md`, uzupełnienia `WORKBENCH.md`, `EXECUTION.md`
  i indeksu dokumentacji. Nie edytowano ręcznie generowanego STATUS.md.

### Testy, błędy i korekty

- Pierwsze nowe testy: **20 passed, 2 failed**. Ponowny odczyt SQLite zwracał
  czas bez offsetu, podczas gdy zapis zwracał UTC; ujednolicono serializację UTC.
- Test głębokości JSON wykazał, że limit rekurencji interpretera nie jest
  stałym limitem profilu. Dodano osobne sprawdzenie poziomów przed parserem,
  uwzględniające ciągi i escapowanie, bez zmian limitów procesu.
- Powtórzona regresja analizatora, centrum realizacji, paczek, odbioru,
  wykonania API, drzewa, migracji kolejki i klienta: **111 passed w 3.52 s**.
  Testy obejmują błędne pliki, brakujące odnośniki, integralność, obce zadanie,
  RBAC, limity, brak wykonania dołączonego Python i brak zmiany postępu.
- **8 testów JS dotychczasowego centrum odbioru** zaliczonych.
  `node --check` i `git diff --check` bez błędów.
- Rozszerzony test Chrome zaliczony: formularz i retry, paczka, kontrola,
  ponowny odczyt raportu, traktowanie HTML w komunikacie jako tekstu,
  brak overflow przy 390px, wylogowanie i brak web storage z tokenem.
  Wszystkie API symulowane wyłącznie w osobnym kontekście przeglądarki;
  użyto sztucznego tokena, nie zapisano zleceń ani raportów produkcyjnych.

### Ochrona środowiska i granica rezultatu

- Nie restartowano hosta, Dockera ani procesów wynajmu; nie włączano GPU,
  modeli, treningu, kontenerów, instalacji zależności ani płatności.
  Kontrola UI uruchomiła jedynie własny krótki proces Chrome z wyłączonym GPU.
- Działający odcinek to paczka → kontrola źródeł → trwały raport. Nadal nie
  ma runnera wykonującego kod produktu ani automatycznej akceptacji. Włączenie
  obciążenia modelu lub kontenerów wymaga oddzielnego uzgodnienia zasobów
  poza aktywnym wynajmem Vast.ai. Sumy kontrolne nie zastępują podpisu
  ani ochrony przed administratorem mogącym zmieniać całą bazę.

## 2026-09-12 — miejsce pracy na partycji poza Dockerem

- Właściciel wskazał możliwość wykorzystania istniejących partycji bez danych
  kontenerów. Przeprowadzono odczyt lsblk/findmnt/df oraz DockerRootDir i samych
  punktów montowania istniejących kontenerów; bez czytania danych klientów,
  zmiennych środowiskowych, sekretów i wnętrza wolumenów.
- Pierwszy odczyt Docker w sandboxie: odmowa dostępu do socketu. Powtórzono
  wyłącznie zapytania odczytowe po zgodzie poza sandboxem. Docker root to
  `/var/lib/docker`, partycja `/dev/nvme1n1p3` XFS. Odczyt dwóch istniejących
  kontenerów nie wykazał montowania `/home`; stan jest punktowy, nie gwarantuje
  braku przyszłych zmian konfiguracji.
- `/home` leży na `/dev/nvme1n1p4` ext4, około 335 GiB wolnego przy kontroli.
  Potwierdzono, że obie partycje dzielą fizyczny NVMe: nie ma izolacji I/O.
  Nie montowano ani nie zmieniano pozostałych partycji NTFS na drugim dysku.
- Po potwierdzeniu, że docelowy katalog nie istniał, utworzono
  `/home/marcin/ai-company-workspaces` oraz `packages`, `runs`, `reports`.
  `stat` potwierdził 0700 i właściciela marcin dla wszystkich czterech katalogów;
  findmnt potwierdził właściwą partycję. Dodano README i dokument STORAGE.md.
- To wyłącznie przygotowanie miejsca, bez migracji bazy/paczek, rezerwacji
  dużych plików, kwot, automatycznego eksportu czy włączenia runnera.
  Nie zmieniano fstab, montowań, sieci, Dockera, Vast.ai, GPU ani cudzych procesów.
  Nie uruchamiano kontenerów, inferencji, treningu ani testów obciążeniowych.
- Zweryfikowano niewielki rozmiar nowego katalogu i `git diff --check`.
  Testów aplikacyjnych nie uruchamiano: nie zmieniano kodu aplikacji.
- Zgoda na miejsce dyskowe nie rozstrzyga limitów CPU/RAM/GPU ani izolacji
  procesów. Dokumentacja jawnie rozróżnia katalog od sandboxu i wskazuje
  bezpieczny dalszy zakres implementacji bez uruchamiania modeli.

## 2026-09-12 — działający eksport paczek na dysk Linux

- Po zgodzie na dalszą budowę dodano `WorkspaceStorage`, chronione API
  eksportu/weryfikacji oraz przyciski w `/os/work`. Stały katalog docelowy:
  `/home/marcin/ai-company-workspaces/packages`. API nie pozwala wybrać
  ścieżki na Windows ani innego dowolnego katalogu hosta.
- Wymaganie pozostania na dysku Linux utrwalono w AGENTS.md. Dysku Windows
  nie używano ani nie montowano; nie zmieniano Docker/Vast.ai i hosta.
- Eksporter najpierw weryfikuje istniejący manifest i hash źródła. Każda paczka
  ma katalog task/package/SHA-256, pliki 0600, katalogi 0700 i marker zakończenia.
  Operacje używają deskryptorów katalogów, O_NOFOLLOW i O_EXCL; kontrolują
  urządzenie względem `/home`, właściciela oraz uprawnienia magazynu.
- Limit 500 wpisów oraz kontrola wolnego miejsca: rezerwa 10 GiB plus źródła
  i zapas na metadane. Blokada katalogu ogranicza współbieżność eksportów;
  nie jest twardą kwotą ani izolacją I/O od innych aplikacji.
- Powtórzenie sprawdza pliki, nie nadpisuje. Niepełny zapis, zmiany, dodatkowe
  pliki, symlinki, hardlinki i FIFO powodują odmowę. Brak automatycznego
  kasowania lub naprawiania zawartości. Awaria SQLite po kompletnym zapisie
  pozwala odtworzyć potwierdzenie przy ponowieniu bez ponownego zapisu plików.
- Potwierdzenie w istniejącym Artifact OTHER, zdarzenie workspace_export.
  Bez nowej tabeli/migracji i bez zmiany statusu/procentu/prób zadań.
  Nie uruchamia paczek, modeli, procesów, nowych kontenerów ani publikacji.
- UI: „Zapisz na dysku Linux” i „Sprawdź zapis na dysku”, ścieżka jako tekst,
  nadal Owner-only i bez tokenów w web storage. Zaktualizowano instrukcję
  magazynu, centrum realizacji oraz README katalogu roboczego.

### Kontrole

- Pierwszy przebieg nowych testów: **11 passed w 0.54 s**.
- Dodano przypadki podmienionego katalogu docelowego i awarii bazy po zapisie.
  Końcowa regresja eksportów, kontroli plików, zleceń, paczek, odbioru,
  wykonania API, kolejki, klienta i drzewa: **124 passed w 4.16 s**.
- Rozszerzony Chrome: zaliczone zapis dyskowy i weryfikacja (API symulowane),
  wcześniejsze formularze/raporty, mobile, wylogowanie i bezpieczny tekst.
  Prywatny proces, GPU wyłączone; brak zapisów do właściwego magazynu przez UI.
- Odczyt rzeczywistego magazynu: właściwa ścieżka, około 335 GiB dostępnego
  miejsca, **0 wpisów**. Była to tylko kontrola stanu. Wszystkie próby plikowe
  i scenariusze awarii wykonano na katalogach tymczasowych oraz izolowanych bazach.
- `git diff --check` i `node --check` bez błędów. Nie wystąpiły nieudane
  przebiegi testów w tej iteracji; scenariusze awarii były celowymi testami.

### Pozostające ograniczenia

- Eksport jest sprawdzaną kopią, nie izolowanym środowiskiem wykonania.
  Nie edytować wersji w miejscu; przygotować nową paczkę dla nowych zmian.
- SQLite i filesystem nie są jedną transakcją; niekompletny katalog wymaga
  decyzji właściciela. Równoległe żądania mogą utworzyć więcej niż jedno
  potwierdzenie w bazie, ale nie nadpisują plików eksportu.
- Nie tworzono runnera, kontenerów, inferencji ani treningu. Limity CPU/RAM/GPU
  i ochrona procesów wynajmu nadal wymagają uzgodnionej konfiguracji.

## 2026-09-12 — statyczny podgląd paczek w centrum realizacji

### Wykonane

- Dodano owner-only GET `.../workspace-packages/{package_id}/preview`.
  Zwraca JSON po sprawdzeniu paczki i powiązania z zadaniem, nie publiczny HTML.
  Brak nowej tabeli, zapisów stanu wykonania, automatycznego odbioru i publikacji.
- Profil index.html + lokalne arkusze CSS; ograniczony zestaw znaczników
  i atrybutów, brak URL w HTML, brak aktywnych formularzy, skryptów, SVG i mediów.
  Limit 5000 znaczników, 128 poziomów HTML i 128 KiB CSS; odmowa poza profilem.
- Podgląd w modalnym oknie `/os/work`, wariant szeroki/telefon 390 px,
  numer zadania/paczki, SHA-256 i jawne ograniczenia. Escape, zamknięcie,
  wylogowanie i opuszczenie strony usuwają dokument. Polling pauzuje przy podglądzie.
- Ramka srcdoc z pustym sandbox, opaque origin, bez tokena, skryptów i sieci.
  CSS jako arkusze data:; tylko workbench dopuszcza data: w style-src.
  Nie poluzowano script-src ani polityki portalu klienta. Brak unsafe-inline/eval.
- Dokumentacja PREVIEW.md, instrukcja WORKBENCH.md, EXECUTION.md i indeks docs.
  Sprawdzono oficjalne materiały MDN o srcdoc/sandbox i CSP (odnośniki w PREVIEW.md).

### Testy i problemy napotkane podczas weryfikacji

- Pierwsze nowe testy backendu: **19 passed w 0.43 s**. Następnie dodano
  przypadek pustych atrybutów link i poprawiono ich odczyt bez AttributeError.
- Końcowa regresja podglądu, eksportów, kontroli, zleceń, paczek, odbioru,
  wykonania, kolejki, klienta i drzewa: **144 passed w 4.58 s**.
- JS: **8 testów delivery center + 6 testów ruchu przestrzennego zaliczonych**.
  `node --check` oraz `git diff --check` bez błędów.
- Trzy pierwsze przebiegi rozszerzonego testu Chrome nie przeszły:
  pierwszy zakładał obecność ramki w głównym procesie (`childFrames`),
  dwa następne widziały blokadę `inspector`, a nie dowód blokady `csp`.
  Poprawiono narzędzie: obsługa osobnego procesu iframe, inspekcja w domyślnym
  kontekście ramki, awaryjna blokada Fetch zamiast wyprzedzającego CSP
  Network.setBlockedURLs dla końcowej próby sieciowej.
- Końcowy Chrome zaliczony: realny CSS z dokumentu testowego, brak wykonania
  skryptu celowo wstrzykniętego już za filtrem, SecurityError dostępu do rodzica,
  odmowa sieci przez CSP (nie przez awaryjne przechwycenie), szerokość 390 px,
  Escape, ponowne otwarcie, mobile bez overflow i usuwanie źródeł przy wylogowaniu.
  API symulowane, osobny tymczasowy profil, GPU wyłączone, bez prawdziwych tokenów,
  zapisów zleceń, eksportów i zmieniania rzeczywistych statusów.

### Granice

- To podgląd przekształconego HTML/CSS, nie runner JavaScript/backendu,
  symulator iPhone'a, pełny sanitizer aplikacji ani dowód realizacji briefu.
- CSS jest renderowany w przeglądarce; rozmiar paczki nie daje twardej kwoty
  CPU/RAM. Pełna obsługa obcego kodu wymaga odrębnego środowiska i dalszych testów.
- Nie restartowano usług, nie uruchamiano modeli/treningu/kontenerów,
  nie używano dysku Windows i nie zmieniano konfiguracji Vast.ai.

## 2026-09-12 — widoczne wejście do centrum realizacji

- Zgłoszenie właściciela: nie może znaleźć centrum. W kodzie wejście było
  dostępne tylko w rozwijanym menu Właściciela; sam adres `/os/work` działał.
- Dodano stały odnośnik **Centrum realizacji ↗** pod górnym paskiem zarówno
  `/os`, jak i `/os/spatial`. Nie wymaga załadowania API, otwarcia kuli ani JS.
  Ma opis „Zlecenia · pliki · podgląd stron”, widoczny również na telefonie.
- Zaktualizowano wersje CSS, ustawiono no-store dla HTML `/os`, uzupełniono
  instrukcję centrum. Nie zmieniano danych projektu ani uprawnień.
- Pierwszy przebieg pytest w sandboxie nie zwrócił wyniku; przerwano tylko
  własną sesję testową (kod 130). Powtórzenie poza sandboxem z dopuszczonym
  poleceniem: **18 passed w 0.80 s** (nawigacja i centrum realizacji).
- Chrome z wyłączonym GPU: oba skróty widoczne przy 1440 i 390 px, mieszczą
  się w pierwszym ekranie i prowadzą do `/os/work`, również przy wyłączonym JS.
  Dotychczasowe testy formularza, raportów, eksportów i izolowanego podglądu
  także zaliczone. API podczas testów formularzy symulowane, bez tokenów i
  zapisów produkcyjnych. `git diff --check` bez błędów.
- Nie restartowano Uvicorna, hosta ani usług Vast.ai; dysk Windows nietknięty.

## 2026-09-12 — spójne palety, nawigacja, czytelniejsze Spatial i księżyce

### Zakres zgłoszeń właściciela

- Niespójne zielone/niebieskie panele, potrzeba białego/czarnego tła,
  brak jasnej drogi powrotnej w części widoków oraz zbędne przewijanie kart.
- Dodatkowo podczas pracy: kule Właściciela i Brain mają przypominać planety
  z księżycem pojawiającym się po najechaniu i poruszającym się po orbicie.

### Wprowadzone zmiany

- Jeden theme.js/theme.css dla `/os`, `/os/spatial`, `/os/work`, lokalnego
  `/client`, starszego `/` i `/progress`. Neutralna, zielona, niebieska paleta
  w wersji jasnej/ciemnej. Neutralne tło dokładnie #fff/#000, szare panele.
  Wspólne aliasy kolorów i wyeliminowanie własnego nadpisywania motywu w work.js.
- Publiczne preferencje zapamiętują się między stronami i synchronizują
  między kartami. Tokeny oraz dane robocze nadal nie są utrwalane przez UI.
- Wspólny pasek Wstecz/Pulpit/Paleta/Tryb; Wstecz używa bezpiecznej historii
  z referrerem tej samej domeny, inaczej linku do pulpitu. Wewnętrzny podgląd
  klienta wraca do `/os`; oddzielny client_main nadal ma tylko własny `/client`.
  Oddzielna aplikacja klienta udostępnia nowy plik CSS, nie wewnętrzne endpointy.
- Spatial: skrócone karty bez scrolla i listy podpunktów. W oddaleniu większe
  nazwy/procenty, w zbliżeniu krótki status i metryki. Kółko nad kartą przesuwa
  dokument/kamerę, nie jej wnętrze. Szczegóły do 940 px, większa typografia.
- Historia panelu szczegółów (do 50 wpisów w pamięci), przyciski Wstecz,
  Menu właściciela, Pulpit. Opisane powroty z modalów głównego pulpitu,
  z zachowaniem czyszczenia tokenów przy zamykaniu odbioru/udostępniania.
- Dekoracyjne księżyce CSS w obu widokach przy obu kulach. Hover/focus-visible
  pokazuje orbitę, opuszczenie zatrzymuje animację; reduced motion wyłącza obrót.
  Dekoracja nie przechwytuje kliknięć, nie zmienia logiki ani uprawnień agentów.
  Kolory ram i pierścieni Spatial dopasowane do wybranej palety.
- Instrukcja APPEARANCE.md, aktualizacja SPATIAL.md, WORKBENCH.md i indeksu docs.

### Testy i ograniczenia

- Wstępna regresja: **56 passed w 1.83 s**. Po dodaniu testów wspólnych
  zasobów, nawigacji i portalu: **107 passed w 3.49 s**.
- Dotychczasowe testy JS: **8 delivery center + 6 ruchu przestrzennego** zaliczone.
- Chrome centrum: **36 porównań** (3 palety × 2 jasności × 6 stron), zachowanie
  wyboru i zgodnego tła, mobilny pasek, faktyczny powrót z centrum do pulpitu,
  wcześniejsze testy formularza, paczek, raportów, eksportu i izolacji podglądu.
  Wszystkie wywołania API w tym teście symulowane.
- Chrome Spatial: 12 kart, zoom 3.04×, brak scrolla wewnątrz kart, powrót
  w historii podpunktów, właściciel, oba księżyce (ruch, pojawienie, zniknięcie,
  brak animacji po opuszczeniu), reduced motion, mobile 390 px, przeciąganie,
  awarie API i fallback WebGL zaliczone. Odczyty lokalnego API bez mutacji.
- Pierwsza próba testu Spatial przerwana przez CDP `Position out of bounds`
  w synthesizeScrollGesture. Zastąpiono narzędziową symulację zaufanym
  Input.dispatchMouseEvent/mouseWheel; oba kolejne przebiegi zaliczone.
- Pierwsza komenda node --check dla modułu Spatial używała trybu CommonJS
  i zgłosiła import outside module; ponowna kontrola z --input-type=module
  przeszła. Kontrole theme.js/work.js i git diff --check również zaliczone.
- Pierwszy patch theme.js został odrzucony przez walidację narzędzia
  (delete/add tego samego pliku); użyto poprawnego Update File, bez utraty pliku.
- Obejrzano zrzuty desktop/telefon/księżyc. Artefakty kontroli:
  `/tmp/ai-navigation-review-vL7FMb`. To pliki tymczasowe, nie dowody odbioru
  projektów klientów. GPU wyłączone, WebGL tylko przez programowy SwiftShader.
- Nie zmieniano statusów zadań, danych Windows, wynajmu Vast.ai ani zasobów
  inferencji. Nie restartowano hosta, Docker lub Uvicorna i nie instalowano pakietów.
- Podgląd źródeł zachowuje własny design paczki; nie jest przemalowywany przez
  motyw panelu. Przestrzenna scena pozostaje przeglądarkową nawigacją, nie
  natywnym systemem operacyjnym ani gwarancją czytelności dowolnych przyszłych treści.
# 2026-09-12 — atlas Spatial, niezależny zoom i orbity z przesłanianiem

- Na prośbę właściciela zastąpiono sterowanie długim scrollem wyborem działu
  i niezależnym zoomem. Kliknięcie treści karty/numera wybiera okno; kółko nad
  wybraną sceną przybliża/oddala (65–125%), nie zmienia działu ani scrolla strony.
  +/−, poprzedni/następny, Escape/Home i mapa dają jawne alternatywy sterowania.
  Zoom po ponownym wybraniu przesuniętego okna uwzględnia jego przesunięcie.
- Usunięto sztuczny wielotysięczny odcinek scrolla i globalne przechwytywanie
  kółka. Dialogi zachowują własny scroll, historię i wszystkie dotychczasowe akcje.
- Pulpit i Spatial mają ten sam przyklejony przełącznik u góry. Usunięto
  rozproszone duplikaty. Motywy, palety i nawigacja innych stron zachowane.
- Pulpit: większa typografia i podsumowania, prostokątne nieprzekrzywione okna,
  głębia materiału i większe odstępy między rzędami. Dane i relacje nadal z API.
- Jedna orbita SVG na każdej kuli zamiast kilku pierścieni. Tylna półorbita
  i księżyc są maskowane sylwetką sfery. To projekcja i maska SVG, nie wspólny
  bufor głębokości HTML/WebGL. Ruch tylko przy hover/fokusie widocznej kuli;
  ukrycie karty, brak interakcji i reduced motion zatrzymują pętlę.
- Przeczytano stronę referencyjną https://otsuka-air.jp/ (Chapter 4 Product).
  Odczyt tekstowy nie weryfikuje jej animacji: nie deklarujemy odtworzenia
  jej zachowania 1:1. Wdrożona własna koncepcja „mapa → dział → szczegóły”.
- Kontrole: 107 testów pytest zaliczonych (izolowane bazy); 7 testów matematyki
  Spatial i 8 testów JS centrum odbioru zaliczonych; składnia JS oraz diff --check OK.
- Chrome Spatial (trzy przebiegi): 12 kart, wzrost skali ok. 3.1–3.2×, zachowanie
  selekcji i scrollY przy kółku, brak scrolla kart, oba księżyce przód/tył,
  pojedyncze orbity, ruch kul, menu i historia, przeciąganie/linie, okna,
  reduced motion, mobile 390px, błędy API i fallback WebGL — zaliczone.
  Drugi i końcowy przebieg dodatkowo porównały położenie przełącznika w obu widokach
  (tolerancja 2px), sprawdził menu właściciela desktop i wykonał zrzuty.
- Chrome Work: 36 kombinacji stron/palet/jasności, widoczna nawigacja bez JS,
  powrót, formularz, paczki, eksport, izolacja podglądu i wylogowanie zaliczone.
  API w tym teście symulowane; Spatial odczytywał lokalne API bez mutacji.
- Obejrzano zrzuty desktop/Spatial/telefon/księżyc za kulą w
  `/tmp/ai-atlas-review-YJ5tNL`. Kontrole używały osobnego Chrome z wyłączonym
  GPU (WebGL tylko programowy SwiftShader). Nie jest to pomiar FPS.
- Zaktualizowano SPATIAL.md, APPEARANCE.md i wersje zasobów cache.
  Bez instalacji pakietów, modeli, kontenerów, restartów hosta/Docker/Uvicorn,
  zmian rzeczywistych statusów zadań, procesów Vast.ai ani dysku Windows.
# 2026-09-12 — kierownicy, zespoły działów i trwałe delegacje zleceń

- Na zlecenie właściciela rozpoczęto warstwę wykonawczą na bazie istniejących
  agents/projects/plans/tasks/work_orders i odbiorów; bez równoległego rejestru zadań.
- Dodano profile sześciu ról na główny dział: kierownik, analityk, wykonawca,
  tester, koordynator przekazania, niezależny kontroler. Kontroler i kierownik
  podlegają Brain; pozostałe role kierownikowi. Rejestr nie oznacza sesji AI.
- Dodano owner-only API /api/agent-teams, /initialize oraz
  /api/work-orders/{id}/delegate. Atomowy, idempotentny zapis z audytem,
  bez nadpisywania już przypisanej pracy i bez zmiany statusów/zgód/kolejki.
- Nowa tabela task_delegations wiąże istniejące zadanie z działem, kierownikiem,
  wykonawcą, kontrolerem, poprzednikiem, kopią briefu, kryterium i polityką.
  Rejestrowana w istniejącym Base.metadata; utworzona addytywnie przy starcie.
- Szczegóły zlecenia pokazują aktorów, instrukcję i blokady poprzednika.
  Status completed bez odebranej, spójnej ostatniej próby nie spełnia bramki.
  Zmieniony brief lub przypisanie i wyłączony agent są jawnie sygnalizowane.
- Polityka wykonania pozostaje zamknięta. list_ready i atomowe claim
  wykluczają delegacje także po zatwierdzeniu i zakolejkowaniu starym API.
  Istniejąca kolejka dla pozostałych zadań zachowuje dotychczasowe działanie.
- /os/work: panel zespołów, idempotentne przygotowanie, odczyt rejestru,
  przydział zlecenia i karty delegacji. Tekst nie jest wykonywany jako HTML;
  token i dane zespołów są czyszczone przy wylogowaniu.
- Testy: początkowo 24 testy agent-teams/work-orders, następnie 90 testów
  kolejki/agentów/API/odbiorów — wszystkie zaliczone. Końcowy szerszy zestaw:
  166 passed w 5.64 s. Testy pracowały wyłącznie na izolowanych bazach/tokenach.
  node --check dla work.js i git diff --check również zaliczone.
- Chrome check_work_browser.py: konfigurowanie zespołu, delegowanie,
  widoczny kontroler i blokady, escapowanie briefu, wcześniejsze operacje
  plików/podglądu i 36 wariantów palet/stron — zaliczone. API symulowane,
  własny Chrome z wyłączonym GPU, bez zapisów do rzeczywistych zleceń.
- Po testach wykonano rzeczywistą inicjalizację samych profili/odpowiedzialności:
  72 nowe role, 12 działów; modele nieuruchomione, brak zakolejkowanych zadań.
  Wykorzystano tę samą transakcyjną usługę co chronione API, z lokalną zgodą
  właściciela w tym wątku. Nie odczytywano tokenów ani prywatnych briefów.
- Przed tą zmianą wykonano SQLite .backup (uwzględnia WAL), nie zwykłe cp:
  /home/marcin/ai-company/data/team-setup-backup-zdSxxg/ai_company.db.
  Katalog prywatny z mktemp; PRAGMA quick_check kopii zwróciło ok.
  Nie przywracać całej kopii po nowych zapisach bez uzgodnienia migracji.
- Dokumentacja: AGENT_TEAMS.md, WORKBENCH.md i indeksy dokumentacji.
  Nie modyfikowano ręcznie STATUS.md ani nie zamykano zadań dla testu.
- Bez inferencji, treningu, publikacji, wydatków, nowych kontenerów,
  zmian usług Vast.ai/Docker, restartu hosta lub ingerencji w dysk Windows.
  Dalsze podłączenie modelu/runnera wymaga uzgodnionych zasobów.
