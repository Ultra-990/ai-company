"""Small public brief and private acceptance probes for the filewise API canary."""
import json
from pathlib import Path
from hashlib import sha256

TITLE='Syntetyczny canary — LICZNIK LITER'
CASE_VERSION='compact-v2'
SOFT_FILE_BUDGETS={'app.py':2400,'test_app.py':1400,'index.html':700,
    'style.css':400,'app.js':700,'README.md':300}
BASE_HARNESS_SHA256='30772e4c4faed5f4f3c1f281bec33af68c30d8915e9cd10f1f61703f83cc1f50'
GOAL='''Zbuduj małą polską aplikację demonstracyjną LICZNIK LITER. To jawna rewizja
compact-v2 po zbyt obszernym CSS w poprzedniej próbie kalibracyjnej. Priorytetem jest
samodzielne napisanie przez model sześciu kompletnych, zwięzłych plików w miękkich
budżetach znaków: app.py <=2400, test_app.py <=1400, index.html <=700,
style.css <=400, app.js <=700, README.md <=300; razem około 5900. Orkiestrator
nie będzie obcinać, przepisywać ani automatycznie minifikować źródeł.
Użyj Python 3.10 stdlib oraz osobnych
lokalnych index.html, style.css i app.js; bez zewnętrznych zasobów i zapisu danych.
Tekst jest wysyłany tylko do lokalnego backendu tej aplikacji, nigdy do zewnętrznego serwisu.
GET /api/count wymaga dokładnie jednego parametru text o długości 1..100 znaków.
Zwraca JSON {"letters":N}, gdzie N to liczba znaków, dla których Python str.isalpha()
jest prawdziwe. Brak, pusty tekst, duplikat parametru, dodatkowy parametr lub tekst
dłuższy niż 100 znaków zwraca HTTP 400 z niepustym polem error. Pozostałe trasy 404,
a /health zwraca {"status":"ok"}. Interfejs zawiera label i input#text, button#calculate
oraz #result z aria-live="polite"; wysyła encodeURIComponent(text), a wynik ustawia
przez textContent. Widocznie wyjaśnij, że to fikcyjne lokalne demo bez wysyłania do
usług zewnętrznych ani zapisywania danych oraz że file:// nie obsługuje API. Dodaj co najmniej pięć realnych
testów unittest. README podaje uruchomienie, testy, URL i ograniczenia. Nie twierdź,
że testy wykonano.'''
PROBES=[
    ('/api/count?text=Hello',200,{'letters':5}),
    ('/api/count?text=A1-b',200,{'letters':2}),
    ('/api/count?text=',400,None),
    ('/api/count?text=a&text=b',400,None),
    ('/api/count?text=a&extra=1',400,None),
    ('/not-a-route',404,None),
]


def public_case():
    return {'case_version':CASE_VERSION,'title':TITLE,'goal':GOAL,
        'audience':'Wewnętrzny syntetyczny canary systemu.',
        'constraints':'Brak danych klientów, sieci, publikacji i automatycznego odbioru.',
        'acceptance_criteria':['Ścisłe API liczy litery i odrzuca błędne zapytania.',
            'Mały lokalny interfejs i rzeczywiste testy mieszczą się w budżecie.']}


def harness_source():
    path=Path(__file__).resolve().parents[1]/'app/runner/harness.py'
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=BASE_HARNESS_SHA256:raise ValueError('base_harness_changed')
    base=raw.decode('utf-8')
    guard="if __name__=='__main__':sys.exit(main())"
    assert base.count(guard)==1
    hook=r'''
_base_fetch=fetch
_canary_probes=REPLACE_PROBES
def fetch(path):
    result=_base_fetch(path)
    if path=='/':
        from html.parser import HTMLParser
        class P(HTMLParser):
            def __init__(self):super().__init__();self.items=[]
            def handle_starttag(self,tag,attrs):self.items.append((tag,dict(attrs)))
        parsed=P();parsed.feed(result[1]);ids={a.get('id'):(t,a) for t,a in parsed.items if a.get('id')}
        for required in ('text','calculate','result'):
            if required not in ids:raise ValueError('Canary acceptance: missing #'+required)
        if ids['result'][1].get('aria-live')!='polite':raise ValueError('Canary acceptance: aria-live')
        if not any(t=='link' and a.get('href') in ('style.css','/style.css') for t,a in parsed.items):
            raise ValueError('Canary acceptance: local CSS')
        if not any(t=='script' and a.get('src') in ('app.js','/app.js') for t,a in parsed.items):
            raise ValueError('Canary acceptance: local JS')
        for target,status,expected in _canary_probes:
            actual_status,body=_base_fetch(target)
            if actual_status!=status:raise ValueError('Canary acceptance: HTTP '+target)
            if expected is not None and json.loads(body)!=expected:raise ValueError('Canary acceptance: JSON '+target)
            if status==400 and not json.loads(body).get('error'):raise ValueError('Canary acceptance: error '+target)
    return result
'''.replace('REPLACE_PROBES',repr(PROBES))
    return base.replace(guard,hook+'\n'+guard)
