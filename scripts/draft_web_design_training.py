"""Bounded local proposals for original web-design planning data, never auto-approved.

No scraped websites, client data, generated-code execution, weight updates or deployment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.local_ollama import OllamaProvider, configuration, ensure_idle
from app.services.ui_interaction_contract import UI_INTERACTION_CONTRACT
from scripts.prepare_training_data import unique_object, validate_record

INSTRUCTION = '''Jesteś projektantem interfejsów. Przygotuj oryginalną, konkretną
specyfikację do realizacji briefu, nie kod. Odpowiedz wyłącznie JSON-em w podanym
schemacie, po polsku. Każde pole jest listą 2–5 konkretnych decyzji. Wyjaśnij
hierarchię, typografię, kompozycję i zachowanie, nie tylko kolory i efekty.
Podaj testowalne kryteria odbioru z wejściem i oczekiwanym wynikiem.
Nie deklaruj wykonanych testów, wdrożenia, posiadania licencji ani wygrania nagród.
Nie kopiuj cudzej strony, logo, grafik lub kodu. Zewnętrzne media wymagają praw.
Uwzględnij dotyk, klawiaturę, mały ekran i prefers-reduced-motion. Jeżeli efekt
3D nie zadziała, treść i podstawowe funkcje muszą pozostać dostępne.
To materiał treningowy pending; nie oceniaj sam swojej odpowiedzi jako approved.''' + '\n' + UI_INTERACTION_CONTRACT
FIELDS = ('art_direction', 'layout', 'interactions', 'accessibility', 'performance',
          'acceptance', 'risks')
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': list(FIELDS),
          'properties': {key: {'type': 'array', 'minItems': 2, 'maxItems': 5,
                               'items': {'type': 'string', 'minLength': 12, 'maxLength': 500}}
                         for key in FIELDS}}
# All are train-only, original briefs. No claim that these constitute held-out tasks.
CASES = (
    ('editorial-architecture', 'Strona pracowni architektury: spokojna i luksusowa, '
     'jasny/ciemny motyw, duża typografia, katalog 6 realizacji. Zdjęcia zostaną '
     'dostarczone później. Rozróżnij nawigację, listę projektów i detal. Bez 3D.'),
    ('orbital-company', 'Panel firmy: planeta Właściciel otwiera menu decyzji, '
     'planeta Brain prowadzi do kierowników 12 działów. Księżyc znika za planetą. '
     'Oddziel relacje nadzoru od zależności zadań. Duże czytelne okna, stały Powrót, '
     'powiadomienia w każdym oknie. Efekty nie mogą zasłaniać tekstu.'),
    ('scroll-product', 'Strona demonstracyjna fizycznego produktu: 5 rozdziałów '
     'z płynnym przybliżaniem modelu 3D podczas przewijania. Normalne przewijanie '
     'i skoki do sekcji muszą działać. Zaprojektuj wersję dotykową i brak WebGL. '
     'Nie kopiuj żadnej istniejącej marki.'),
    ('accessible-media-studio', 'Interfejs przyszłego generatora wideo: prompt, '
     'parametry, kolejka, podgląd i pobranie. Backend jeszcze nie jest połączony. '
     'Nie udawaj generowania ani postępu. Zaplanuj błędy, anulowanie i stany puste '
     'oraz oryginalny elegancki wygląd dla twórców.'),
    ('data-dense-delivery', 'Portal klienta: projekt, kamienie milowe, dowody testów, '
     'historia wersji i pobieranie odebranego wydania. Logowanie będzie osobnym '
     'etapem. Zaprojektuj przejrzysty dashboard przy 20 projektach, filtry i detal '
     'zawsze z powrotem do listy. Bez efektów utrudniających pracę.'),
    ('kinetic-event', 'Strona wydarzenia kulturalnego z ekspresyjną typografią '
     'i animacjami, programem i formularzem zapisu. Nie ma usługi wysyłania '
     'formularza. Należy uczciwie pokazać ograniczenie; tekst ma pozostawać '
     'czytelny w ruchu, na telefonie i przy wyłączonej animacji.'),
)


def validate_response(content):
    value = json.loads(content, object_pairs_hook=unique_object)
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        raise ValueError('invalid design fields')
    for items in value.values():
        if not isinstance(items, list) or not 2 <= len(items) <= 5:
            raise ValueError('invalid design list')
        if any(not isinstance(item, str) or not 12 <= len(item.strip()) <= 500 for item in items):
            raise ValueError('invalid design decision')
    return value


def candidate(case, content, reference):
    validate_response(content)
    row = {'version': 'company-sft.v1', 'id': 'web-design-' + case[0],
           'family': 'web-design.' + case[0], 'split': 'train', 'skill': 'planning',
           'source': {'kind': 'synthetic', 'reference': reference,
                      'rights': 'Autorski syntetyczny brief i lokalna propozycja; bez cudzych zasobów.',
                      'privacy_checked': True},
           'messages': [{'role': 'system', 'content': INSTRUCTION},
                        {'role': 'user', 'content': case[1]},
                        {'role': 'assistant', 'content': content}],
           'review': {'status': 'pending', 'reviewer': '', 'reviewed_on': None,
                      'evidence': [], 'note': 'Poprawny JSON nie dowodzi jakości projektu ani działania UI.'}}
    validate_record(row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--limit', type=int, choices=range(1, 7), default=6)
    args = parser.parse_args()
    if not args.generate:
        print(json.dumps({'cases': len(CASES), 'split': 'train', 'generation_started': False}))
        return 0
    config = configuration() | {'num_predict': 2800, 'timeout_seconds': 120, 'format': SCHEMA}
    ensure_idle()
    root = Path('/home/marcin/ai-company-workspaces/qwen-training')
    root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='web-design-drafts-', dir=root))
    report = {'recipe': 'web-design-planning.v1', 'model': config['model'],
              'digest': config['digest'], 'cases': [], 'automatically_approved': 0,
              'training_started': False, 'parameters': {'num_predict': 2800, 'timeout_seconds': 120}}
    print(json.dumps({'output': str(output)}), flush=True)
    started, candidates = time.monotonic(), []
    for case in CASES[:args.limit]:
        if time.monotonic() - started > 600:
            break
        entry = {'id': case[0], 'format_passed': False}
        try:
            ensure_idle()
            result = OllamaProvider(config).complete([
                {'role': 'system', 'content': INSTRUCTION}, {'role': 'user', 'content': case[1]}])
            entry['result'] = result
            candidates.append(candidate(case, result['content'], str(output/'report.json')+'#'+case[0]))
            entry['format_passed'] = True
        except (ValueError, TimeoutError) as exc:
            entry['error_type'] = type(exc).__name__
        report['cases'].append(entry)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        payload = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in candidates)
        (output/'candidates.jsonl').write_text(payload, encoding='utf-8')
        report['candidates_sha256'] = hashlib.sha256(payload.encode()).hexdigest()
        (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'id': case[0], 'format_passed': entry['format_passed']}), flush=True)
    return 0 if len(candidates) == args.limit else 1


if __name__ == '__main__':
    raise SystemExit(main())
