"""Frozen synthetic transfer case for a six-file service quote website.

The public brief is safe to show to a builder. Exact examiner requests remain
only in the trusted harness. This is a transfer probe, not a blind holdout once
the public brief has been shown, and it is not an accepted training example.
"""
from hashlib import sha256
import json
from pathlib import Path


TITLE = "Syntetyczny transfer — SERWIS CREMA"
AUDIENCE = "Właściciel systemu — fikcyjny test transferu, bez danych klienta"
CONSTRAINTS = "Python 3.10 stdlib, lokalne zasoby, bez sieci, publikacji i zależności."
FILES = ("app.py", "test_app.py", "index.html", "style.css", "app.js", "README.md")
BASE_HARNESS_SHA256 = "30772e4c4faed5f4f3c1f281bec33af68c30d8915e9cd10f1f61703f83cc1f50"

GOAL = """Zbuduj kompletną polską stronę fikcyjnego serwisu ekspresów SERWIS CREMA.
Przygotuj dokładnie sześć osobnych plików: app.py, test_app.py, index.html,
style.css, app.js i README.md. Użyj wyłącznie Python stdlib oraz lokalnych CSS/JS.
Strona ma mieć dopracowaną, oryginalną oprawę inspirowaną warsztatem kawowym,
bez zewnętrznych assetów. Zawrzyj sekcje usług, procesu, kalkulatora, FAQ i
kontaktu tekstowego. Nie dodawaj opinii, rezerwacji, prawdziwych danych firmy ani
formularza wysyłającego. Widocznie oznacz markę, ceny i realizację jako fikcyjne demo.

GET /api/quote przyjmuje dokładnie po jednym parametrze plan=check|restore,
machines będącym zapisem cyfr liczby całkowitej 1..6 oraz onsite=0|1. Parametry
brakujące, puste, powtórzone, dodatkowe lub o innej wartości zwracają HTTP 400
i JSON z niepustym tekstowym polem error. Zera wiodące machines są dozwolone.
check kosztuje 85 PLN za ekspres, restore 235 PLN za ekspres. onsite=1 dodaje
jedną stałą opłatę 70 PLN do całego zlecenia, niezależnie od liczby ekspresów.
total=cena_planu*machines+(70 gdy onsite=1, inaczej 0). Sukces zwraca HTTP 200
i dokładnie JSON z liczbowym total oraz currency równym PLN. Inne trasy to 404.

Interfejs ma etykiety label z atrybutem for dla #plan, #machines i #onsite,
przycisk #calculate oraz #result z aria-live=polite. Wynik ustaw przez textContent dokładnie jako
Szacunkowo: NUMBER PLN. Domyślne wartości to check, 1 i wyłączony onsite.
Nawigacja prowadzi do #services, #quote, #faq i #contact. Dodaj skip link do
main#main. Na telefonie #menu-toggle ma aria-controls=site-nav, początkowe
aria-expanded=false, otwiera/zamyka #site-nav, a Escape zamyka menu i oddaje
fokus przyciskowi. FAQ używa natywnego details#faq-process.

To aplikacja serwerowa. #runtime-note z aria-live=polite ma jawnie wyjaśnić, że kalkulator wymaga
uruchomienia python app.py. Przy location.protocol === 'file:' JavaScript ma
pokazać tę informację i wyłączyć #calculate bez próby fetch. README ma krótko
opisać zakres, sześć plików, uruchomienie, testy, tryb file:// i ograniczenia;
nie może twierdzić, że testy wykonano. Strona działa przy 390 px i 1440 px.
test_app.py zawiera co najmniej pięć sensownych testów unittest obejmujących
logikę wyceny, parser parametrów, body/status HTTP, /health i bezpieczne trasy."""

ACCEPTANCE = [
    "Ścisły parser i API poprawnie rozróżniają plan, liczbę ekspresów oraz jednorazowy dojazd.",
    "Sześcioplikowy interfejs jest responsywny, dostępny i bezpiecznie objaśnia tryb file://.",
    "Menu, kalkulator, FAQ, lokalne zasoby i zwięzły README spełniają jawny kontrakt.",
]

