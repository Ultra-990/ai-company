# Kopia interfejsu sprzed Centrum dowodzenia

Utworzona 2026-09-13 przed zmianą domyślnego `/os`.

Archiwum: `interface.tar.gz`.
SHA-256: `13a230ce7e6d8b24b0b529506fd1f4d350508aecdcbb0aac3f8646dfffcb0002`.

Zawartość: `app/templates/organization-os`, `app/static/organization-os`,
`app/static/spatial`. Bez bazy, tokenów, konfiguracji i modeli.
Integralność archiwum sprawdzona przez pełny odczyt jego spisu.

Najprostszy powrót do poprzedniego widoku: `/os/legacy`; Spatial pozostaje
pod `/os/spatial`. Nie trzeba rozpakowywać kopii do działającej aplikacji.

Do porównania źródeł najpierw utwórz osobny katalog tymczasowy przez
`mktemp -d`, rozpakuj tam archiwum i porównaj wybrane pliki. Nie rozpakowuj
bezpośrednio na repozytorium: nadpisałoby to późniejsze zmiany. Przywracanie
tras i kontraktów wymaga oddzielnego przeglądu zgodności i testów.
