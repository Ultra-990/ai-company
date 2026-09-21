"""Provenance/data tests use synthetic fixtures, never real model inference."""
from hashlib import sha256
import json

from PIL import Image
import pytest

from scripts import interior_learning_records as records
from scripts import interior_school as school
from scripts.prepare_training_data import validate_record,DatasetError


def fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(school,'ROOT',tmp_path)
    report={'schema':'interior-school.v1','status':'packaged_pending_independent_review',
            'synthetic':True,'published':False,'model':'fixture','digest':'0'*64,'inspections':[]}
    rendered={'schema':'interior-school.v1','status':'rendered','assets':[]}
    judgments={'schema':'interior-teacher-judgments.v1','reviewer':'assistant_direct_visual_review',
               'synthetic_privacy_checked':True,'split':'train','assets':[]}
    for i,key in enumerate(school.SHAPES):
        p=tmp_path/(key+'.png');im=Image.new('RGB',school.SHAPES[key],(20+i,30,40));im.save(p)
        image_sha=records.digest(p)
        ob={'description':'A complete fixture description.','alt_text':'A complete fixture alt text.',
            'visible_details':['one','two','three'],'possible_defects':[],
            'brand_fit':'Fixture evidence.','recommendation':'candidate','uncertainty':'Fixture limit.'}
        raw=json.dumps(ob,indent=2)
        request={'system':'Exact fixture system.','user':'Exact fixture task.','image_source':str(p),
                 'image_sha256':image_sha,'config':{'model':'fixture','digest':'0'*64}}
        school.save(tmp_path/(key+'-request.json'),request)
        school.save(tmp_path/(key+'-response.json'),{'model':'fixture','digest':'0'*64,'content':raw})
        rendered['assets'].append({'id':key,'file':p.name,'sha256':image_sha})
        report['inspections'].append({'id':key,'image_sha256':image_sha,'image_source':str(p),
                                      'response_sha256':sha256(raw.encode()).hexdigest(),'observation':ob})
        judgments['assets'].append({'id':key,'approved':i==0,'notes':'Fixture independent decision.',
            'image_sha256':image_sha,'request_sha256':records.digest(tmp_path/(key+'-request.json')),
            'response_sha256':records.digest(tmp_path/(key+'-response.json'))})
    rendered_path=tmp_path/'render.json';school.save(rendered_path,rendered)
    report.update(source_report=str(rendered_path),source_sha256=records.digest(rendered_path))
    source=tmp_path/'report.json';school.save(source,report)
    judgments['report_sha256']=records.digest(source)
    proof=tmp_path/'judgments.json';school.save(proof,judgments)
    return source,proof


def test_export_keeps_image_exact_response_and_train_family(tmp_path,monkeypatch):
    source,proof=fixture(tmp_path,monkeypatch)
    out=records.export(source,proof)
    rows=[json.loads(x) for x in (out/'records.jsonl').read_text().splitlines()]
    assert len(rows)==1
    row=rows[0]
    assert row['messages'][2]['content']==records.read(tmp_path/'hero-response.json')['content']
    assert row['messages'][1]['content'][1]=={'type':'image','image_id':'image-0'}
    assert (out/row['images'][0]['file']).read_bytes()==(tmp_path/'hero.png').read_bytes()
    assert row['split']=='train' and row['family'].startswith('interior-render-')
    assert row['messages'][0]['content']=='Exact fixture system.'
    manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['ready_for_trainer'] is False and manifest['training_started'] is False
    with pytest.raises(DatasetError):validate_record(row)


@pytest.mark.parametrize('target',['hero.png','hero-request.json','hero-response.json','render.json'])
def test_rejects_changed_image_prompt_response_or_render(tmp_path,monkeypatch,target):
    source,proof=fixture(tmp_path,monkeypatch)
    path=tmp_path/target
    if path.suffix=='.png':path.write_bytes(path.read_bytes()+b'changed')
    else:
        obj=json.loads(path.read_text());obj['changed']=True;school.save(path,obj)
    with pytest.raises(ValueError):records.collect(source,proof)


def test_model_self_recommendation_cannot_approve_or_move_to_test(tmp_path,monkeypatch):
    source,proof=fixture(tmp_path,monkeypatch)
    decisions=records.read(proof)
    for decision in decisions['assets']:decision['approved']=False
    school.save(proof,decisions)
    assert records.collect(source,proof)[0]==[]
    with pytest.raises(ValueError,match='No approved'):records.export(source,proof)
    decisions['assets'][0]['approved']=True;decisions['split']='test';school.save(proof,decisions)
    with pytest.raises(ValueError):records.collect(source,proof)


def test_evaluation_render_cannot_be_relabelled_as_training_inspection(tmp_path,monkeypatch):
    source,proof=fixture(tmp_path,monkeypatch)
    rendered=records.read(tmp_path/'render.json')
    rendered.update(curriculum='cottage-reading-eval-v1',data_split='test',family='cottage-reading-room-001')
    school.save(tmp_path/'render.json',rendered)
    report=records.read(source);report['source_sha256']=records.digest(tmp_path/'render.json');school.save(source,report)
    decisions=records.read(proof);decisions['report_sha256']=records.digest(source);school.save(proof,decisions)
    with pytest.raises(ValueError,match='Reserved evaluation images'):records.collect(source,proof)
