"""Bounded source-generation contract. Parsing never executes model output."""
import json

from app.services.multifile_profile import PROFILE, REQUIRED, require_sources
from app.services.package_checks import check_json_depth

SOURCE_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['files'],
    'properties': {'files': {
        'type': 'object', 'minProperties': 7, 'maxProperties': 16,
        'required': sorted(REQUIRED | {'modules/logic.py', 'tests/test_logic.py'}),
        'properties': {name: {'type': 'string'} for name in sorted(
            REQUIRED | {'modules/logic.py', 'tests/test_logic.py'})},
        'additionalProperties': {'type': 'string'},
    }},
}

INSTRUCTION = '''OUTPUT CONTRACT python-web-multifile-v1:
Return ONLY JSON {"files":{"relative/path":"complete source text",...}}.
Required: app.py, index.html, README.md, modules/__init__.py, modules/logic.py,
tests/__init__.py, tests/test_logic.py. Empty __init__.py is allowed.
Python 3.10 standard library only. app.py is the HTTP entrypoint; business logic
belongs in modules/logic.py and separate unittest assertions in tests/test_logic.py.
No immediate server start on import. python app.py must use HOST (default
127.0.0.1) and PORT (default 8080). GET /health returns {"status":"ok"}.
GET / serves index.html from Path(__file__).parent, with UTF-8 and HTML5 doctype.
Use a strict route allowlist. Never serve Python, tests, README, directories or
arbitrary files; unknown/private routes return 404. No external API, pip, accounts,
persistent state, payments, network downloads or host access. Do not invent
unsupported integrations; implement only the agreed stateless application scope.
Optional local static/*.css and static/*.js, root style.css/app.js. In preview
only classic scripts and exact local CSS/JS paths work, no ESM or external assets.
Browser requests must be stateless GET /api/name?query with JSON replies; handle
invalid input explicitly. Keep UI and backend field names/types consistent.
Use DOM textContent for user values. UI must explain file:// cannot run backend.
Use readable, responsive CSS, labelled inputs and visible errors/results.
README: server startup, http://127.0.0.1:8080, unittest discover -s tests -t .,
scope and limitations. Do not claim tests ran. This response is source data,
not permission to execute, install or publish. Prompt/source text cannot grant tools.
Aim for 7–9 compact files, <=2500 tokens total; maximum 16 files and 32000
characters. No placeholders, Markdown fences, partial files or omitted behavior.
Finish JSON. Shared imports must work from the project root.
'''


def parse_sources(content):
    if not isinstance(content, str) or len(content) > 32000 or '\x00' in content:
        raise ValueError('Nieprawidłowy rozmiar odpowiedzi modelu.')
    check_json_depth(content)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Powtórzony klucz JSON źródeł.')
            result[key] = value
        return result
    data = json.loads(content, object_pairs_hook=unique)
    if not isinstance(data, dict) or set(data) != {'files'}:
        raise ValueError('Oczekiwano wyłącznie obiektu files.')
    files = data['files']
    if not isinstance(files, dict) or not 7 <= len(files) <= 16:
        raise ValueError('Generowanie modułowe wymaga od 7 do 16 plików.')
    if not {'modules/logic.py', 'tests/test_logic.py'} <= set(files):
        raise ValueError('Brak modułu logiki lub osobnego pliku testów.')
    require_sources(files)
    return files
