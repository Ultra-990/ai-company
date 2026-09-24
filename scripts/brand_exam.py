"""Holdout exam and scorer for restaurant-brand scene responses."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import brand_school


SCHEMA = 'restaurant-brand-exam.v1'


def make(package, output):
    package = Path(package); output = Path(output)
    report = json.loads((package/'report.json').read_text())
    if report.get('brief', {}).get('split') != 'validation': raise ValueError('Validation brand package required')
    cases=[]
    for id_, kind, request_name, image_name in ((0,'logo','logo-a-request.json','logo-a.png'),
                                                  (1,'logo','logo-b-request.json','logo-b.png'),
                                                  (2,'card','card-request.json','business-card.png')):
        request_path=package/request_name; image=package/'delivery'/image_name
        request=json.loads(request_path.read_text())
        cases.append({'id':id_,'kind':kind,'request':request,'request_path':str(request_path),
                      'image_path':str(image)})
    value={'schema':SCHEMA,'family':report['brief']['family'],'data_split':'validation',
           'package':str(package),'cases':cases,'synthetic':True,
           'limitation':'Holdout scoring is structural and visual-preview based; it is not commercial approval.'}
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2)); return value


def score(raw, case, out):
    raw = raw.strip()
    if raw.startswith('```'):
        lines = raw.splitlines()
        raw = '\n'.join(lines[1:-1]).strip() if len(lines) >= 3 else raw
    request=case['request']; data=json.loads(request['user']); brief=data['brief']; plan=data['plan']
    old=brand_school.BRIEF; brand_school.BRIEF=brief
    try:
        kind=case['kind']; logo=None
        if kind=='card':
            logo=data.get('chosen_logo_svg')
            if not isinstance(logo,str): raise ValueError('Card request missing chosen logo')
        svg=brand_school.compile_scene(raw, plan, kind=kind, logo=logo)
        folder=Path(out); folder.mkdir(parents=True,exist_ok=True); (folder/'artwork.svg').write_text(svg)
        import asyncio
        measured=asyncio.run(brand_school.render(svg,folder,profile='brand_'+kind))
        issues=brand_school.quality_issues(measured,'brand_'+kind)
        if issues: raise ValueError('Measured brand defects: '+json.dumps(issues))
        texts=measured.get('layout',[])
        expected=[brief['restaurant_name']] if kind=='logo' else [brief['restaurant_name'],plan['tagline'],*brief['contacts']]
        actual=[x['text'] for x in texts]
        if sorted(actual)!=sorted(expected): raise ValueError('Expected brand copy missing')
        return {'passed':True,'kind':kind,'texts':actual,'issues':issues,'render':str(folder/'preview.png')}
    finally: brand_school.BRIEF=old


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('package',type=Path); parser.add_argument('output',type=Path); args=parser.parse_args()
    print(json.dumps(make(args.package,args.output),ensure_ascii=False))
