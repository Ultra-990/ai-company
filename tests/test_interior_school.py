import base64
import io
import json
from hashlib import sha256

from PIL import Image
import pytest

from app.services import local_vision as vision
from scripts import interior_school as school
from scripts.interior_school_contract import Plan,check_plan,Inspection,VISION_INSTRUCTION,inspection_instruction


def fixture_plan():
    return {'article_title':'Fixture article','proposed_slug':'fixture-article',
            'meta_description':'Fixture descriptive article metadata.',
            'writer_brief':'Fixture brief','outline':['a','b','c'],'publishing_checks':['a','b','c'],
            'assets':[{'id':key,'filename':'fixture-'+key+'.png','title':'Fixture',
                       'prompt':' '.join(['word']*90),'concept':'Fixture','brand_fit':'Fixture'} for key in school.SHAPES]}


def test_model_file_paths_and_plan_counts_are_bounded():
    obj=fixture_plan();check_plan(Plan.model_validate(obj))
    obj['assets'][0]['filename']='../../outside.png'
    with pytest.raises(ValueError):check_plan(Plan.model_validate(obj))
    obj=fixture_plan();obj['assets'][1]['filename']=obj['assets'][0]['filename']
    with pytest.raises(ValueError,match='Distinct'):check_plan(Plan.model_validate(obj))
    obj=fixture_plan();obj['assets'][0]['prompt']='too short'
    with pytest.raises(ValueError,match='80'):check_plan(Plan.model_validate(obj))


def test_vision_only_accepts_one_bounded_png_not_url_or_file_path(monkeypatch):
    config={'model':'fixture','digest':'0'*64,'num_ctx':8192,'num_predict':1000,'num_thread':4,'timeout_seconds':180}
    monkeypatch.setattr(vision,'configuration',lambda:config)
    stream=io.BytesIO();Image.new('RGB',(768,512),'ivory').save(stream,format='PNG')
    encoded=base64.b64encode(stream.getvalue()).decode()
    payload={'config':config,'messages':[{'role':'system','content':'Fixture'},
              {'role':'user','content':'Inspect','images':[encoded]}]}
    vision.validate_payload(payload)
    for value in ('https://example.com/image.png','/etc/passwd',base64.b64encode(b'not an image').decode()):
        payload['messages'][1]['images']=[value]
        with pytest.raises((ValueError,OSError)):vision.validate_payload(payload)
    payload['messages'][1]['images']=[encoded,encoded]
    with pytest.raises(ValueError):vision.validate_payload(payload)


def test_source_stage_and_spreadsheet_formula_protection(tmp_path,monkeypatch):
    monkeypatch.setattr(school,'ROOT',tmp_path)
    path=tmp_path/'report.json';path.write_text(json.dumps({'schema':'interior-school.v1','status':'planned'}))
    school.load_stage(path,'planned')
    with pytest.raises(ValueError):school.load_stage(path,'rendered')
    assert school.csv_cell('=HYPERLINK("bad")').startswith("'")
    assert school.csv_cell('A warm kitchen')=='A warm kitchen'


def test_default_never_invokes_model(monkeypatch,capsys):
    monkeypatch.setattr('sys.argv',['interior_school.py','--plan'])
    monkeypatch.setattr(school.media,'check_idle',lambda:pytest.fail('Unexpected model preflight'))
    assert school.main()==0 and json.loads(capsys.readouterr().out)['model_invoked'] is False


def test_visible_schema_matches_decoder_contract_and_legacy_is_preserved():
    assert inspection_instruction('legacy')==VISION_INSTRUCTION
    for name in ('schema-visible-v1','grounded-concise-v1'):
        instruction=inspection_instruction(name)
        assert len(instruction)<12000
        assert json.loads(instruction.split('maxima, not targets):\n')[1])==Inspection.model_json_schema()
    with pytest.raises(ValueError):inspection_instruction('arbitrary')


