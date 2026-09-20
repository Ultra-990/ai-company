"""Six bounded local-model lessons; exact outputs stay pending independent review."""
import argparse
from datetime import date
import fcntl
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import check_technical_reviewer as lab
from scripts.technical_review_curriculum import CASES
from scripts.prepare_training_data import validate_dataset


def candidate(case, out, report):
    request=json.loads((out/'request.json').read_text())
    response=json.loads((out/'response.json').read_text())
    raw=response['content']
    if (report['status']!='structurally_valid'
            or sha256(raw.encode()).hexdigest()!=report['response_sha256']
            or sha256((out/'request.json').read_bytes()).hexdigest()!=report['request_sha256']):
        raise ValueError('Only intact structurally valid outputs may become pending candidates')
    lab.check_response(raw,case['article'],case['sources'])
    return {'version':'company-sft.v1', 'id':'review-school-'+case['id'],
            'family':case['family'], 'split':'train', 'skill':'evidence',
            'source':{'kind':'synthetic','reference':str(out/'report.json'),
                      'rights':'Teacher-authored synthetic exercise; exact local-model review. No client content.',
                      'privacy_checked':False},
            'messages':request+[{'role':'assistant','content':raw}],
            'review':{'status':'pending','reviewer':'','reviewed_on':None,
                      'evidence':[],'note':'Structure is not technical acceptance; independent content review required.'}}


def load_school_revisions(parent):
    if any(p.is_symlink() for p in (parent,*parent.parents)) or not parent.resolve().is_relative_to(lab.ROOT.resolve()):
        raise ValueError('Private school directory required')
    report=json.loads((parent/'report.json').read_text())
    snapshot=parent/'curriculum-snapshot.json'
    if (report['schema']!='technical-review-school.v1' or report['status']!='awaiting_independent_review'
            or sha256(snapshot.read_bytes()).hexdigest()!=report['curriculum_sha256']
            or json.loads(snapshot.read_text())!=json.loads(json.dumps(CASES))
            or len(report['runs'])!=len(CASES)):
        raise ValueError('Changed or incomplete source school')
    revisions={}
    for case,run in zip(CASES,report['runs']):
        path=Path(run['path'])
        if case['id']!=run['case'] or sha256((path/'report.json').read_bytes()).hexdigest()!=run['report_sha256']:
            raise ValueError('Changed source school run')
        revision=lab.load_revision(path,path/'teacher-feedback.json')
        if revision['article']!=case['article'] or revision['sources']!=case['sources']:
            raise ValueError('Source run is from a different exercise')
        revisions[case['id']]=revision
    return revisions


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--revise-from',type=Path,help='School with independent per-run teacher-feedback.json')
    parser.add_argument('--feedback-only',action='store_true',help='Reconstruct from feedback without copying a rejected draft')
    parser.add_argument('--cases',nargs='+',choices=[c['id'] for c in CASES])
    args=parser.parse_args()
    if args.feedback_only and not args.revise_from:parser.error('--feedback-only requires --revise-from')
    selected=[c for c in CASES if not args.cases or c['id'] in args.cases]
    if not args.run:
        print(json.dumps({'cases':[c['id'] for c in selected], 'model_invoked':False,
                          'automatic_approval':False,'weights_trained':False}));return 0
    revisions=load_school_revisions(args.revise_from) if args.revise_from else {}
    if args.feedback_only:
        for revision in revisions.values():revision['context_mode']='feedback_only'
    lab.ROOT.mkdir(parents=True,exist_ok=True)
    with (lab.ROOT/'school.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        out=Path(tempfile.mkdtemp(prefix='school-',dir=lab.ROOT))
        lab.save(out/'curriculum-snapshot.json',CASES)
        report={'schema':'technical-review-school.v1','status':'running',
                'date':date.today().isoformat(),'runs':[], 'weights_trained':False,
                'accepted':False,'production_ready':False,
                'curriculum_sha256':sha256((out/'curriculum-snapshot.json').read_bytes()).hexdigest(),
                'limitation':'Public synthetic development lessons, not unseen evaluation or autonomous research.'}
        lab.save(out/'report.json',report)
        print(json.dumps({'school':str(out)}),flush=True)
        config=lab.configuration()|{'num_ctx':16384,'num_predict':6000,'num_thread':4,
                                   'timeout_seconds':180,'format':lab.Review.model_json_schema()}
        rows=[]
        try:
            for case in selected:
                path,result=lab.execute(case['article'],True,config,sources=case['sources'],
                                        revision=revisions.get(case['id']))
                report['runs'].append({'case':case['id'],'path':str(path),'status':result['status'],
                                      'report_sha256':sha256((path/'report.json').read_bytes()).hexdigest()})
                lab.save(out/'report.json',report)
                if result['status']=='infrastructure_error':
                    raise RuntimeError('Infrastructure/resource gate failed; remaining cases not run')
                if result['status']=='structurally_valid':rows.append(candidate(case,path,result))
            report['status']='awaiting_independent_review'
        except Exception as exc:
            report['status']='incomplete';report['error_type']=type(exc).__name__
        finally:
            payload=''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows).encode()
            if rows:
                _,gate=validate_dataset(payload)
                (out/'candidates.jsonl').write_bytes(payload)
                report['candidate_sha256']=sha256(payload).hexdigest();report['dataset_gate']=gate
            lab.save(out/'report.json',report)
        print(json.dumps({'report':str(out/'report.json'),'status':report['status'],
                          'pending_candidates':len(rows)}),flush=True)
        return 0 if report['status']=='awaiting_independent_review' else 1


if __name__=='__main__':raise SystemExit(main())
