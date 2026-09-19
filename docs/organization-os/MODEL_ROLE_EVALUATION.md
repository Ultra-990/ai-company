# Dobór modeli do ról — protokół porównania

Stan 2026-09-13: plan porównania zatwierdzony kierunkiem właściciela, bez
automatycznego przełączenia modeli. QLoRA jest metodą dostrajania adaptera
na kwantyzowanej bazie, nie alternatywnym modelem:
[dokumentacja PEFT](https://huggingface.co/docs/peft/developer_guides/quantization).

## Co porównujemy

1. Bazowy Qwen, bez adaptera.
2. Ten sam checkpoint Qwen z adapterem wytrenowanym na sprawdzonym zbiorze.
3. Opcjonalnie inne lokalne modele jako osobny eksperyment po identyfikacji
   ich wag, formatu, licencji i wymagań zasobów.

Obecny adapter `smoke-bui0t39x/adapter-NOT-FOR-PRODUCTION` ma3kroki treningu
na4krótkich przykładach arytmetycznych. Raport: production_ready=false,
quality_improvement_measured=false. Nie nazywamy go specjalistą i nie
przypisujemy do działów. Właściwego porównania firmowej specjalizacji jeszcze
nie przeprowadzono. Dwanaście odebranych przykładów train nie zastępuje
reprezentatywnego zbioru i osobnej walidacji/testów.

## Równe warunki

Efekt adaptera mierzymy w tym samym runtime, checkpointcie, kwantyzacji,
tokenizerze, szablonie rozmowy i budżecie. Wariant bez adaptera versus z nim.
Nie przypisujemy różnicy między Ollama GGUF Q4_K_M a checkpointem HF4bit
wyłącznie QLoRA: to również różne środowiska i formaty wag.
Kolejność przypadków, seedy, sampling, instrukcje, testy i limity zamrażamy
przed pomiarem. Testów nie dodajemy do treningu. Rozwój na błędach pilota
raportujemy osobno od niewidzianego zestawu końcowego.

## Macierz ról

| Rola | Niezależna kontrola | Dodatkowe pomiary |
| --- | --- | --- |
| Analityk zlecenia | Zakres, pytania o braki, poprawna odmowa niewspieranego projektu | Halucynowane ustalenia, JSON, czas |
| Programista | Pliki uruchomione w izolacji, kontrakty API i scenariusze przeglądarkowe | Sukces pierwszej próby, tokeny, pamięć |
| Agent napraw | Rzeczywisty błąd przed zmianą i niezmienione testy po niej | Liczba poprawek, zbędne zmiany, regresje |
| Kontroler jakości | Wykrycie celowo zasianych błędów, bez deklarowania niewykonanych testów | Fałszywe akceptacje i fałszywe alarmy |
| Kierownik / dokumentacja | Spójny plan zależności, instrukcja zgodna z faktycznym artefaktem | Pominięcia, wymyślone funkcje, czytelność |

W każdej roli zapisujemy wszystkie przypadki i porażki, nie tylko najlepszy
wynik. Błąd infrastruktury oznacza niepełną ocenę, nie zero jakości modelu.
Brak odpowiedzi/ucięcie/nieprawidłowy format są osobnymi kategoriami.
Najpierw porównujemy jakość, następnie koszt i szybkość. Kontroler nie może
uznawać własnego werdyktu za dowód wykonania: potrzebny runner i artefakty.

## Przypisanie do pracy

Domyślny Qwen pozostaje bez zmian do czasu dowodu przewagi adaptera w danej
roli i kontroli regresji. Adapter może wygrać jedną rolę i przegrać inną;
nie przełączamy całej firmy na podstawie jednej średniej lub kilku przykładów.
Routing musi wskazywać wersję modelu/adaptera i raport, mieć możliwość powrotu
do bazy oraz respektować te same uprawnienia i limity. Nie zwiększa liczby
równoległych obciążeń GPU automatycznie.

Najbliższe prace: przygotować reprezentatywne dane specjalizacji i osobny
zestaw ról, wytrenować wersjonowany adapter, dodać wykonawcę porównania
base/adapter w tym samym runtime, przeprowadzić pomiar i dopiero przypisać
warianty do ról. Ten dokument nie twierdzi, że porównywarka lub routing już działa.
