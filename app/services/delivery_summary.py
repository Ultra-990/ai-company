"""Client-safe, deterministic technical scope. Inputs must be release-validated."""


def build(run, package, report, acceptance_proof=None):
    count = acceptance_proof.get('case_count') if acceptance_proof else None
    if acceptance_proof is not None and (type(count) is not int or not 1 <= count <= 4):
        raise ValueError('Nieprawidłowa liczba potwierdzonych przykładów wydania.')
    files = [{k: f[k] for k in ('path', 'size_bytes', 'sha256')} for f in package['files']]
    summary = {
        'schema': 'delivery-summary.v1', 'profile': run.profile['profile'],
        'source_checksum': run.package_checksum, 'test_report_checksum': report.checksum,
        'file_count': len(files), 'source_bytes': sum(f['size_bytes'] for f in files), 'files': files,
        'recorded_test_profile_passed': True, 'verified_http_examples': count,
        'business_scope_verified': False, 'visual_review_verified': False,
        'full_security_audit_verified': False, 'production_deployment_verified': False,
        'owner_accepted': True, 'client_accepted': False,
    }
    inventory = '\n'.join(f"| `sources/{f['path']}` | {f['size_bytes']} | `{f['sha256']}` |" for f in files)
    examples_en = (f'{count} explicitly selected HTTP example(s) passed for these exact sources.' if count is not None else
                   'No separately selected HTTP acceptance plan is recorded. This is not a claim of zero tests or full requirement coverage.')
    examples_pl = (f'{count} jawnie wybranych przykładów HTTP zaliczono dla dokładnie tych źródeł.' if count is not None else
                   'Nie wybrano osobnego planu przykładów odbioru HTTP. Nie oznacza to braku testów ani pełnego pokrycia wymagań.')
    en = f'''# Delivery summary

## What this package contains

Local Python application sources, launch instructions and the recorded test report.
This inventory describes delivered files, not an automatic inventory of working
business features. Read sources/README.md and compare the result with your agreed
scope. Start with CLIENT-START-HERE.md; do not open index.html directly.

Source version (SHA-256): {run.package_checksum}
Test report (SHA-256): {report.checksum}
Recorded profile: {run.profile['profile']}
Source files: {len(files)}; source bytes: {summary['source_bytes']} (not ZIP size).

| Delivered file | Bytes | SHA-256 |
| --- | ---: | --- |
{inventory}

## Evidence and limits

- The recorded test profile passed for this source version; see test-report.json.
- {examples_en}
- The owner accepted this version. This is not client acceptance.
- The automated checks do not establish full business scope, visual quality,
  a full security audit, production deployment or compatibility with every device.
- Hosting, support commitments, payments and changes of scope are separate agreements.
- This summary did not run new tests or call an AI model. It describes existing evidence.

## If you find an issue

Send the source version above, the affected feature, steps to reproduce, input,
expected output, actual output and your browser/runtime version. Mention whether
the problem repeats and how it affects your work. Remove secrets and personal data
from inputs, logs and screenshots. Do not send passwords or access tokens.

Send the report to your agreed contact; this document sends nothing automatically.
'''
    pl = f'''# Metryka przekazanego wydania

## Co zawiera paczka

Źródła lokalnej aplikacji Python, instrukcje uruchomienia i zapisany raport testów.
Spis opisuje przekazane pliki, nie potwierdza automatycznie działania funkcji
biznesowych. Przeczytaj sources/README.md i porównaj rezultat z uzgodnionym zakresem.
Zacznij od CLIENT-START-HERE.pl.md; nie otwieraj index.html dwuklikiem.

Wersja źródeł (SHA-256): {run.package_checksum}
Raport testów (SHA-256): {report.checksum}
Zapisany profil: {run.profile['profile']}
Pliki źródłowe: {len(files)}; bajty źródeł: {summary['source_bytes']} (nie rozmiar ZIP-a).

| Przekazany plik | Bajty | SHA-256 |
| --- | ---: | --- |
{inventory}

## Dowody i ograniczenia

- Zapisany profil testów zaliczono dla tej wersji; raport znajduje się w test-report.json.
- {examples_pl}
- Właściciel odebrał tę wersję. Nie oznacza to odbioru klienta.
- Kontrole automatyczne nie potwierdzają pełnego zakresu biznesowego, jakości
  wizualnej, pełnego audytu bezpieczeństwa, wdrożenia ani zgodności z każdym urządzeniem.
- Hosting, zobowiązania wsparcia, płatności i zmiany zakresu wymagają osobnych ustaleń.
- Metryka nie uruchomiła nowych testów ani modelu AI. Opisuje istniejące dowody.

## Jak zgłosić problem

Podaj powyższą wersję źródeł, funkcję, kroki odtworzenia, dane wejściowe, wynik
oczekiwany i rzeczywisty oraz wersję przeglądarki/środowiska. Napisz, czy problem
się powtarza i jak wpływa na pracę. Usuń sekrety i dane osobowe z wejścia, logów
i zrzutów ekranu. Nie wysyłaj haseł ani tokenów dostępu.

Przekaż zgłoszenie uzgodnionemu opiekunowi; ten dokument niczego nie wysyła.
'''
    return summary, {'DELIVERY-SUMMARY.md': en, 'DELIVERY-SUMMARY.pl.md': pl}
