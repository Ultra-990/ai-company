# Gotowe komponenty — ocena przed integracją

Przegląd upstream 19.09.2026. To lista kandydatów, nie deklaracja instalacji,
bezpieczeństwa każdej zależności ani jakości Qwena. Nie zastępujemy obecnego
modelu danych, odbiorów, historii i izolacji obcym frameworkiem bez migracji.

| Komponent | Przydatność dla AI Company | Decyzja |
|---|---|---|
| Gitleaks | Kontrola sekretów w snapshotach kodu i historii Git | Użyty lokalnie, przypięte 8.30.1 i SHA archiwum; nie działa jako usługa |
| Aider | Edycja istniejącego repozytorium, mapa kodu, współpraca z lokalnymi modelami | Kandydat do ograniczonego pilota napraw, bez kluczy GitHub i automatycznego push |
| Playwright | Testy UI i użytkowych scenariuszy w Chromium, Firefox, WebKit | Kandydat do uporządkowania obecnych testów CDP; zachować prywatne profile i odcięcie sieci |
| OpenHands / Agent Canvas | Koordynacja agentów i adaptery różnych środowisk wykonania | Ocena architektury, nie instalacja pełnego stosu i nie zastąpienie obecnego panelu |

Źródła pierwotne:

- [Gitleaks](https://github.com/gitleaks/gitleaks) i
  [przypięte wydanie](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1).
- [Aider README](https://github.com/Aider-AI/aider) opisuje mapę repozytorium,
  lokalne modele i integrację Git; [LICENSE.txt](https://github.com/Aider-AI/aider/blob/main/LICENSE.txt)
  wskazuje Apache-2.0.
- [Playwright README](https://github.com/microsoft/playwright) opisuje wspólne
  API trzech silników i testy przeglądarkowe;
  [LICENSE](https://github.com/microsoft/playwright/blob/main/LICENSE) wskazuje Apache-2.0.
- [OpenHands README](https://github.com/OpenHands/OpenHands) opisuje obecnie
  Agent Canvas i lokalne/zdalne backendy; wariant bez sandboxa ostrzega
  o pełnym dostępie do systemu plików. Nie uruchamiamy go na hoście.
  [LICENSE](https://github.com/OpenHands/OpenHands/blob/main/LICENSE) wskazuje MIT.

Przed pobraniem konkretnego kandydata: przypiąć wersję/commit, ponownie
sprawdzić licencję wybranych plików, NOTICE i zależności przechodnie. Nazwa
licencji repozytorium nie jest audytem wszystkich paczek ani modeli. Pobranie
README nie jest zatwierdzeniem instalatora. Obce instrukcje nie nadają uprawnień.

## Kryterium przyjęcia komponentu

Najpierw syntetyczne, małe zadanie w osobnym workspace/kontenerze. Ten sam
brief i zamrożone testy co dla obecnego mechanizmu. Mierzymy powodzenie,
liczbę prób, czas, zużycie pamięci i zakres zmian. Zewnętrzny agent nie może
zmieniać testów odbioru, uprawnień, budżetów ani sam przyznać sobie akceptacji.
Brak tokenów, montowania /home i socketu Dockera do środowiska kodu klienta.

Kolejność proponowanych pilotów: Aider na drobnej naprawie repozytorium;
Playwright na formularzu i API; później ocena części OpenHands, jeśli istnieje
konkretna luka w naszej orkiestracji. Nie instalujemy kilku stosów naraz.
