"""Bounded local-model school: full sources -> independent feedback -> model repair.

The teacher writes this orchestration, never the submitted website. Experience
memory contains examiner facts, not model self-approval. No weight training here.
"""
import argparse
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.services.local_ollama import configuration, generation_options, OllamaProvider
from scripts.compare_local_models import check_idle
from scripts.web_school.contract import FILES, SYSTEM, LESSONS, brief
from scripts.web_school.probe import examine, examiner_hash

ROOT = Path('/home/marcin/ai-company-workspaces/web-school')
SCHEMA = {'type':'object', 'properties':{'content':{'type':'string'}},
          'required':['content'], 'additionalProperties':False}


def digest(value):
    return sha256(value.encode()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def parse_source(raw):
    def unique(items):
        result = {}
        for k,v in items:
            if k in result: raise ValueError('Duplicate JSON key')
            result[k] = v
        return result
    data = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(data,dict) or set(data)!={'content'} or not isinstance(data['content'],str):
        raise ValueError('Expected exactly one content string')
    value = data['content']
    if not 30 <= len(value) <= 26000 or '\x00' in value or '```' in value:
        raise ValueError('Invalid source size, NUL or markdown wrapper')
    return value


class HTMLBoundary(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id') in self.ids:
            raise ValueError('Duplicate HTML id: '+a['id'])
        if a.get('id'):
            self.ids.add(a['id'])
        if tag in {'iframe','object','embed','base'} or any(k.lower().startswith('on') for k in a):
            raise ValueError('Embedded document or inline handler forbidden')
        if tag=='script' and (a.get('src')!='app.js' or 'defer' not in a):
            raise ValueError('Only deferred local app.js allowed')
        if tag=='meta' and a.get('http-equiv','').lower()=='refresh':
            raise ValueError('Automatic navigation forbidden')
        for key in ('src','href','action','formaction','poster','srcset'):
            value = a.get(key)
            if value and not (value in FILES or value.startswith('#')):
                raise ValueError('Only local files and section anchors allowed')


def validate_sources(files):
    if set(files)!=set(FILES) or sum(len(v.encode()) for v in files.values())>70000:
        raise ValueError('Exactly three bounded source files required')
    HTMLBoundary().feed(files['index.html'])
    if '<html' not in files['index.html'].lower() or '<h1' not in files['index.html'].lower():
        raise ValueError('Complete HTML document with heading required')
    for name in ('style.css','app.js'):
        if files[name].lstrip().lower().startswith(('<!doctype','<html','<style','<script')):
            raise ValueError(name+' contains an HTML document/wrapper instead of its source type')


def failure_lessons(attempts):
    """Automatic factual feedback only, never arbitrary model-authored instructions."""
    if not attempts or not attempts[-1].get('evaluation',{}).get('passed'):
        return []
    failed = {c['name'].split('-')[0] for a in attempts[:-1]
              for c in a.get('evaluation',{}).get('checks',[]) if c.get('passed') is False}
    return [{'skill':k, 'lesson':LESSONS[k]} for k in sorted(failed) if k in LESSONS]


def load_experience(run_path):
    """Reject changed sources, changed examiner, incomplete/failed runs and edits to lessons.

    Local trusted workspace provenance, not cryptographic proof against its owner.
    No arbitrary file names or paths from reports are opened.
    """
    if any(p.is_symlink() for p in (run_path,*run_path.parents)):
        raise ValueError('Symlink experience path')
    root = run_path.resolve()
    if not root.is_relative_to(ROOT) or not root.is_dir():
        raise ValueError('Experience must be a local school run')
    report = json.loads((root/'report.json').read_text())
    attempts = report['attempts']
    if report.get('schema')!='local-web-school.v1' or report.get('status')!='functional_pass' or not 1<=len(attempts)<=3:
        raise ValueError('Only completed functional runs can supply experience')
    if report.get('examiner_sha256')!=examiner_hash():
        raise ValueError('Examiner changed; re-evaluation required')
    for i, attempt in enumerate(attempts, 1):
        evaluation = attempt.get('evaluation')
        if evaluation is None: continue
        folder = root/f'attempt-{i}'
        if json.loads((folder/'evaluation.json').read_text()) != evaluation:
            raise ValueError('Evaluation mismatch')
        for name in FILES:
            if (folder/name).is_symlink() or digest((folder/name).read_text())!=evaluation['source_sha256'][name]:
                raise ValueError('Source changed after examination')
        if evaluation['examiner_sha256']!=examiner_hash():
            raise ValueError('Mixed examiners')
    final = attempts[-1].get('evaluation',{})
    if final.get('passed') is not True or not final.get('checks') or not all(c.get('passed') is True for c in final['checks']):
        raise ValueError('No passing evidence')
    lessons = failure_lessons(attempts)
    if report.get('experience') != lessons:
        raise ValueError('Experience differs from examiner-derived facts')
    final_sources = {n:(root/f'attempt-{len(attempts)}'/n).read_text() for n in FILES}
    validate_sources(final_sources)
    origin=report.get('revision_origin')
    if origin:
        previous=load_revision(Path(origin['path']))
        if previous['report_sha256']!=origin['report_sha256'] or previous['feedback']!=origin['feedback']:
            raise ValueError('Revision origin changed')
        skills={c['name'].split('-')[0] for c in previous['feedback']}
        existing={lesson['skill'] for lesson in lessons}
        lessons=lessons+[{'skill':k,'lesson':LESSONS[k]} for k in sorted(skills-existing) if k in LESSONS]
    # Static contract failures precede browser checks. Replay the trusted validator
    # on exact earlier model sources before deriving this additional lesson.
    for i, attempt in enumerate(attempts[:-1],1):
        if not attempt.get('contract_failure'): continue
        folder = root/f'attempt-{i}'
        original = {}
        for name in FILES:
            response = json.loads((folder/(name+'.response.json')).read_text())
            original[name] = parse_source(response['content'])
            if original[name] != (folder/name).read_text():
                raise ValueError('Failed source changed after generation')
        try: validate_sources(original)
        except ValueError:
            lessons = lessons + [{'skill':'source', 'lesson':
                'Before binding interactions, ensure each HTML id is unique and each requested file '
                'contains the correct source type: HTML, CSS or JavaScript. Fix the reported contract '
                'failure in the responsible file instead of reproducing the previous source.'}]
            break
    return lessons


def load_revision(path):
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.resolve().is_relative_to(ROOT):
        raise ValueError('Private non-symlink school run required')
    report=json.loads((path/'report.json').read_text())
    if report.get('schema')!='local-web-school.v1' or report.get('examiner_sha256')!=examiner_hash():
        raise ValueError('Re-examine sources with the current examiner first')
    if report.get('status')!='needs_more_learning' or not 1<=len(report['attempts'])<=3:
        raise ValueError('Completed failed school run required')
    last=report['attempts'][-1];folder=path/f"attempt-{len(report['attempts'])}"
    if folder.is_symlink():raise ValueError('Symlink attempt')
    files={}
    for name in FILES:
        if (folder/name).is_symlink() or (folder/(name+'.response.json')).is_symlink():
            raise ValueError('Symlink model artifact')
        response=json.loads((folder/(name+'.response.json')).read_text())
        files[name]=parse_source(response['content'])
        if files[name]!=(folder/name).read_text():raise ValueError('Edited model source')
    if last.get('evaluation'):
        evaluation=last['evaluation']
        if evaluation!=json.loads((folder/'evaluation.json').read_text()) or evaluation['source_sha256']!={n:digest(s) for n,s in files.items()}:
            raise ValueError('Revision evidence mismatch')
        feedback=[c for c in evaluation['checks'] if not c['passed']]
    else:
        try:validate_sources(files)
        except ValueError as exc:feedback=[{'name':'source-contract','passed':False,'error':str(exc)}]
        else:raise ValueError('No reproducible contract failure')
    if not feedback:raise ValueError('No failing checks to repair')
    return {'path':str(path.resolve()),'report_sha256':digest((path/'report.json').read_text()),
            'variant':report['variant'],'files':files,'feedback':feedback}


def teach(config, variant, max_attempts, experience, provider=None, examiner=examine, revision=None):
    ROOT.mkdir(exist_ok=True)
    if any(p.is_symlink() for p in (ROOT,*ROOT.parents)) or ROOT.stat().st_dev!=Path('/home').stat().st_dev:
        raise ValueError('Linux workspace required')
    out = Path(tempfile.mkdtemp(prefix='stamps-', dir=ROOT))
    report = {'schema':'local-web-school.v1', 'status':'running', 'variant':variant,
              'model':config['model'], 'digest':config['digest'], 'sampling':generation_options(config),
              'examiner_sha256':examiner_hash(), 'brief':brief(variant), 'instruction':SYSTEM,
              'experience_used':experience, 'attempts':[], 'experience':[],
              'authorship':{'website':'local_model', 'examiner_and_orchestration':'assistant'},
              'weights_trained':False, 'visual_accepted':False, 'accepted':False, 'deployed':False,
              'split':'development', 'limitations':'Same-family practice, not a held-out generalization test.'}
    if revision:
        report['revision_origin']={k:v for k,v in revision.items() if k!='files'}
    critic = provider or OllamaProvider(config | {'num_predict':1000})
    provider = provider or OllamaProvider(config)
    files = dict(revision['files']) if revision else {}
    feedback = revision['feedback'] if revision else []
    started = time.monotonic()
    def persist():
        report['elapsed_seconds'] = round(time.monotonic()-started,3)
        save(out/'report.json', report)
    persist()
    print(json.dumps({'run':str(out), 'variant':variant}), flush=True)
    try:
        for number in range(1,max_attempts+1):
            folder = out/f'attempt-{number}'; folder.mkdir()
            attempt = {'number':number,'generations':[], 'feedback_received':feedback}
            report['attempts'].append(attempt); persist()
            diagnosis=''
            if feedback:
                check_idle()
                request={'brief':brief(variant),'current_sources':files,'independent_failures':feedback,
                         'task':'diagnose'}
                messages=[{'role':'system','content':SYSTEM}, {'role':'user','content':
                    'Diagnose this failed website before implementing a repair. Do not write source code. '
                    'Identify the root causes and which elements/files need changing, preserving the exact '
                    'acceptance contract. In particular distinguish selectors for buttons from sections. '
                    'Return JSON {"content":"concise diagnosis, at most 180 words"}.\n'+
                    json.dumps(request,ensure_ascii=False)}]
                save(folder/'diagnosis.request.json',messages)
                response=critic.complete(messages)
                save(folder/'diagnosis.response.json',response)
                diagnosis=parse_source(response['content'])
                attempt['diagnosis']={'seconds':response['elapsed_seconds'],'tokens':response['eval_count'],
                                      'raw_sha256':digest(response['content'])}
                persist()
            for name in FILES:
                check_idle()
                request = {'brief':brief(variant), 'experience':experience,
                           'current_sources':{n:s for n,s in files.items() if n!='style.css' or name=='style.css'},
                           'independent_failures':feedback,
                           'local_model_diagnosis':diagnosis,
                           'requested_file':name,
                           'instruction':'Write the complete requested file. JSON {"content":"exact source"}. '
                           'Keep compatible with the other files; you will write all three in order. '
                           'Fix failures yourself, preserve working requirements. No tests or reports in sources. '
                           'Use concise code: aim below 1800 tokens HTML, 2200 CSS, 3500 JavaScript. '
                           'Prioritize complete working functions over decorative verbosity. Missing controls '
                           'must be repaired in HTML, not hidden by ignoring null elements in JavaScript.'}
                kind = {'index.html':'HTML document','style.css':'CSS stylesheet only','app.js':'JavaScript source only'}[name]
                messages = [{'role':'system','content':SYSTEM},
                            {'role':'user','content':'Your task in THIS response: write '+name+' ('+kind+').\n'
                             'The following JSON supplies requirements, previous source and error evidence.\n'+
                             json.dumps(request,ensure_ascii=False)+'\nReturn JSON {"content":"complete '+name+
                             ' source"}. Do not return any other file. Correct the reported failures.'}]
                save(folder/(name+'.request.json'),messages)
                generated = provider.complete(messages)
                save(folder/(name+'.response.json'),generated)
                attempt['generations'].append({'file':name, 'seconds':generated['elapsed_seconds'],
                                               'tokens':generated['eval_count'],
                                               'raw_sha256':digest(generated['content'])})
                persist()
                files[name] = parse_source(generated['content'])
                (folder/name).write_text(files[name],encoding='utf-8')
                print(json.dumps({'attempt':number, 'file':name, 'tokens':generated['eval_count']}),flush=True)
            try:
                validate_sources(files)
            except ValueError as exc:
                failure = {'name':'source-contract', 'passed':False, 'error':str(exc)}
                # A static failure prevents the functional re-test; its previous
                # findings remain unresolved and must not disappear from memory.
                feedback = [c for c in feedback if c['name']!='source-contract']+[failure]
                attempt['contract_failure'] = [failure]; persist(); continue
            evaluation = examiner(files, folder, variant)
            save(folder/'evaluation.json', evaluation)
            attempt['evaluation'] = evaluation
            feedback = [c for c in evaluation['checks'] if not c['passed']]
            persist()
            print(json.dumps({'attempt':number,'passed':evaluation['passed'],
                              'checks':len(evaluation['checks']), 'failed':[c['name'] for c in feedback]}),flush=True)
            if evaluation['passed']:
                report['status'] = 'functional_pass'
                report['experience'] = failure_lessons(report['attempts'])
                break
        else:
            report['status'] = 'needs_more_learning'
    except Exception as exc:
        report['status'] = 'infrastructure_or_generation_failure'
        report['error'] = {'type':type(exc).__name__, 'message':str(exc)[:500]}
    finally:
        persist()
    return out, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true')
    p.add_argument('--max-attempts',type=int,choices=(1,2,3),default=3)
    p.add_argument('--practice-next',action='store_true',help='One additional same-family task after a functional pass')
    p.add_argument('--learn-from',type=Path)
    p.add_argument('--revise-from',type=Path,help='Continue exact failed model sources after re-examination')
    p.add_argument('--variant',type=int,choices=(0,1),default=0)
    a = p.parse_args()
    if not a.run:
        print(json.dumps({'model_invoked':False, 'brief':brief(a.variant),
                          'max_attempts':a.max_attempts, 'examiner_sha256':examiner_hash(),
                          'weights_trained':False},ensure_ascii=False)); return 0
    check_idle()
    config = configuration() | {'format':SCHEMA, 'num_ctx':16384, 'num_predict':6000,
                                'num_thread':4, 'timeout_seconds':180}
    experience = load_experience(a.learn_from) if a.learn_from else []
    revision=load_revision(a.revise_from) if a.revise_from else None
    variant=revision['variant'] if revision else a.variant
    out, report = teach(config, variant, a.max_attempts, experience, revision=revision)
    if report['status']=='functional_pass':
        from scripts.web_school.collect import collect
        print(json.dumps({'training_candidates':collect(out)}),flush=True)
    if a.practice_next and report['status']=='functional_pass':
        # Preserve both runs; practice is explicitly not independent validation.
        next_out, next_report = teach(config, 1-variant, a.max_attempts, load_experience(out))
        save(out/'practice-link.json',{'next_run':str(next_out),'status':next_report['status']})
        if next_report['status']=='functional_pass':
            print(json.dumps({'training_candidates':collect(next_out)}),flush=True)
        report = next_report
    print(json.dumps({'status':report['status'], 'weights_trained':False}),flush=True)
    return 0 if report['status']=='functional_pass' else 1


if __name__=='__main__':
    raise SystemExit(main())
