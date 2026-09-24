"""Reproducible independent scoring for a completed brand text pilot."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import brand_exam


def score(run, exam_path):
    run=Path(run); exam=json.loads(Path(exam_path).read_text()); report=json.loads((run/'report.json').read_text())
    if report.get('status') != 'completed_research': raise ValueError('Completed research report required')
    phases={}
    for key in ('brand_baseline','brand_after'):
        values=[]; details=[]
        for case,item in zip(exam['cases'],report.get(key,[])):
            try:
                result=brand_exam.score(item['content'],case,run/(key+'-'+str(case['id'])))
                values.append(bool(result.get('passed'))); details.append(result)
            except Exception as exc:
                values.append(False); details.append({'passed':False,'error':str(exc)[:400]})
        phases[key]={'passed':sum(values),'total':len(values),'details':details}
    result={'schema':'brand-text-comparison.v1','training_report_sha256':sha256((run/'report.json').read_bytes()).hexdigest(),
            'exam_sha256':sha256(Path(exam_path).read_bytes()).hexdigest(),'base':phases['brand_baseline'],
            'adapter':phases['brand_after'],'automatic_promotion':False,'production_ready':False,
            'limitation':'One synthetic holdout family; assistant baseline and commercial readiness remain unproven.'}
    (run/'brand-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)); return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('exam',type=Path);args=parser.parse_args()
    print(json.dumps(score(args.run,args.exam),ensure_ascii=False,indent=2))
