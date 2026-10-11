"""Frozen synthetic brief and independent checks for the ROWEROWNIA pilot."""
import json
from pathlib import Path

TITLE = "Syntetyczny pilot — ROWEROWNIA"
AUDIENCE = "Właściciel — test systemu, nie zlecenie klienta"
CONSTRAINTS = "Python stdlib, lokalne zasoby. Bez sieci, publikacji i danych klientów."
GOAL = """Zbuduj kompletną polską stronę fikcyjnego serwisu rowerowego ROWEROWNIA.
Projekt ma być czysty i dopracowany: ciepłe tło ivory, granat i pomarańcz,
oryginalna grafika CSS bez zewnętrznych assetów. Zwróć osobne, kompletne pliki
style.css i app.js oraz podłącz je lokalnie z index.html. Strona zawiera sekcje usług,
procesu, wyceny, FAQ i kontaktu tekstowego. Nie dodawaj opinii, prawdziwych
danych kontaktowych, formularza wysyłającego wiadomość ani rezerwacji. Widocznie
oznacz markę, ofertę i wycenę jako fikcyjną demonstrację, a obliczenie jako lokalne.

GET /api/estimate wymaga dokładnie parametrów service=basic|full, bikes jako
cyfry oznaczające liczbę całkowitą 1..8 oraz express=0|1. Brak, pusty parametr,
ułamek, liczba ujemna albo inna wartość zwraca HTTP 400 i obiekt JSON z polem
error. basic kosztuje 90 PLN za rower, full 180 PLN za rower, a express dodaje
50 PLN za każdy rower. total=(cena_bazowa+(50 gdy express=1, inaczej 0))*bikes.
Poprawna odpowiedź to JSON z liczbowym polem total. Zera wiodące w bikes są dozwolone.

Interfejs ma etykietowane kontrolki #service, #bikes i #express, przycisk
#calculate oraz #result z aria-live=polite; wynik ustawiaj przez textContent dokładnie
Wycena: NUMBER PLN. Domyślne wartości to basic, 1 i wyłączony express. Nawigacja
prowadzi do #services, #estimate, #faq i #contact. Dodaj skip link do main#main.
Na telefonie #menu-toggle ma aria-controls=site-nav, steruje domyślnie ukrytym
#site-nav, aktualizuje aria-expanded (początkowo false), a Escape zamyka menu
i przywraca fokus przyciskowi. FAQ używa natywnego details#faq-service. Nie dodawaj przełącznika
motywu. Strona musi działać przy 390 px i 1440 px. Co najmniej pięć sensownych
testów unittest; /health, bezpieczne trasy, lokalne pliki i README zgodnie z
profilem python-web-v1."""

ACCEPTANCE = [
    "Wycena API liczy oba pakiety, liczbę rowerów i dopłatę express oraz odrzuca nieprawidłowe dane.",
    "Polski, responsywny interfejs spełnia kontrakt dostępności i jasno opisuje fikcyjne demo.",
]

PROBES = [
    ["/api/estimate?service=basic&bikes=1&express=0", 200, {"total": 90}],
    ["/api/estimate?service=full&bikes=3&express=0", 200, {"total": 540}],
    ["/api/estimate?service=basic&bikes=8&express=1", 200, {"total": 1120}],
    ["/api/estimate?service=full&bikes=2&express=1", 200, {"total": 460}],
    ["/api/estimate?service=basic&bikes=01&express=0", 200, {"total": 90}],
    ["/api/estimate?service=basic&bikes=0&express=0", 400, None],
    ["/api/estimate?service=basic&bikes=9&express=0", 400, None],
    ["/api/estimate?service=basic&bikes=1.0&express=0", 400, None],
    ["/api/estimate?service=basic&bikes=-1&express=0", 400, None],
    ["/api/estimate?service=basic&bikes=&express=0", 400, None],
    ["/api/estimate?service=other&bikes=1&express=0", 400, None],
    ["/api/estimate?service=basic&bikes=1&express=", 400, None],
    ["/api/estimate?service=basic&bikes=1", 400, None],
    ["/api/estimate?bikes=1&express=0", 400, None],
    ["/api/estimate?service=basic&bikes=1&express=0&extra=1", 400, None],
    ["/not-a-route", 404, None],
]


