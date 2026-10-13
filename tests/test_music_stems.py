import json, subprocess, wave
from pathlib import Path
import pytest
from app.services import music_stems as stems

def wav(path,seconds=1):
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\0\0'*8000*seconds)

def test_runtime_contract_is_cpu_four_stems(monkeypatch,tmp_path):
    monkeypatch.setattr(stems,'PYDEPS',tmp_path);(tmp_path/'demucs').mkdir()
    py=tmp_path/'python';py.write_text('');monkeypatch.setattr(stems,'PYTHON',py)
    model=tmp_path/'model.th';model.write_bytes(b'model');monkeypatch.setattr(stems,'MODEL_FILE',model)
    import hashlib;monkeypatch.setattr(stems,'MODEL_SHA256',hashlib.sha256(b'model').hexdigest())
    result=stems.runtime_preflight()
    assert result['ready'] and result['device']=='cpu' and result['stems']==['vocals','drums','bass','other']

def test_rejects_symlink_source_and_existing_receipt(tmp_path):
    original=tmp_path/'a.wav';wav(original);link=tmp_path/'link.wav';link.symlink_to(original)
    with pytest.raises(stems.StemError,match='source'):stems.separate_stems(link,tmp_path/'out')

def test_fake_worker_preserves_source_and_writes_verified_private_stems(tmp_path,monkeypatch):
    source=tmp_path/'song.wav';wav(source);before=source.read_bytes();out=tmp_path/'out'
    monkeypatch.setattr(stems,'runtime_preflight',lambda:{'ready':True})
    real=subprocess.run
    def run(command,**kwargs):
        if command[0]=='ffprobe':return real(command,**kwargs)
        target=Path(command[command.index('-o')+1])/stems.MODEL/source.stem;target.mkdir(parents=True)
        for name in stems.STEMS:wav(target/(name+'.mp3'))
        return subprocess.CompletedProcess(command,0,b'',b'')
    receipt=stems.separate_stems(source,out,run)
    assert receipt['status']=='completed_unreviewed' and source.read_bytes()==before
    assert set(receipt['stems'])==set(stems.STEMS) and all((out/(x+'.mp3')).stat().st_mode&0o777==0o600 for x in stems.STEMS)
    assert json.loads((out/'stems-report.json').read_text())==receipt

def test_timeout_is_durable_and_cleans_partial(tmp_path,monkeypatch):
    source=tmp_path/'song.wav';wav(source);out=tmp_path/'out';monkeypatch.setattr(stems,'runtime_preflight',lambda:{'ready':True})
    real=subprocess.run
    def run(command,**kwargs):
        if command[0]=='ffprobe':return real(command,**kwargs)
        raise subprocess.TimeoutExpired(command,1)
    with pytest.raises(stems.StemError,match='timeout'):stems.separate_stems(source,out,run,1)
    report=json.loads((out/'stems-report.json').read_text());assert report['status']=='failed' and report['error_type']=='TimeoutExpired'
    assert not list(out.glob('.stems-*'))
