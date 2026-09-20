from hashlib import sha256
import json

import pytest

from scripts import reviewer_exam_assessment as lab


def test_blinded_labels_and_scores_cannot_hide_invalid_or_incomplete_outputs(tmp_path,monkeypatch):
    monkeypatch.setattr(lab,'ROOT',tmp_path)
    suite=lab.load_reviewer_suite()
    value={'comments':[],'top_fixes':['Fixture'],'citation_needs':[],
           'additions':['Fixture'],'verdict':'needs_technical_revision',
           'reader_intent':'Fixture','uncertainty':'Fixture'}
    report={'status':'completed_research_pending_semantic_review',
            'protocol':{'reviewer_evaluation':{'sha256':lab.REVIEWER_CHECKSUM}}}
    for phase in ('reviewer_baseline','reviewer_after'):
        entries=[]
        for i,case in enumerate(suite['cases']):
            raw=json.dumps(value) if phase=='reviewer_after' or i else 'not-json'
            entries.append({'id':case['id'],'content':raw,'response_sha256':sha256(raw.encode()).hexdigest(),
                            'prompt_sha256':'0'*64,'stop_token_seen':not (phase=='reviewer_after' and i==1)})
        report[phase]=entries;lab.save(tmp_path/(phase+'.json'),entries)
    lab.save(tmp_path/'report.json',report)
    out=lab.prepare(tmp_path);packet=json.loads((out/'blind-packet.json').read_text())
    assert len(packet['samples'])==6
    assert 'reviewer_baseline' not in json.dumps(packet) and 'reviewer_after' not in json.dumps(packet)
    judgments={s['sample']:{'scores':{c:True for c in lab.CRITERIA},'notes':'Fixture judgment only.'} for s in packet['samples']}
    lab.save(out/'judgments.json',judgments)
    compared=lab.finalize(out)
    assert compared['totals']['reviewer_baseline']['passed_probes']==2
    assert compared['totals']['reviewer_after']['passed_probes']==2
    assert compared['production_ready'] is compared['training_exported'] is False
    mapping_path=out/'mapping-OPEN-AFTER-SCORING.json'
    original=mapping_path.read_text();mapping=json.loads(original)
    first=next(iter(mapping['mapping']));mapping['mapping'][first]['phase']='invented-phase'
    lab.save(mapping_path,mapping)
    with pytest.raises(ValueError,match='phase mapping'):lab.finalize(out)
    mapping_path.write_text(original)
    report['changed']=True;lab.save(tmp_path/'report.json',report)
    with pytest.raises(ValueError,match='Changed evidence'):lab.finalize(out)