# Independently authored before generation. Do not place these exact requests in the brief.
PROBES = (
    ("/api/quote?plan=check&machines=1&onsite=0", 200, {"total": 85, "currency": "PLN"}),
    ("/api/quote?onsite=0&machines=2&plan=restore", 200, {"total": 470, "currency": "PLN"}),
    ("/api/quote?machines=6&plan=check&onsite=1", 200, {"total": 580, "currency": "PLN"}),
    ("/api/quote?plan=restore&onsite=1&machines=3", 200, {"total": 775, "currency": "PLN"}),
    ("/api/quote?plan=check&machines=01&onsite=0", 200, {"total": 85, "currency": "PLN"}),
    ("/api/quote?plan=check&machines=0&onsite=0", 400, None),
    ("/api/quote?plan=restore&machines=7&onsite=0", 400, None),
    ("/api/quote?plan=check&machines=1.0&onsite=0", 400, None),
    ("/api/quote?plan=check&machines=-2&onsite=0", 400, None),
    ("/api/quote?plan=check&machines=&onsite=0", 400, None),
    ("/api/quote?plan=clean&machines=1&onsite=0", 400, None),
    ("/api/quote?plan=check&machines=1&onsite=", 400, None),
    ("/api/quote?plan=check&machines=1", 400, None),
    ("/api/quote?machines=1&onsite=0", 400, None),
    ("/api/quote?plan=check&machines=1&onsite=0&coupon=1", 400, None),
    ("/api/quote?plan=check&plan=restore&machines=1&onsite=0", 400, None),
    ("/api/quote?plan=check&machines=1&machines=2&onsite=0", 400, None),
    ("/api/quote?plan=check&machines=1&onsite=0&onsite=1", 400, None),
    ("/missing-page", 404, None),
)

