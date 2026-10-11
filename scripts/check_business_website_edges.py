"""Run three bounded supplemental API probes against a reviewed ROWEROWNIA candidate."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.application_preview import PreviewRunner, preview_configuration
from app.services.application_profile import parse_sources
from scripts.compare_local_models import check_idle

PILOT = Path('/home/marcin/ai-company-workspaces/business-website-pilot-fkf_d3w0')
SOURCE = PILOT/'revision-1'/'report.json'
EXPECTED_SOURCE_SHA256 = 'dd4486524418b8cb6406b2029059c1be85aa4237bcd5c743034ffe140e2c3b22'
PROBES = (
    ('valid-control', '/api/estimate?service=basic&bikes=2&express=0', 200, True),
    ('extra-empty-rejected', '/api/estimate?service=basic&bikes=2&express=0&coupon=', 400, True),
    ('duplicate-value-diagnostic', '/api/estimate?service=basic&service=full&bikes=2&express=0', 400, False),
)


def digest(path): return sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)


def _checked(path):
    if any(item.is_symlink() for item in (path,*path.parents)):raise ValueError('Symlink source is not allowed')
    resolved=path.resolve(strict=True)
    if not resolved.is_relative_to(PILOT.resolve(strict=True)):raise ValueError('Source report is outside pilot')
    return resolved


def _revision_one():
    raw=_checked(SOURCE).read_bytes()
    if sha256(raw).hexdigest()!=EXPECTED_SOURCE_SHA256:raise ValueError('Fixed revision-1 report changed')
    report=json.loads(raw)
    revision=report.get('revision',{})
    files=report.get('final_sources',{})
    if (report.get('schema')!='business-website-revision.v1' or report.get('status')!='awaiting_review'
            or revision.get('new_package_id')!=17
            or revision.get('new_package_checksum')!='4652ea35ae3a7391291456611a24072428f7ce252b86cbc54a297c54a4131b0d'
            or revision.get('test_state')!='passed'):
        raise ValueError('Revision 1 is not the fixed tested candidate')
    parse_sources(json.dumps({'files':files},ensure_ascii=False))
    return report,files


def load_source(path=SOURCE):
    original,original_files=_revision_one();path=_checked(path);raw=path.read_bytes();source_sha=sha256(raw).hexdigest()
    if path==_checked(SOURCE):return path,source_sha,original_files
    report=json.loads(raw);revision=report.get('revision',{});files=report.get('final_sources',{})
    if (report.get('schema')!='business-website-edge-repair.v1'
            or report.get('source_report_sha256')!=EXPECTED_SOURCE_SHA256
            or report.get('only_app_changed') is not True
            or report.get('candidate_created') is not True
            or report.get('status')!='awaiting_review'
            or revision.get('test_state')!='passed'
            or not revision.get('new_package_id') or not revision.get('new_package_checksum')):
        raise ValueError('Selected report is not an intact tested edge-repair candidate')
    parse_sources(json.dumps({'files':files},ensure_ascii=False))
    preserved={name:sha256(content.encode()).hexdigest() for name,content in original_files.items() if name!='app.py'}
    if (set(files)!=set(original_files) or files.get('app.py')==original_files['app.py']
            or any(sha256(files[name].encode()).hexdigest()!=value for name,value in preserved.items())
            or report.get('preserved_sha256')!=preserved):
        raise ValueError('Selected repair changed frozen tests or frontend sources')
    return path,source_sha,files


def new_output():
    for number in range(1,1000):
        candidate=PILOT/f'edge-check-{number}'
        try:candidate.mkdir(mode=0o700);return candidate
        except FileExistsError:continue
    raise ValueError('Edge check directory limit reached')


def run(source):
    source,source_sha,files=load_source(source);out=new_output();report_path=out/'report.json'
    report={'schema':'business-website-edge-check.v1','status':'running',
        'source_report':str(source),'source_report_sha256':source_sha,
        'selected_source_schema':json.loads(source.read_text()).get('schema'),
        'source_sha256':{name:sha256(content.encode()).hexdigest() for name,content in files.items()},
        'probes':[],'gate_passed':False,'accepted':False,'deployed':False}
    save(report_path,report)
    profile=preview_configuration()
    for name,path,expected,gate in PROBES:
        check_idle()
        raw=PreviewRunner(path).run(files,profile,'aic-package-'+uuid4().hex)
        try:
            payload=json.loads(raw.get('log',''))
            response=payload['response']
            observed=response['status']
            valid=(raw.get('exit_code')==0 and raw.get('cli_exit_code')==0
                and raw.get('cleanup_confirmed') is True and raw.get('reason') is None
                and payload.get('schema')=='python-web-preview.v1'
                and type(observed) is int and isinstance(response.get('body'),str))
        except (ValueError,KeyError,TypeError,json.JSONDecodeError):
            response={};observed=None;valid=False
        report['probes'].append({'name':name,'path':path,'gate':gate,'expected_status':expected,
            'observed_status':observed,'passed':valid and observed==expected,
            'response':response,'raw_run':raw})
        save(report_path,report)
    report['gate_passed']=all(item['passed'] for item in report['probes'] if item['gate'])
    report['diagnostic_passed']=all(item['passed'] for item in report['probes'] if not item['gate'])
    report['status']='passed' if report['gate_passed'] else 'failed'
    report['source_unchanged']=digest(source)==source_sha
    save(report_path,report)
    print(json.dumps({'report':str(report_path),'status':report['status'],
                      'diagnostic_passed':report['diagnostic_passed']}))
    return 0 if report['gate_passed'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',help='run three isolated CPU preview containers')
    parser.add_argument('--report',type=Path,default=SOURCE,
                        help='fixed revision-1 report or an intact business-website-edge-repair.v1 report')
    args=parser.parse_args();source,source_sha,_=load_source(args.report)
    if not args.run:
        print(json.dumps({'containers_started':False,'source_report':str(source),
            'source_report_sha256':source_sha,
            'probes':[{'name':n,'path':p,'expected_status':e,'gate':g} for n,p,e,g in PROBES],
            'required_flag':'--run'}));return 0
    return run(source)


if __name__=='__main__':raise SystemExit(main())
