"""Deterministic delivery documents. No model, execution or platform access."""
from hashlib import sha256

SCHEMA = 'client-handoff.v2'

EN_GUIDE = '''# Start here — local Python application

## Before running
This is a server application, not a standalone HTML file. Do not double-click
index.html: its buttons may require the running backend.

Extract the release ZIP into a separate project directory. Review sources/README.md
and the source code first. Run only in an approved development environment,
without credentials or sensitive files. Do not run it inside your company panel.
The tested profile targets Python 3.10 and the standard library, without pip packages.
Compatibility with other Python versions has not been established by this report.

## Start
Open a terminal in the extracted sources directory (the one containing app.py).
Check that port 8080 is available. Do not stop unrelated programs to free it.

Linux / macOS:
```sh
HOST=127.0.0.1 PORT=8080 python3 app.py
```

Windows PowerShell:
```powershell
$env:HOST = "127.0.0.1"
$env:PORT = "8080"
py -3.10 app.py
```

Keep the terminal open. In a browser on the SAME computer, open:
http://127.0.0.1:8080

No AI Company owner token or owner account is needed to run these sources.
This profile does not provide customer login, payments or persistent storage.
Stop your own application with Ctrl+C in its terminal when finished.

## Run the included tests
In a separate terminal in sources/:
```sh
python3 -m unittest test_app -v
```
On Windows use `py -3.10 -m unittest test_app -v` instead.
Read test-report.json for the recorded isolated test run. Running the included
tests locally does NOT reproduce the container isolation checks in that report.

## If something does not work
- Empty page / no calculation: use the HTTP address above, not file://.
- Connection refused: inspect your application's terminal; it must still be running.
- Port already in use: coordinate a free port; do not terminate unrelated services.
- Python not found: obtain the agreed Python runtime through your normal IT process.
- Unexpected result: send input, expected output, actual output, and reproduction steps.
  Include the source checksum below, but never passwords, access tokens or private files.

## Scope of evidence
The release passed its recorded automated test profile and was accepted by the owner.
That does not establish every business requirement, visual quality, a full security
audit, production deployment or client acceptance. Review the agreed scope separately.
There is no hosting, automatic publication, support SLA or payment action in this ZIP.
'''

PL_GUIDE = '''# Zacznij tutaj — lokalna aplikacja Python

## Przed uruchomieniem
To aplikacja serwerowa. Nie otwieraj index.html dwuklikiem: przyciski mogą
wymagać działającego backendu.

Rozpakuj ZIP wydania w osobnym katalogu projektu. Przeczytaj sources/README.md
i sprawdź kod. Uruchamiaj tylko w zatwierdzonym środowisku developerskim,
bez sekretów i prywatnych plików, nie w katalogu panelu firmy.
Testowany profil jest przeznaczony dla Python 3.10 i biblioteki standardowej,
bez zależności pip. Raport nie potwierdza zgodności z innymi wersjami Pythona.

## Uruchomienie
Otwórz terminal w rozpakowanym katalogu sources, zawierającym app.py.
Sprawdź dostępność portu 8080. Nie zatrzymuj innych usług, żeby go zwolnić.

Linux / macOS:
```sh
HOST=127.0.0.1 PORT=8080 python3 app.py
```

Windows PowerShell:
```powershell
$env:HOST = "127.0.0.1"
$env:PORT = "8080"
py -3.10 app.py
```

Zostaw terminal otwarty. W przeglądarce na TYM SAMYM komputerze otwórz:
http://127.0.0.1:8080

Do uruchomienia źródeł nie potrzebujesz tokena ani konta właściciela AI Company.
Ten profil nie zapewnia logowania klientów, płatności ani trwałej bazy danych.
Aby zakończyć własną aplikację, naciśnij Ctrl+C w jej terminalu.

## Testy dostarczone z aplikacją
W osobnym terminalu, w sources/:
```sh
python3 -m unittest test_app -v
```
Na Windows użyj `py -3.10 -m unittest test_app -v`.
Zapisany wynik wykonania w izolacji znajduje się w test-report.json.
Lokalne uruchomienie testów NIE powtarza kontroli izolacji kontenera z raportu.

## Rozwiązywanie problemów
- Brak obliczeń / pusta strona: otwórz adres HTTP powyżej, nie file://.
- Brak połączenia: sprawdź terminal własnej aplikacji — musi nadal działać.
- Zajęty port: uzgodnij inny port, nie zamykaj cudzych usług.
- Nie znaleziono Pythona: przygotuj uzgodnioną wersję przez swój proces IT.
- Błędny wynik: przekaż dane wejściowe, wynik oczekiwany i rzeczywisty oraz kroki
  odtworzenia. Dołącz sumę źródeł poniżej, nigdy hasła, tokeny czy prywatne pliki.

## Granice potwierdzenia
Wydanie ma zaliczony zapisany profil testów i odbiór właściciela. Nie oznacza to
potwierdzenia wszystkich wymagań biznesowych, wyglądu, pełnego audytu bezpieczeństwa,
wdrożenia ani odbioru klienta. Osobno sprawdź uzgodniony zakres.
ZIP nie zapewnia hostingu, automatycznej publikacji, SLA wsparcia ani płatności.
'''


