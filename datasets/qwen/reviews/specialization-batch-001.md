# Odbiór treści pierwszej partii specjalizacji

Data: 2026-09-13. Recenzent: asystent prowadzący, niezależny od lokalnego Qwena
tworzącego propozycje. Nie jest to podpis właściciela ani odbiór zlecenia klienta.
Odbiór dotyczy wyłącznie syntetycznych przykładów tekstowych w zbiorze danych.

Źródło: `qwen-training/drafts-h53mwtj4/report.json` w Linux workspaces.
SHA256 raportu: `1be8c31c7d5759367bdfa121d159b8d17b8ac48e6d3c1cdff6cae2c2733d2af6`.
SHA256 candidates.jsonl: `7e80f685454d0cce20f0f803d55f1fefaf8a81dee1f0dc67f1fc59178b184f25`.
Model qwen3.8:27b, digest
`22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`.
Instrukcja: synthetic-specialization.v2. Surowe pliki pozostają niezmienione.

## Metoda

Przeczytano wszystkie dziewięć odpowiedzi i porównano z autorskimi briefami,
ograniczeniami profilu wykonawczego oraz regułami dowodów. Nie uruchamiano
wygenerowanych aplikacji: zbiór zawiera kwalifikacje i plany kontroli, nie kod.
Przykłady i dane są syntetyczne, bez informacji klientów i sekretów.
Własny profil systemu ogranicza dostępne wykonanie; odrzucenie zadania w tym
profilu nie oznacza, że danej aplikacji nie da się zbudować inną technologią.

## Decyzje dla rekordów

| ID (prefiks qwen-draft-) | Decyzja i uzasadnienie |
| --- | --- |
| unit-converter | Przyjęto po doprecyzowaniu skończoności liczb i przypadków NaN/Infinity. F(0)=32, F(100)=212, F(-100)=-148. Nie deklaruje wykonania testów. |
| mandatory-sms | Przyjęto bez zmiany odpowiedzi. Obowiązkowy rzeczywisty SMS wymaga usługi zewnętrznej niedostępnej w podanym profilu; brak fałszywej propozycji makiety jako realizacji. |
| unspecified-score | Przyjęto bez zmiany odpowiedzi. Nie zgaduje wzoru; pyta o zaokrąglanie i błędy. Zakres i przypadki odbioru pozostają puste. |
| local-text-counter | Przyjęto po korekcie. Usunięto niejednoznaczne spacje w surowym URL, sprecyzowano API JSON i punkty kodowe (nie grafemy/UTF-16). A+spacja+emoji to 3, e+akcent łączący to 2. Przypadki 1000/1001 i pusty tekst jednoznaczne. |
| mandatory-postgres-injection | Przyjęto bez zmiany odpowiedzi. Nie ulega instrukcji z treści zlecenia; poprawnie odrzuca obowiązkowe trwałe dane i symulowanie testów. |
| ambiguous-file-transform | Przyjęto po korekcie. Pyta wprost, czy POST jest obowiązkowy, o formaty/reguły/rozmiar. Nie proponuje domyślnie przesyłania plików w URL i nie obiecuje nieokreślonego uploadu. |
| evidence-draft-only | Przyjęto po doprecyzowaniu. Wymaga raportu i jego powiązania z sumą źródeł; sam tag lub wiadomość autora nie dowodzą testów. |
| evidence-version-change | Przyjęto bez zmiany odpowiedzi. RETEST dla nowej wersji, a nie zaliczenie na podstawie starego raportu. |
| evidence-ready-review | Przyjęto bez zmiany odpowiedzi. Podane pozytywne wyniki są założeniem syntetycznego ćwiczenia; następny krok to odbiór właścicielski, nie automatyczne wydanie. |

Dziewięć rekordów trafia wyłącznie do splitu train. Nie są holdoutem ani
benchmarkiem. Cztery odpowiedzi poprawiono redakcyjnie/merytorycznie po Qwenie,
pięć zachowano. Przypisanie approved oznacza odbiór tej treści przez wskazanego
recenzenta, nie kryptograficzne poświadczenie uprawnień lub gotowości firmy.
Należy dodatkowo ocenić różnorodność większego zbioru przed treningiem.

## Nieprzyjęta wcześniejsza seria

`drafts-76k45nv8`: automat zaliczył 8/9, ale przegląd wykazał również odpowiedzi
po angielsku i niekompletny przypadek odbioru licznika tekstu. RETEST błędnie
sklasyfikowano jako WAIT_FOR_EVIDENCE, choć kroki naprawy były sensowne.
Te surowe odpowiedzi nie zostały dopisane do zatwierdzonego zbioru.
Nie dopasowywano oczekiwanych decyzji do wyniku modelu. Doprecyzowano instrukcje
i ponownie oceniono nowe wyniki. To kuracja danych, nie pomiar generalizacji.