def test_feedback_rejects_changed_model_answer_or_different_render(tmp_path,monkeypatch):
    monkeypatch.setattr(school,'ROOT',tmp_path)
    rendered=tmp_path/'render.json';rendered.write_text('{}')
    previous={'schema':'interior-school.v1','status':'packaged_pending_independent_review',
              'source_report':str(rendered),'source_sha256':sha256(rendered.read_bytes()).hexdigest(),
              'model':'fixture','digest':'0'*64,'inspections':[]}
    for key in school.SHAPES:
        raw=json.dumps({'fixture':key})
        (tmp_path/(key+'-response.json')).write_text(json.dumps({'content':raw,'model':'fixture','digest':'0'*64}))
        previous['inspections'].append({'id':key,'response_sha256':sha256(raw.encode()).hexdigest(),
                                        'observation':json.loads(raw)})
    source=tmp_path/'report.json';source.write_text(json.dumps(previous))
    feedback={'source_report':str(source),'source_sha256':sha256(source.read_bytes()).hexdigest(),
              'comments':{key:'Reinspect this example.' for key in school.SHAPES}}
    path=tmp_path/'feedback.json';path.write_text(json.dumps(feedback))
    assert school.load_feedback(path,rendered)==feedback
    with pytest.raises(ValueError,match='Changed feedback source'):
        school.load_feedback(path,tmp_path/'different.json')
    raw=json.loads((tmp_path/'hero-response.json').read_text());raw['content']='{}'
    (tmp_path/'hero-response.json').write_text(json.dumps(raw))
    with pytest.raises(ValueError,match='Changed reviewed response'):
        school.load_feedback(path,rendered)


def test_inspection_sees_pixels_and_packages_exact_model_metadata(tmp_path,monkeypatch):
    import csv
    monkeypatch.setattr(school,'ROOT',tmp_path)
    plan=fixture_plan()
    original=tmp_path/'original.json';original.write_text(json.dumps({'plan':plan}))
    source=tmp_path/'render.json'
    rendered={'schema':'interior-school.v1','status':'rendered','own_service_stopped':True,
              'source_report':str(original),'source_sha256':sha256(original.read_bytes()).hexdigest(),
              'plan':plan,'assets':[]}
    images=[]
    for i,asset in enumerate(plan['assets']):
        stream=io.BytesIO();Image.new('RGB',school.SHAPES[asset['id']],(50+i,80,100)).save(stream,format='PNG')
        image=stream.getvalue();images.append(image)
        (tmp_path/asset['filename']).write_bytes(image)
        width,height=school.SHAPES[asset['id']]
        rendered['assets'].append({'id':asset['id'],'file':asset['filename'],'sha256':sha256(image).hexdigest(),
                                  'width':width,'height':height})
    source.write_text(json.dumps(rendered))
    class Connection:
        status=200
        def __init__(self,*a,**kw):pass
        def request(self,*a,**kw):pass
        def getresponse(self):return self
        def read(self,n):return b'{"capabilities":["vision"]}'
        def close(self):pass
    monkeypatch.setattr(school.http.client,'HTTPConnection',Connection)
    monkeypatch.setattr(school.media,'check_idle',lambda:None)
    monkeypatch.setattr(school,'configuration',lambda:{'model':'fixture','digest':'0'*64})
    observations=[]
    def complete(config,system,user,image):
        i=len(observations)
        assert image==images[i]
        assert plan['assets'][i]['prompt'] not in system+user
        assert plan['assets'][i]['filename'] not in system+user
        observation={'description':f'Fixture observed description {i}.','alt_text':f'Fixture alt text {i}.',
                     'visible_details':['one','two','three'],'possible_defects':[],
                     'brand_fit':'Fixture fit.','recommendation':'needs_human_review','uncertainty':'Fixture uncertainty.'}
        observations.append(observation)
        return {'content':json.dumps(observation),'model':'fixture','digest':'0'*64}
    monkeypatch.setattr(school.local_vision,'complete',complete)
    out=tmp_path/'package';out.mkdir();report={'independently_accepted':False}
    school.inspect(source,out,report,lambda:None)
    assert report['status']=='packaged_pending_independent_review'
    assert report['independently_accepted'] is False
    assert len(observations)==3
    rows=list(csv.DictReader((out/'image-tracker.csv').open()))
    url=json.loads((out/'new-url-package.json').read_text())
    assert url['live_url'] is None
    for i,(asset,observation) in enumerate(zip(plan['assets'],observations)):
        assert (out/'library'/asset['filename']).read_bytes()==images[i]
        assert rows[i]['description']==observation['description']
        assert rows[i]['alt_text']==url['assets'][i]['alt_text']==observation['alt_text']
        assert rows[i]['review']=='independent_review_pending'
        assert rows[i]['publication']=='not_published'
        assert observation['description'] in (out/'writer-package.md').read_text()
