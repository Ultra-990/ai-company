# Samodzielna praca lokalnych modeli

Właściciel 28.09.2026 polecił kontynuować rozwój do uzyskania samodzielnej
pracy. Przedmiotem oceny jest kompletna realizacja w zdefiniowanym zakresie,
a nie sam poprawny JSON, liczba testów infrastruktury czy liczba rekordów SFT.
Obowiązują reguły autorstwa lokalnych modeli z `AGENTS.md`.

## Kolejność wskazana przez właściciela 29.09.2026

Po potwierdzeniu gotowości modelu właściciel chce rozszerzyć jego umiejętności
w kierunku możliwości asystenta prowadzącego: analiza wymagań, planowanie,
programowanie, testowanie, diagnozowanie błędów i korzystanie z narzędzi.
Każdą kompetencję trzeba sprawdzić na osobnych zadaniach; nie zakładamy
automatycznie równego poziomu modeli ani nie obiecujemy go na podstawie SFT.

Następnie lokalny model ma kontynuować rozbudowę AI Company i zaprojektować
nowy interfejs. Asystent prowadzący rozwija narzędzia/naukę i niezależnie
ocenia pracę, zachowując autorstwo modelu. Szczegółowe instrukcje panelu
klienta i panelu właściciela właściciel przekaże po ukończeniu tych etapów.
Obecne działania nadal dotyczą pierwszego etapu, czyli gotowości modelu.

## Kryterium zakończenia dla każdej usługi

Pięć usług pozostaje zgodnych z `scripts/upwork_qualification.py`: przegląd
techniczny, obrazy wnętrz/Pinterest, odtworzenie ulotki wektorowej, infografiki
produktowe i identyfikacja restauracji. Macierz historycznych dowodów nadal
ma znaczenie, ale samo ustawienie wszystkich pól na `true` nie jest dowodem
samodzielności.

Przed kwalifikacją kompletnego przebiegu wymagamy:

- trzech różnych, zamrożonych przed inferencją briefów końcowych spoza nauki;
- wykonania całego pakietu przez lokalne modele i narzędzia z zachowaniem
  surowych odpowiedzi, wersji kodu, konfiguracji, wejść i hashy artefaktów;
- niezależnej kontroli obowiązkowych faktów, plików, pochodzenia, eksportu
  i jakości właściwej danej usłudze, a także porównania ze wspólną bazą;
- zaliczenia wszystkich trzech pakietów bez ręcznych zmian produktu
  i bez doraźnych podpowiedzi asystenta w trakcie ocenianego przebiegu;
- dwóch zamrożonych prób korekt rzeczywistych błędów, rozpoznanych przez
  system i poprawionych w ograniczonym budżecie bez utraty już poprawnych cech;
- jawnego zatrzymania i raportu przy wyczerpaniu budżetu lub braku danych,
  zamiast oznaczania wadliwego wyniku jako ukończonego;
- niezależnego końcowego przeglądu kompletnych dowodów. Ocena autora
  własnej pracy nie zastępuje tej kontroli.

Wynik dotyczy przetestowanego zakresu, nie dowolnego zlecenia klienta.
Próby rozwojowe, poprawki po komentarzach asystenta i znane egzaminy są
oznaczane osobno. Nie zmieniamy wyników historycznych po rozszerzeniu
kontroli: aktualna ocena powstaje w odrębnym audycie. Nie przenosimy
przykładów egzaminacyjnych do zbioru treningowego.

## Kolejność pracy

Najpierw usuwamy potwierdzone ograniczenia narzędzi i niejasności instrukcji,
następnie zbieramy niezależnie zaakceptowane przykłady pełnych realizacji
i korekt. Trening wag wymaga poprawnych danych, zachowania bazowych wag
i porównania base/adapter na osobnych zadaniach. Adapter bez wykazanej
poprawy nie jest promowany.

Aktualny etap dotyczy infografik: rozdzielone instrukcje poprawiły źródła,
ale kompletne kompozycje pozostają odrzucone. Transformacja źródła była
ograniczona do skali 1,5 i dodatnich przesunięć, co utrudniało uzyskanie
czytelnego dużego produktu przy pustych marginesach oryginalnego płótna.
Nowy wersjonowany kontrakt rozszerza narzędzie bez zmiany samych kształtów;
sprawdzamy go na tym samym źródle i stylu, z niezależnym odbiorem paneli.

Po pierwszych próbach rozszerzonego kontraktu i rozumowania pełny pakiet
ma już czytelny większy produkt. Otwarte problemy to znaczenie linii
wymiarowych, powiązanie materiałów z odpowiednimi częściami i niepotwierdzone
obietnice nagłówków. Następny kontrakt powinien wiązać wskazane przez model
elementy sceny z pomierzonymi granicami produktu/części, bez narzucania
gotowej kompozycji i bez ręcznego poprawiania współrzędnych. Znane błędy
pozostają próbami rozwojowymi; nowe briefy końcowe trzeba zamrozić osobno.

Kontrole funkcjonalnych oznaczeń zostały wdrożone eksperymentalnie
(`--functional-callouts`). Mierzą faktyczną geometrię i widoczną farbę
części; v2 wykrywa także przecięcia łączników. Rozumowanie poprawiło
układ materiałów, a rozdzielenie instrukcji paneli usunęło obcą miarkę
z care. Dwie zaakceptowane poprawki są danymi rozwojowymi. Składanie
zatwierdzonych rewizji (`--assemble-reviewed`, `--reviewed-revision`)
zachowuje literalne SVG i wymaga osobnego odbioru całej paczki.

Istotne próby i wyniki zapisujemy w `docs/WORK_LOG.md`. Historyczna
kwalifikacja przeglądu technicznego nie zostaje automatycznie zamieniona
w potwierdzenie wszystkich kryteriów samodzielnego przebiegu powyżej.
