# Struktura organizacyjna wirtualnej firmy

## Właściciel

Definiuje cele strategiczne, zatwierdza decyzje wysokiego ryzyka
i otrzymuje raporty zbiorcze.

## Orkiestrator

Orkiestrator:

- przyjmuje cele,
- dzieli je na projekty i zadania,
- wybiera właściwy pion,
- przydziela zadania,
- monitoruje postęp,
- wykrywa blokady i ryzyka,
- przygotowuje raporty.

## Piony organizacyjne

### Pion techniczny

Odpowiada za architekturę, backend, API, bazę danych, testy i DevOps.

### Pion badawczy

Odpowiada za wyszukiwanie informacji, analizę danych i rekomendacje.

### Pion kreatywny

Odpowiada za grafiki, materiały wizualne i projekty kreatywne.

### Pion operacyjny

Odpowiada za realizację procesów, dokumentację i raportowanie.

## Hierarchia

Właściciel  
└── Orkiestrator  
&nbsp;&nbsp;&nbsp;&nbsp;├── Kierownik pionu technicznego  
&nbsp;&nbsp;&nbsp;&nbsp;├── Kierownik pionu badawczego  
&nbsp;&nbsp;&nbsp;&nbsp;├── Kierownik pionu kreatywnego  
&nbsp;&nbsp;&nbsp;&nbsp;└── Kierownik pionu operacyjnego  

## Role

- `owner` — decyzje strategiczne
- `orchestrator` — planowanie i koordynacja
- `manager` — zarządzanie pionem
- `agent` — wykonywanie zadań

## Zasady

1. Każde zadanie należy do jednego głównego pionu.
2. Każde zadanie ma osobę lub agenta odpowiedzialnego.
3. Zadania zablokowane oznaczamy jako `blocked`.
4. Problemy przekraczające kompetencje agenta eskalujemy do kierownika.
5. Problemy strategiczne i wysokiego ryzyka eskalujemy do Właściciela.
6. Zakończenie zadania ustawia postęp na `100`.
