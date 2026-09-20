"""Collect exact successful model responses as pending SFT records, never approve/train."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.web_school.run import FILES, load_experience, parse_source
from scripts.prepare_training_data import validate_record, DatasetError


def collect(root):
    load_experience(root)  # Includes unchanged sources, examiner and functional result.
    report = json.loads((root/'report.json').read_text())
    folder = root/f"attempt-{len(report['attempts'])}"
    rows = []; skipped = []
    for name in FILES:
        messages = json.loads((folder/(name+'.request.json')).read_text())
        response = json.loads((folder/(name+'.response.json')).read_text())
        source = (folder/name).read_text()
        if parse_source(response['content']) != source:
            raise ValueError('Source was edited outside the model response')
        if response.get('model')!=report['model'] or response.get('digest')!=report['digest']:
            raise ValueError('Model provenance mismatch')
        row = {'version':'company-sft.v1', 'id':root.name+'-'+name.replace('.','-'),
               'family':'web-school.stamp-shop', 'split':'train',
               'skill':'repair' if len(report['attempts'])>1 else 'coding',
               'source':{'kind':'synthetic','reference':str(root/'report.json'),
                         'rights':'Original synthetic teaching brief and local model output; no customer media.',
                         'privacy_checked':False},
               'messages':messages+[{'role':'assistant','content':response['content']}],
               'review':{'status':'pending','reviewer':'','reviewed_on':None,
                         'evidence':[{'kind':'independent_test','reference':str(folder/'evaluation.json'),
                                      'sha256':sha256((folder/'evaluation.json').read_bytes()).hexdigest()}],
                         'note':'Functional checks only. Requires source, privacy, visual and token-length review. Same-family practice is train, never holdout.'}}
        try: validate_record(row)
        except DatasetError as exc:
            skipped.append({'file':name,'reason':str(exc),'truncated':False}); continue
        rows.append(row)
    # Refuse replacement even if an earlier collection was pending or incomplete.
    with (root/'training-candidates.jsonl').open('x',encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    result={'records':len(rows),'skipped':skipped,'review':'pending','weights_trained':False,
            'auto_approved':False,'family':'web-school.stamp-shop','split':'train'}
    with (root/'training-candidates-summary.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);a=p.parse_args()
    print(json.dumps(collect(a.run),ensure_ascii=False))


if __name__=='__main__':main()
