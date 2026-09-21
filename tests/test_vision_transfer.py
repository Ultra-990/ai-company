import json
from hashlib import sha256
import pytest
from scripts import check_vision_transfer as exam
from scripts.interior_school_contract import curriculum_metadata


def test_curriculum_cannot_silently_change_split():
    assert curriculum_metadata({})['data_split']=='train'
    assert curriculum_metadata({'curriculum':'cottage-reading-eval-v1'})['data_split']=='test'
    with pytest.raises(ValueError):curriculum_metadata({'curriculum':'cottage-reading-eval-v1','data_split':'train'})


def fixture_exam(tmp_path):
    report={'status':'completed_pending_blind_review','results':[]}
    image=tmp_path/'fixture.png';image.write_bytes(b'fixture bytes')
    for phase in ('base','adapter'):
        for case in exam.SHAPES:
            raw=phase+' '+case
            report['results'].append({'phase':phase,'case':case,'image':str(image),'image_sha256':sha256(image.read_bytes()).hexdigest(),'content':raw,
                'input_ids_sha256':'same-input','response_sha256':sha256(raw.encode()).hexdigest(),
                'structure_valid':True,'stop_token_seen':True})
    exam.save(tmp_path/'report.json',report);exam.blind(tmp_path,report)
    packet=json.loads((tmp_path/'blind-packet.json').read_text())
    exam.save(tmp_path/'judgments.json',{s['sample']:{'scores':{k:True for k in exam.CRITERIA},
                                                   'notes':'Independent fixture scoring.'} for s in packet['samples']})
    return packet


def test_blind_packet_and_comparison_keep_all_six_sources(tmp_path):
    packet=fixture_exam(tmp_path)
    assert len(packet['samples'])==6 and all('phase' not in s for s in packet['samples'])
    comparison=exam.finalize(tmp_path)
    assert comparison['totals']=={'base':{'points':15,'passed':3},'adapter':{'points':15,'passed':3}}
    assert comparison['parity_proven'] is False and comparison['training_exported'] is False


def test_changed_blind_mapping_is_rejected(tmp_path):
    fixture_exam(tmp_path)
    path=tmp_path/'mapping-OPEN-AFTER-SCORING.json';mapping=json.loads(path.read_text())
    first=mapping['mapping']['sample-01'];first['phase']='adapter' if first['phase']=='base' else 'base'
    exam.save(path,mapping)
    with pytest.raises(ValueError):exam.finalize(tmp_path)


def test_changed_pixels_after_generation_invalidate_assessment(tmp_path):
    fixture_exam(tmp_path);(tmp_path/'fixture.png').write_bytes(b'different bytes')
    with pytest.raises(ValueError,match='image changed'):exam.finalize(tmp_path)
