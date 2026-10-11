"""Frozen synthetic development-transfer case for a workshop catalogue."""
from hashlib import sha256
import json
from pathlib import Path


TITLE = "Syntetyczny transfer rozwojowy — PLAN ZAJĘĆ"
AUDIENCE = "Właściciel systemu — fikcyjny test transferu, bez danych klienta"
CONSTRAINTS = "Python 3.10 stdlib, lokalne zasoby, bez sieci, publikacji i zależności."
FILES = ("app.py", "test_app.py", "index.html", "style.css", "app.js", "README.md")
BASE_HARNESS_SHA256 = "30772e4c4faed5f4f3c1f281bec33af68c30d8915e9cd10f1f61703f83cc1f50"

SESSIONS = (
    {"id": "paper-garden", "title": "Papierowy ogród", "day": "monday", "start": "17:00", "level": "beginner", "duration_minutes": 75},
    {"id": "clay-stories", "title": "Historie z gliny", "day": "monday", "start": "19:00", "level": "intermediate", "duration_minutes": 90},
    {"id": "cyanotype", "title": "Błękitna cyjanotypia", "day": "tuesday", "start": "17:30", "level": "beginner", "duration_minutes": 80},
    {"id": "bookbinding", "title": "Notes szyty ręcznie", "day": "tuesday", "start": "19:15", "level": "advanced", "duration_minutes": 105},
    {"id": "plant-print", "title": "Roślinny druk", "day": "saturday", "start": "10:00", "level": "intermediate", "duration_minutes": 120},
    {"id": "woodcut", "title": "Mały drzeworyt", "day": "saturday", "start": "13:30", "level": "advanced", "duration_minutes": 135},
)

GOAL = """Zbuduj kompletną polską stronę fikcyjnego katalogu warsztatów PLAN ZAJĘĆ.
Zwróć dokładnie sześć osobnych plików: app.py, test_app.py, index.html, style.css,
app.js i README.md. Użyj wyłącznie Python stdlib i lokalnych CSS/JS. Oprawa ma
być estetyczna, oryginalna i responsywna przy 390 px oraz 1440 px. Nie dodawaj
cen, zapisów, formularza danych osobowych, zewnętrznych assetów ani nowych API.
Widocznie oznacz katalog jako fikcyjną demonstrację.

Katalog ma dokładnie te rekordy i tę kolejność:
1. paper-garden | Papierowy ogród | monday | 17:00 | beginner | 75
2. clay-stories | Historie z gliny | monday | 19:00 | intermediate | 90
3. cyanotype | Błękitna cyjanotypia | tuesday | 17:30 | beginner | 80
4. bookbinding | Notes szyty ręcznie | tuesday | 19:15 | advanced | 105
5. plant-print | Roślinny druk | saturday | 10:00 | intermediate | 120
6. woodcut | Mały drzeworyt | saturday | 13:30 | advanced | 135
Pola rekordu to dokładnie id, title, day, start, level i duration_minutes.

GET /api/sessions wymaga dokładnie po jednym parametrze day oraz level. day ma
wartość all|monday|tuesday|saturday, a level all|beginner|intermediate|advanced.
Parametry brakujące, puste, powtórzone, dodatkowe lub o innej wartości zwracają
HTTP 400 oraz JSON z niepustym tekstowym polem error. Sukces zwraca HTTP 200 i
dokładnie obiekt {\"sessions\": [...]} z pasującymi rekordami w kolejności
katalogu. all nie ogranicza danego wymiaru, a dwa filtry łączą się przez AND.
Brak dopasowań jest sukcesem z pustą listą. Techniczne GET /health zwraca JSON
ze status równym ok, GET / oraz lokalne /style.css i /app.js są obsługiwane,
a wszystkie inne trasy zwracają 404. GET /api/sessions bez query zwraca 400.

Interfejs ma main#main i sekcje #catalog, #schedule, #faq, #contact. index.html
podłącza lokalne style.css przez link oraz app.js przez script src. Nawigacja
prowadzi do tych czterech kotwic i zawiera skip link. Kontrolka select#day ma
wartości all, monday, tuesday, saturday, a select#level ma wartości all,
beginner, intermediate, advanced; obie mają jawne label z for. Przycisk
#apply-filters, lista #sessions oraz #filter-status i
#runtime-note mają jawny kontrakt; dwa ostatnie używają aria-live=polite.
Pusty wynik pokazuje czytelny komunikat w #sessions. Kod JavaScript nie może
przypisywać do innerHTML; używa bezpiecznych metod DOM. #menu-toggle ma
aria-controls=site-nav i początkowe
aria-expanded=false; Escape zamyka #site-nav i oddaje fokus przyciskowi. FAQ
używa natywnego details#faq-filtering. Przy location.protocol === 'file:'
widoczne ostrzeżenie wyjaśnia konieczność uruchomienia python app.py i wyłącza
#apply-filters bez fetch. Te zachowania interaktywne sprawdza rzeczywista
przeglądarka, niezależnie od wybranej poprawnej implementacji JavaScript.

test_app.py używa unittest i zawiera co najmniej pięć sensownych testów dla
katalogu, obu filtrów, pustej listy, statusu/body API, /health i bezpiecznych
tras. Własny helper request(path) zwraca osobno trójkę (status, headers, body),
aby testy nie myliły pełnej odpowiedzi HTTP z body. README opisuje zakres,
sześć plików, uruchomienie, unittest, file:// i ograniczenia oraz nie twierdzi,
że testy już wykonano."""

