"""Blind the matched service outputs before independent human/teacher scoring.

Never generates corrections or exports exam answers for training. Scores are
examiner judgments, not objective certification or a market/assistant benchmark.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.check_technical_reviewer import check_response,save
from scripts.qwen_evaluation_catalog import load_reviewer_suite,REVIEWER_CHECKSUM
from scripts.qwen_qlora_smoke import ROOT

CRITERIA={
    'first_issue':'First rubric issue detected and correctly explained with a practical correction.',
    'second_issue':'Second rubric issue detected and correctly explained with a practical correction.',
    'controls':'Accurate control statements preserved; optional elaborations are suggestions, not defects.',
    'evidence':'No invented causes/guarantees/results; source scope and uncertainty accurately represented.',
    'deliverables':'Five deliverables are specific and coherent; citation needs seek meaningful bounded evidence or are appropriately empty.'}


def local_path(path):
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Private non-symlink research workspace required')


def prepare(run):
    local_path(run)
    report=json.loads((run/'report.json').read_text());suite=load_reviewer_suite()
    if (report['status']!='completed_research_pending_semantic_review'
            or report['protocol']['reviewer_evaluation']['sha256']!=REVIEWER_CHECKSUM):
        raise ValueError('Complete pinned matched experiment required')
    phases={phase:json.loads((run/(phase+'.json')).read_text()) for phase in ('reviewer_baseline','reviewer_after')}
    for phase,entries in phases.items():
        if entries!=report[phase] or [e['id'] for e in entries]!=[c['id'] for c in suite['cases']]:
            raise ValueError('Changed or incomplete service evidence')
    packet={'criteria':CRITERIA,'samples':[]};mapping={}
    for i,case in enumerate(suite['cases']):
        order=list(phases);random.SystemRandom().shuffle(order)
        if phases[order[0]][i]['prompt_sha256']!=phases[order[1]][i]['prompt_sha256']:
            raise ValueError('Before/after prompts differ')
        for phase in order:
            entry=phases[phase][i]
            if sha256(entry['content'].encode()).hexdigest()!=entry['response_sha256']:
                raise ValueError('Changed raw model answer')
            sample=f'sample-{len(mapping)+1:02d}'
            valid=True
            try:check_response(entry['content'],case['article'],case['sources'])
            except (ValueError,TypeError):valid=False
            packet['samples'].append({'sample':sample,'case':case['id'],'article':case['article'],
              'sources':case['sources'],'expected_issues':case['expected_issues'],
              'correct_controls':case['correct_controls'],'content':entry['content'],
              'structure_valid':valid,'stop_token_seen':entry['stop_token_seen']})
            mapping[sample]={'phase':phase,'case':case['id'],'response_sha256':entry['response_sha256']}
    out=Path(tempfile.mkdtemp(prefix='exam-assessment-',dir=run))
    save(out/'blind-packet.json',packet)
    save(out/'mapping-OPEN-AFTER-SCORING.json',{'mapping':mapping,
        'packet_sha256':sha256((out/'blind-packet.json').read_bytes()).hexdigest(),
        'report_sha256':sha256((run/'report.json').read_bytes()).hexdigest()})
    return out


def finalize(out):
    local_path(out)
    packet=json.loads((out/'blind-packet.json').read_text())
    mapping=json.loads((out/'mapping-OPEN-AFTER-SCORING.json').read_text())
    judgments=json.loads((out/'judgments.json').read_text())
    report=json.loads((out.parent/'report.json').read_text())
    if (sha256((out/'blind-packet.json').read_bytes()).hexdigest()!=mapping['packet_sha256']
            or sha256((out.parent/'report.json').read_bytes()).hexdigest()!=mapping['report_sha256']
            or packet['criteria']!=CRITERIA or set(judgments)!=set(mapping['mapping'])):
        raise ValueError('Changed evidence, rubric or incomplete judgment set')
    expected={(phase,e['id']):e['response_sha256'] for phase in ('reviewer_baseline','reviewer_after')
              for e in report[phase]}
    observed={}
    for sample in packet['samples']:
        origin=mapping['mapping'][sample['sample']];key=(origin['phase'],origin['case'])
        checksum=sha256(sample['content'].encode()).hexdigest()
        if (key in observed or origin['case']!=sample['case'] or expected.get(key)!=checksum
                or origin['response_sha256']!=checksum):
            raise ValueError('Blind phase mapping does not match original outputs')
        observed[key]=checksum
    if observed!=expected:raise ValueError('Incomplete phase mapping')
    result={'schema':'reviewer-matched-assessment.v1','criteria':CRITERIA,'samples':[],
            'blind_judgments_sha256':sha256((out/'judgments.json').read_bytes()).hexdigest(),
            'production_ready':False,'parity_proven':False,'training_exported':False}
    for sample in packet['samples']:
        judgment=judgments[sample['sample']]
        if (set(judgment)!={'scores','notes'} or set(judgment['scores'])!=set(CRITERIA)
                or any(type(v) is not bool for v in judgment['scores'].values())
                or not isinstance(judgment['notes'],str) or not 10<=len(judgment['notes'])<=3000):
            raise ValueError('Explicit boolean criteria and examiner notes required')
        accepted=all(judgment['scores'].values()) and sample['structure_valid'] and sample['stop_token_seen']
        result['samples'].append(mapping['mapping'][sample['sample']]|judgment|
            {'sample':sample['sample'],'structure_valid':sample['structure_valid'],
             'stop_token_seen':sample['stop_token_seen'],'rubric_points':sum(judgment['scores'].values()),
             'passed_probe':accepted})
    result['totals']={phase:{'rubric_points':sum(x['rubric_points'] for x in result['samples'] if x['phase']==phase),
                              'passed_probes':sum(x['passed_probe'] for x in result['samples'] if x['phase']==phase)}
                       for phase in ('reviewer_baseline','reviewer_after')}
    save(out/'comparison.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',type=Path);group.add_argument('--finalize',type=Path)
    args=parser.parse_args()
    if args.prepare:print(json.dumps({'assessment':str(prepare(args.prepare))}))
    else:print(json.dumps(finalize(args.finalize)['totals']))


if __name__=='__main__':main()
