"""Trusted pilot-only acceptance probes. Generated code runs inside Docker only."""
import json
from pathlib import Path

PROBES = [
    ['/api/estimate?hours=8&rate=322&discount=10',200,{'subtotal':2576,'discount_amount':257.6,'total':2318.4}],
    ['/api/estimate?hours=8&rate=322',200,{'subtotal':2576,'discount_amount':0,'total':2576}],
    ['/api/estimate?hours=0&rate=322&discount=100',200,{'subtotal':0,'discount_amount':0,'total':0}],
    ['/api/estimate?hours=1.5&rate=80&discount=25',200,{'subtotal':120,'discount_amount':30,'total':90}],
    ['/api/estimate?hours=8&rate=322&discount=101',400,None],
    ['/api/estimate?hours=-1&rate=322',400,None],
    ['/api/estimate?hours=NaN&rate=322',400,None],
    ['/api/estimate?hours=1&rate=Infinity',400,None],
    ['/api/estimate?hours=1&rate=2&discount=-1',400,None],
    ['/api/estimate?hours=1&rate=2&discount=oops',400,None],
    ['/api/estimate?hours=1',400,None],
    ['/api/estimate?hours=&rate=2',400,None],
    ['/api/estimate?hours=1&rate=2&discount=',400,None],
    ['/not-a-route',404,None],
]


def harness_source():
    base=(Path(__file__).resolve().parents[1]/'app/runner/harness.py').read_text(encoding='utf-8')
    guard="if __name__=='__main__':sys.exit(main())"
    assert base.count(guard)==1
    # Wrap the trusted HTTP probe, never import source modules on the host.
    hook='''
_basic_fetch=fetch
_acceptance_probes=REPLACE_PROBES
def fetch(path):
    result=_basic_fetch(path)
    if path=='/':
        import re
        html=result[1]
        if re.search(r'\\.\\s*innerHTML\\s*=',html):
            raise ValueError('Independent acceptance: UI must use textContent/DOM nodes, not innerHTML assignments')
        if 'file:' not in html:
            raise ValueError('Independent acceptance: missing visible file:// mode explanation in application HTML')
        for target,expected_status,expected_json in _acceptance_probes:
            status,body=_basic_fetch(target)
            if status!=expected_status:
                raise ValueError('Independent acceptance: '+target+' expected HTTP '+str(expected_status)+' got '+str(status))
            if expected_json is not None:
                actual=json.loads(body)
                if not isinstance(actual,dict) or any(type(actual.get(k)) not in (int,float) or actual[k]!=v for k,v in expected_json.items()):
                    raise ValueError('Independent acceptance: '+target+' expected '+json.dumps(expected_json)+' got '+body[:300])
    return result
'''.replace('REPLACE_PROBES',repr(PROBES))
    return base.replace(guard,hook+'\n'+guard)