ACCEPTANCE = (
    "API zwraca jawny sześciorekordowy katalog i poprawnie łączy dwa filtry.",
    "Routing, statusy, JSON oraz własne testy rozdzielają odpowiedź HTTP od body.",
    "Responsywny interfejs, menu, FAQ, empty state i tryb file:// spełniają jawny kontrakt.",
)

# Frozen before generation. Exact requests are deliberately absent from the public brief.
PROBES = (
    ("/api/sessions?day=all&level=all", 200, list(SESSIONS)),
    ("/api/sessions?level=beginner&day=monday", 200, [SESSIONS[0]]),
    ("/api/sessions?day=tuesday&level=all", 200, [SESSIONS[2], SESSIONS[3]]),
    ("/api/sessions?day=saturday&level=intermediate", 200, [SESSIONS[4]]),
    ("/api/sessions?day=monday&level=advanced", 200, []),
    ("/api/sessions?day=&level=all", 400, None),
    ("/api/sessions?day=all&level=", 400, None),
    ("/api/sessions?day=friday&level=all", 400, None),
    ("/api/sessions?day=all", 400, None),
    ("/api/sessions?level=all", 400, None),
    ("/api/sessions?day=all&level=expert", 400, None),
    ("/api/sessions", 400, None),
    ("/api/sessions?day=all&level=all&extra=1", 400, None),
    ("/api/sessions?day=all&level=all&extra=", 400, None),
    ("/api/sessions?day=all&day=monday&level=all", 400, None),
    ("/api/sessions?day=all&level=all&level=beginner", 400, None),
    ("/missing", 404, None),
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


PROBES_SHA256 = "66a0517cfaf5d455fdd7b8361a922bce2a0b3846f7010f4bedee5be76dabb666"


def harness_source():
    """Build the pinned examiner without importing or running candidate code."""
    path = Path(__file__).resolve().parents[1] / "app/runner/harness.py"
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != BASE_HARNESS_SHA256:
        raise ValueError("Base harness changed; version this case explicitly")
    if sha256(_canonical(PROBES).encode()).hexdigest() != PROBES_SHA256:
        raise ValueError("Workshop probes changed; create a new case version")
    base = raw.decode("utf-8")
    guard = "if __name__=='__main__':sys.exit(main())"
    if base.count(guard) != 1:
        raise ValueError("Base harness entrypoint changed")
    hook = r'''
_base_fetch=fetch
_workshop_probes=REPLACE_PROBES
_required_files=set(REPLACE_FILES)
def fetch(path):
    result=_base_fetch(path)
    if path=='/':
        import re
        from html.parser import HTMLParser
        root_files={p.name for p in WORKSPACE.iterdir() if p.is_file()}
        if 'runner_harness.py' not in root_files or root_files-{'runner_harness.py'}!=_required_files:
            raise ValueError('Workshop acceptance: expected exactly six root files')
        status,html=result
        if status!=200: raise ValueError('Workshop acceptance: root must return HTTP 200')
        class ContractParser(HTMLParser):
            def __init__(self): super().__init__();self.elements=[]
            def handle_starttag(self,tag,attrs): self.elements.append((tag,dict(attrs)))
        parsed=ContractParser();parsed.feed(html)
        by_id={attrs['id']:(tag,attrs) for tag,attrs in parsed.elements if 'id' in attrs}
        required=('main','catalog','schedule','faq','contact','day','level','apply-filters',
                  'sessions','filter-status','runtime-note','menu-toggle','site-nav','faq-filtering')
        missing=[item for item in required if item not in by_id]
        labels={attrs.get('for') for tag,attrs in parsed.elements if tag=='label'}
        links={attrs.get('href') for tag,attrs in parsed.elements if tag=='a'}
        if (missing or by_id.get('main',(None,))[0]!='main' or by_id.get('faq-filtering',(None,))[0]!='details'
            or by_id.get('filter-status',(None,{}))[1].get('aria-live')!='polite'
            or by_id.get('runtime-note',(None,{}))[1].get('aria-live')!='polite'
            or by_id.get('menu-toggle',(None,{}))[1].get('aria-controls')!='site-nav'
            or by_id.get('menu-toggle',(None,{}))[1].get('aria-expanded')!='false'
            or not {'day','level'}<=labels
            or not {'#catalog','#schedule','#faq','#contact'}<=links):
            raise ValueError('Workshop acceptance: HTML/accessibility/navigation contract missing')
        if (not any(tag=='link' and a.get('href') in ('style.css','/style.css') for tag,a in parsed.elements)
            or not any(tag=='script' and a.get('src') in ('app.js','/app.js') for tag,a in parsed.elements)):
            raise ValueError('Workshop acceptance: local CSS/JS links missing')
        css_status,css_body=_base_fetch('/style.css');js_status,js_body=_base_fetch('/app.js')
        if css_status!=200 or js_status!=200:
            raise ValueError('Workshop acceptance: local assets not served')
        if re.search(r'\.\s*innerHTML\s*=',js_body):
            raise ValueError('Workshop acceptance: JavaScript must not assign innerHTML')
        readme=(WORKSPACE/'README.md').read_text(encoding='utf-8').lower()
        if ('python app.py' not in readme or 'unittest' not in readme or 'file://' not in readme
            or any(x in readme for x in ('testy przeszły','tests passed'))):
            raise ValueError('Workshop acceptance: README contract missing')
        for target,expected_status,expected_sessions in _workshop_probes:
            actual_status,body=_base_fetch(target)
            if actual_status!=expected_status:
                raise ValueError('Workshop acceptance: unexpected status for frozen request')
            if expected_status==200:
                try: actual=json.loads(body)
                except (ValueError,TypeError): raise ValueError('Workshop acceptance: success body must be JSON')
                if not isinstance(actual,dict) or set(actual)!={'sessions'} or actual['sessions']!=expected_sessions:
                    raise ValueError('Workshop acceptance: incorrect sessions body')
            elif expected_status==400:
                try: actual=json.loads(body)
                except (ValueError,TypeError): raise ValueError('Workshop acceptance: error body must be JSON')
                if not isinstance(actual,dict) or not isinstance(actual.get('error'),str) or not actual['error'].strip():
                    raise ValueError('Workshop acceptance: HTTP 400 requires nonempty error')
    return result
'''.replace("REPLACE_PROBES", repr(PROBES)).replace("REPLACE_FILES", repr(FILES))
    return base.replace(guard, hook + "\n" + guard)


def public_case():
    return {
        "title": TITLE, "goal": GOAL, "audience": AUDIENCE, "constraints": CONSTRAINTS,
        "acceptance_criteria": list(ACCEPTANCE),
        "status_note": ("Jawny test transferu rozwojowego; nie jest ślepym holdoutem ani zaakceptowanym "
                        "przykładem treningowym. Nowe uwagi należy zachować jako osobny feedback."),
    }
