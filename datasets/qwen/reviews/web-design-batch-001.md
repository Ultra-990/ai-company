# Przegląd propozycji web-design — 19.09.2026

Recenzent: asystent prowadzący (nie odbiór właściciela/klienta).
Źródło: sześć własnych syntetycznych briefów z
`scripts/draft_web_design_training.py`, lokalny Qwen z przypiętym digestem.
Wynik surowy: `/home/marcin/ai-company-workspaces/qwen-training/web-design-drafts-d7m70f1h/`.
SHA-256 `candidates.jsonl`:
`53ff2c0b57f406be126c699e8871bc89ffca5234c5f0386cb3e5128a7473b250`.
Sześć poprawnych formatów, 112.188 s. To propozycje treści, nie wykonane UI.
Surowe rekordy pozostają pending i nie są eksportowane do uczenia.

## Ustalenia po przeczytaniu wszystkich sześciu odpowiedzi

| Przypadek | Dlaczego odpowiedź surowa nie jest wzorcem |
| --- | --- |
| editorial-architecture | „Kasowanie cache” ma przyspieszać powroty; nie rozróżniono obrazu LCP i obrazów lazy. Alternatywa strona/modal zostawia nierozstrzygniętą nawigację. Brak konkretnych skal typograficznych. |
| orbital-company | Właściciel staje się nieaktywną dekoracją, Brain księżycem zamiast osobnym węzłem. Znikanie księżyca powiązano z przejściem widoku, nie głębią orbity. Sprzeczne układy mobilne. |
| scroll-product | Obrót zastępuje wymagane przybliżanie. Gesty przejmują przewijanie, sztywne 100vh i ukryte dane grożą utratą treści. Kryterium wibracji nie jest przenośne. |
| accessible-media-studio | Angielski zamiast polskiego; disabled Generate ma jednocześnie reagować na kliknięcie. Symulowana próba połączenia i komunikaty wymagają rozdzielenia od rzeczywistych operacji. |
| data-dense-delivery | Brak jednoznacznej blokady nieodebranego wydania, dodana edycja statusów klienta bez wymagania, sprzeczna obsługa klawiatury, nieokreślony pomiar wydajności. |
| kinetic-event | Angielski, niedokończone zdanie lazy-loading pomimo poprawnego JSON/stop; success i czyszczenie formularza bez wysyłki. Potrząsanie błędem koliduje z reduced motion. |

## Odebrane po korekcie

`web-design-orbital-company` i `web-design-kinetic-event` otrzymały nowe,
autorskie odpowiedzi asystenta prowadzącego przy zachowaniu briefu i rodziny.
Nie są odbiorem surowych odpowiedzi Qwena ani samodzielną oceną przez autora-model.
Pozostałe cztery wymagają osobnej korekty; nie zwiększają licznika approved.

Przegląd poprawionej specyfikacji orbitalnej potwierdza: dwa niezależne
przyciski Właściciel/Brain, właściwy kierunek delegacji, czytelne okna,
powiadomienia lokalne dla działu, powrót i fokus, zasłanianie księżyca zgodne
z głębią, rozróżnienie relacji, brak udawanych danych i responsywny fallback.

Przegląd poprawionej specyfikacji wydarzenia potwierdza: język polski,
konkretna hierarchia i siatka, ruch opcjonalny bez kolizji tekstu, brak
fałszywego wysłania formularza, brak kasowania danych, stany błędów i
kryteria dotyk/klawiatura/reduced motion.

Zakres odbioru: **planning/content review**, nie coding. Nie ma wykonanej
strony, testu przeglądarkowego, pomiaru kontrastu/FPS ani oceny Awwwards.
Specyfikacje opisują przyszłe kryteria do sprawdzenia. Nie udają wyników.
Treści są syntetyczne, bez klientów, sekretów i kopiowanych zasobów stron.
Warianty obu rodzin muszą pozostać train; nie wolno użyć ich w holdoucie.