PROBES_SHA256 = "35c85624fe28046663667e8e5a9b3f670ead0f8ea71fc5078086bbf5231e3a78"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def harness_source():
    """Build a pinned trusted harness without importing the candidate package."""
    path = Path(__file__).resolve().parents[1] / "app/runner/harness.py"
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != BASE_HARNESS_SHA256:
        raise ValueError("Base harness changed; version this transfer case explicitly")
    if sha256(_canonical(PROBES).encode()).hexdigest() != PROBES_SHA256:
        raise ValueError("Transfer probes changed; create a new case version")
    base = raw.decode("utf-8")
    guard = "if __name__=='__main__':sys.exit(main())"
    if base.count(guard) != 1:
        raise ValueError("Base harness entrypoint changed")
    hook = r'''
_base_fetch=fetch
_transfer_probes=REPLACE_PROBES
_required_files=set(REPLACE_FILES)
def fetch(path):
    result=_base_fetch(path)
    if path=='/':
        import re
        from html.parser import HTMLParser
        root_files={p.name for p in WORKSPACE.iterdir() if p.is_file()}
        if 'runner_harness.py' not in root_files or root_files-{'runner_harness.py'}!=_required_files:
            raise ValueError('Transfer acceptance: expected exactly six root files')
        status,html=result
        if status!=200:
            raise ValueError('Transfer acceptance: root must return HTTP 200')
        lower=html.lower()
        class ContractParser(HTMLParser):
            def __init__(self): super().__init__();self.elements=[]
            def handle_starttag(self,tag,attrs): self.elements.append((tag,dict(attrs)))
        parsed=ContractParser();parsed.feed(html)
        by_id={attrs['id']:(tag,attrs) for tag,attrs in parsed.elements if 'id' in attrs}
        required=('main','services','quote','faq','contact','plan','machines','onsite',
                  'calculate','result','runtime-note','menu-toggle','site-nav','faq-process')
        missing=[item for item in required if item not in by_id]
        if missing:
            raise ValueError('Transfer acceptance: missing HTML contract '+','.join(missing))
        labels={attrs.get('for') for tag,attrs in parsed.elements if tag=='label'}
        links={attrs.get('href') for tag,attrs in parsed.elements if tag=='a'}
        if (by_id['main'][0]!='main' or by_id['faq-process'][0]!='details'
            or by_id['result'][1].get('aria-live')!='polite'
            or by_id['runtime-note'][1].get('aria-live')!='polite'
            or by_id['menu-toggle'][1].get('aria-controls')!='site-nav'
            or by_id['menu-toggle'][1].get('aria-expanded')!='false'
            or not {'plan','machines','onsite'}<=labels
            or not {'#services','#quote','#faq','#contact'}<=links):
            raise ValueError('Transfer acceptance: accessibility/navigation contract missing')
        if (not any(tag=='link' and attrs.get('href') in ('style.css','/style.css') for tag,attrs in parsed.elements)
            or not any(tag=='script' and attrs.get('src') in ('app.js','/app.js') for tag,attrs in parsed.elements)):
            raise ValueError('Transfer acceptance: local CSS/JS links missing')
        css_status,css_body=_base_fetch('/style.css')
        js_status,js_body=_base_fetch('/app.js')
        if css_status!=200 or len(css_body)<160 or js_status!=200 or len(js_body)<220:
            raise ValueError('Transfer acceptance: separate local assets missing')
        if (re.search(r'\.\s*innerHTML\s*=',js_body) or 'textContent' not in js_body
            or 'location.protocol' not in js_body or 'file:' not in js_body
            or 'disabled' not in js_body):
            raise ValueError('Transfer acceptance: calculator/file-mode implementation missing')
        if (not any(word in lower for word in ('fikcyjn','demonstr'))
            or 'python app.py' not in lower):
            raise ValueError('Transfer acceptance: fictional/server-mode explanation missing')
        readme=(WORKSPACE/'README.md').read_text(encoding='utf-8')
        readme_lower=readme.lower()
        if ('python app.py' not in readme_lower
            or 'unittest' not in readme_lower or 'file://' not in readme_lower
            or 'ograniczen' not in readme_lower or any(phrase in readme_lower for phrase in
                ('testy przeszły','tests passed','wszystkie testy zaliczone'))):
            raise ValueError('Transfer acceptance: concise README scope/run/test/file-mode contract missing')
        for target,expected_status,expected_json in _transfer_probes:
            actual_status,body=_base_fetch(target)
            if actual_status!=expected_status:
                raise ValueError('Transfer acceptance: unexpected status for frozen request')
            if expected_status==200:
                try: actual=json.loads(body)
                except (ValueError,TypeError):
                    raise ValueError('Transfer acceptance: success body must be JSON')
                if (not isinstance(actual,dict) or set(actual)!=set(expected_json)
                    or type(actual.get('total')) not in (int,float)
                    or actual!=expected_json):
                    raise ValueError('Transfer acceptance: incorrect success body')
            elif expected_status==400:
                try: actual=json.loads(body)
                except (ValueError,TypeError):
                    raise ValueError('Transfer acceptance: error body must be JSON')
                if (not isinstance(actual,dict) or not isinstance(actual.get('error'),str)
                    or not actual['error'].strip()):
                    raise ValueError('Transfer acceptance: HTTP 400 requires nonempty error field')
    return result
'''.replace("REPLACE_PROBES", repr(PROBES)).replace("REPLACE_FILES", repr(FILES))
    return base.replace(guard, hook + "\n" + guard)


def public_case():
    return {"title": TITLE, "goal": GOAL, "audience": AUDIENCE,
            "constraints": CONSTRAINTS, "acceptance_criteria": list(ACCEPTANCE),
            "status_note": ("Transferowy test syntetyczny. Przypadki testowe zamrożono przed generacją; "
                            "po pokazaniu briefu wykonawcy nie jest to ślepy holdout. Brak zaakceptowanego przykładu treningowego.")}
