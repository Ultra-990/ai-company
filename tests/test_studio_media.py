from hashlib import sha256
import json

from PIL import Image
import pytest

from scripts import build_studio_media as builder, studio_gallery as gallery


def plan():
    return {'assets':[{'id':key,'prompt':'Original sculptural image, no text.',
        'alt':'Opis obrazu','title':'Studium'} for key in builder.IDS]}


def test_art_plan_is_only_three_bounded_text_descriptions():
    assert len(builder.validate_plan(plan()))==3
    for data in [{}, {'assets':[]}, plan()|{'command':'run'}]:
        with pytest.raises(ValueError):builder.validate_plan(data)
    for changes in [{'id':'other'},{'prompt':'x'*1501},{'title':'x\ncommand'},{'alt':None},{'node':'arbitrary'}]:
        data=plan();data['assets'][0].update(changes)
        with pytest.raises(ValueError):builder.validate_plan(data)


def test_dry_mode_does_not_touch_gpu_or_models(monkeypatch):
    monkeypatch.setattr(builder,'check_idle',lambda:pytest.fail('Dry mode must not inspect/invoke models'))
    assert builder.main(['--plan'])==0


def test_foreign_work_refuses_further_generation_without_killing_it(monkeypatch):
    from app.services import local_ollama
    monkeypatch.setattr(local_ollama,'ensure_idle',lambda:None)
    monkeypatch.setattr(builder.subprocess,'check_output',lambda *a,**k:'foreign-container')
    with pytest.raises(RuntimeError,match='container'):builder.external_idle()
    monkeypatch.setattr(builder.subprocess,'check_output',lambda *a,**k:'')
    monkeypatch.setattr(builder,'local_json',lambda *a:{'queue_running':[1],'queue_pending':[]})
    with pytest.raises(RuntimeError,match='ComfyUI'):builder.external_idle()
    monkeypatch.setattr(builder,'local_json',lambda *a:{'queue_running':[],'queue_pending':[]})
    builder.external_idle()


def media(tmp_path,monkeypatch):
    monkeypatch.setattr(gallery,'ROOT',tmp_path)
    image=tmp_path/'sample.png';Image.new('RGB',(768,512),(120,150,70)).save(image)
    report={'schema':'studio-media.v1','status':'rendered','own_service_stopped':True,
            'assets':[dict(entry,status='rendered',file='sample.png',sha256=sha256(image.read_bytes()).hexdigest()) for entry in plan()['assets']]}
    path=tmp_path/'report.json';path.write_text(json.dumps(report))
    return path,report


def test_verified_pngs_become_data_urls_and_escaped_markup(tmp_path,monkeypatch):
    path,report=media(tmp_path,monkeypatch)
    report['assets'][0]['title']='<script>alert(1)</script>'
    path.write_text(json.dumps(report))
    assets=gallery.load_assets(path)
    assert all(a['src'].startswith('data:image/png;base64,') for a in assets)
    source='<head></head><body><div class="art" aria-hidden="true"><i></i><i></i><i></i></div><section id="services"></section></body>'
    html,files=gallery.enhance(source,{'app.js':'original'},assets)
    assert '<script>alert(1)</script>' not in html and '&lt;script&gt;' in html
    assert html.count('data-art=')==3 and 'id="art-viewer"' in html
    assert files['app.js']=='original' and 'studio-gallery.js' in files


@pytest.mark.parametrize('change',['status','hash','escape','size','stopped'])
def test_media_must_be_local_complete_unchanged_and_bounded(tmp_path,monkeypatch,change):
    path,report=media(tmp_path,monkeypatch)
    if change=='status':report['status']='pending'
    if change=='hash':report['assets'][0]['sha256']='wrong'
    if change=='escape':report['assets'][0]['file']='../escape.png'
    if change=='size':
        image=tmp_path/'sample.png';Image.new('RGB',(20,20)).save(image)
        report['assets'][0]['sha256']=sha256(image.read_bytes()).hexdigest()
    if change=='stopped':report['own_service_stopped']=False
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):gallery.load_assets(path)