def harness_source():
    """Create the trusted evaluator; its exact cases are never placed in the prompt."""
    base = (Path(__file__).resolve().parents[1] / "app/runner/harness.py").read_text(encoding="utf-8")
    guard = "if __name__=='__main__':sys.exit(main())"
    assert base.count(guard) == 1
    hook = r'''
_basic_fetch=fetch
_acceptance_probes=REPLACE_PROBES
def fetch(path):
    result=_basic_fetch(path)
    if path=='/':
        import re
        html=result[1]
        lower=html.lower()
        from html.parser import HTMLParser
        class ContractParser(HTMLParser):
            def __init__(self): super().__init__(); self.elements=[]
            def handle_starttag(self,tag,attrs): self.elements.append((tag,dict(attrs)))
        parsed=ContractParser(); parsed.feed(html)
        by_id={a['id']:(tag,a) for tag,a in parsed.elements if 'id' in a}
        required=('main','services','estimate','faq','contact','service','bikes','express',
                  'calculate','result','menu-toggle','site-nav','faq-service')
        missing=[value for value in required if value not in by_id]
        if missing:
            raise ValueError('Independent acceptance: missing HTML contract '+','.join(missing))
        if (by_id['main'][0]!='main' or by_id['faq-service'][0]!='details'
            or by_id['result'][1].get('aria-live')!='polite'
            or by_id['menu-toggle'][1].get('aria-controls')!='site-nav'
            or not any(tag=='link' and a.get('href') in ('style.css','/style.css') for tag,a in parsed.elements)
            or not any(tag=='script' and a.get('src') in ('app.js','/app.js') for tag,a in parsed.elements)):
            raise ValueError('Independent acceptance: semantic elements/local assets/accessibility contract missing')
        if re.search(r'\.\s*innerHTML\s*=',html):
            raise ValueError('Independent acceptance: UI must use textContent/DOM nodes, not innerHTML assignments')
        if 'file:' not in lower or not any(word in lower for word in ('fikcyjn','demonstr')):
            raise ValueError('Independent acceptance: missing file mode or fictional demo explanation')
        css_status,css_body=_basic_fetch('/style.css')
        js_status,js_body=_basic_fetch('/app.js')
        if css_status!=200 or len(css_body)<100 or js_status!=200 or len(js_body)<100:
            raise ValueError('Independent acceptance: separate local CSS and JavaScript must be served')
        for target,expected_status,expected_json in _acceptance_probes:
            status,body=_basic_fetch(target)
            if status!=expected_status:
                raise ValueError('Independent acceptance: '+target+' expected HTTP '+str(expected_status)+' got '+str(status))
            actual=json.loads(body) if expected_json is not None or expected_status==400 else None
            if expected_json is not None and (not isinstance(actual,dict) or any(type(actual.get(k)) not in (int,float) or actual[k]!=v for k,v in expected_json.items())):
                raise ValueError('Independent acceptance: '+target+' expected '+json.dumps(expected_json)+' got '+body[:300])
            if expected_status==400 and (not isinstance(actual,dict) or not isinstance(actual.get('error'),str) or not actual['error']):
                raise ValueError('Independent acceptance: HTTP 400 requires JSON error')
    return result
'''.replace("REPLACE_PROBES", repr(PROBES))
    return base.replace(guard, hook + "\n" + guard)


def public_case():
    return {"title": TITLE, "goal": GOAL, "audience": AUDIENCE,
            "constraints": CONSTRAINTS, "acceptance_criteria": ACCEPTANCE}
