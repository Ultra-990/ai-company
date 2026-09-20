"""Re-examine exact prior model sources after fixing the examiner, without inference."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.web_school.run import ROOT, FILES, digest, save, parse_source, validate_sources, failure_lessons
from scripts.web_school.probe import examine, examiner_hash


def recheck(source, examiner=examine):
    if any(p.is_symlink() for p in (source,*source.parents)):
        raise ValueError('Symlink run')
    source=source.resolve()
    if not source.is_relative_to(ROOT):raise ValueError('Private school run required')
    old=json.loads((source/'report.json').read_text())
    if old.get('schema')!='local-web-school.v1' or not 1<=len(old['attempts'])<=3 or old['variant'] not in (0,1):
        raise ValueError('Invalid school run')
    out=Path(tempfile.mkdtemp(prefix='recheck-',dir=ROOT))
    report=copy.deepcopy(old)
    report.update(status='running', attempts=[], experience=[], examiner_sha256=examiner_hash(),
                  recheck_of=str(source), inference_performed=False,
                  origin_report_sha256=digest((source/'report.json').read_text()))
    report.pop('error',None)
    save(out/'report.json',report)
    for number, previous in enumerate(old['attempts'],1):
        folder=out/f'attempt-{number}';folder.mkdir()
        original=source/f'attempt-{number}'
        if original.is_symlink():raise ValueError('Symlink attempt')
        files={}
        for name in FILES:
            for suffix in ('','.request.json','.response.json'):
                path=original/(name+suffix)
                if path.is_symlink():raise ValueError('Symlink artifact')
                (folder/(name+suffix)).write_bytes(path.read_bytes())
            response=json.loads((folder/(name+'.response.json')).read_text())
            files[name]=parse_source(response['content'])
            if files[name]!=(folder/name).read_text():raise ValueError('Edited model source')
        attempt={k:v for k,v in previous.items() if k not in ('evaluation','contract_failure')}
        report['attempts'].append(attempt)
        try:validate_sources(files)
        except ValueError as exc:
            attempt['contract_failure']=[{'name':'source-contract','passed':False,'error':str(exc)}]
            report['status']='needs_more_learning'
        else:
            evaluation=examiner(files,folder,old['variant'])
            save(folder/'evaluation.json',evaluation)
            attempt['evaluation']=evaluation
            report['status']='functional_pass' if evaluation['passed'] else 'needs_more_learning'
        report['experience']=failure_lessons(report['attempts'])
        save(out/'report.json',report)
    return out,report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);a=p.parse_args()
    out,report=recheck(a.run)
    print(json.dumps({'run':str(out),'status':report['status'],'inference_performed':False}))
    return 0 if report['status']=='functional_pass' else 1


if __name__=='__main__':raise SystemExit(main())