def documents(run, package, report, release, acceptance_proof=None):
    """Call only after source/report/current owner release have been validated."""
    if run.profile.get('profile') not in {'python-web-v1','python-web-multifile-v1'}:
        raise ValueError('Instrukcja przekazania wymaga obsługiwanego profilu Python web.')
    binding = (f'\n## Version / Wersja\n\n'
               f'Source SHA-256: {run.package_checksum}\n\n'
               f'Test report SHA-256: {report.checksum}\n')
    guides = {'CLIENT-START-HERE.md': EN_GUIDE + binding,
              'CLIENT-START-HERE.pl.md': PL_GUIDE + binding}
    if run.profile['profile']=='python-web-multifile-v1':
        guides={name:value.replace('unittest test_app -v','unittest discover -s tests -t . -p "test_*.py" -v')
                for name,value in guides.items()}
    from app.services.delivery_summary import build
    delivery_summary, summaries = build(run, package, report, acceptance_proof)
    guides.update(summaries)
    message = (
        'Hello,\n\nI am sharing the local application release for your review. '
        'Please start with CLIENT-START-HERE.md in the attached ZIP, then review '
        'sources/README.md for application-specific instructions. '
        'Start the Python server before opening http://127.0.0.1:8080; '
        'do not open index.html directly.\n\n'
        'DELIVERY-SUMMARY.md lists the delivered files and evidence limits. '
        'The included test-report.json records the automated checks for these sources. '
        'Please also verify the agreed requirements; these checks are not a full '
        'security audit or a production deployment.\n\n'
        'If a change is needed, please share the steps, input, expected result and '
        'actual result, without credentials or private data.\n\n'
        f'Source version (SHA-256): {run.package_checksum}\n'
    )
    return {
        'schema': SCHEMA, 'run_id': run.id, 'package_id': run.package_id,
        'source_checksum': run.package_checksum, 'test_report_checksum': report.checksum,
        'release_checksum': release.checksum, 'owner_accepted': True,
        'sent_to_client': False, 'client_accepted': False, 'deployed': False,
        'message_en': message, 'guides': guides, 'delivery_summary': delivery_summary,
        'document_checksums': {name: sha256(value.encode()).hexdigest() for name, value in guides.items()},
        'files': [{k: v for k, v in f.items() if k != 'content'} for f in package['files']],
        'owner_checklist': [
            'Sprawdź wymagania klienta i wyłączenia — raport testów nie zastępuje ich odbioru.',
            'Sprawdź źródła i materiały przed wysłaniem: brak sekretów, prawidłowe licencje i zakres.',
            'Sprawdź instrukcję aplikacji i dopasuj szkic wiadomości do uzgodnień z klientem.',
            'Dołącz właściwe zatwierdzone wydanie ZIP i sam wyślij materiały na Upwork.',
            'Odbiór klienta i publikacja to osobne działania; ten dokument ich nie potwierdza.',
        ],
    }


def handoff(session, run_id):
    from app.services.package_runner import validated_release
    run, package, report, release, payload = validated_release(session, run_id)
    return documents(run, package, report, release, payload.get('acceptance_proof'))
