import numpy as np
from app.instruments.audio_checks import inspect_source


def test_overload_detected_before_gain_can_hide_it():
    audio=np.zeros((1000,2),dtype=np.float32);audio[400:420,0]=8
    result=inspect_source(audio,sample_rate=1000,frame_offset=6000)
    assert not result['passed'] and result['first_bad_seconds']==6.4
    assert result['overload_frames']==20 and result['raw_peak']==8
    # A final mix peak check alone misses this failure after attenuation.
    assert np.abs(audio*.05).max()<1


def test_nonfinite_signal_is_rejected_and_normal_signal_not_quality_accepted():
    audio=np.full((100,2),.1,dtype=np.float32)
    clean=inspect_source(audio,sample_rate=1000,frame_offset=0)
    assert clean['passed'] and clean['scope']=='source_integrity_only_not_musical_quality'
    audio[5,1]=np.nan
    result=inspect_source(audio,sample_rate=1000,frame_offset=0)
    assert not result['passed'] and not result['finite'] and result['first_bad_seconds']==.005


def test_renderer_stops_before_export_when_synth_overloads(tmp_path, monkeypatch):
    import json
    import sys
    import types
    import pytest
    from scripts import render_instrument_score as renderer
    from tests.test_instrument_score import fixture_score
    from scripts.generation_limits import UNIT
    monkeypatch.setattr(renderer,'cgroup_path',lambda:tmp_path/UNIT)
    monkeypatch.setattr(renderer,'verify_limits',lambda:{'test_only':True})
    monkeypatch.setattr(renderer.runtime,'preflight',lambda:{'test_only':True})
    monkeypatch.setattr(renderer.runtime,'preset_state',lambda _:b'fixture')
    class Plugin:
        is_instrument=True
        name='Surge XT'
        def __call__(self, messages, *, duration, sample_rate, **kwargs):
            audio=np.zeros((2,round(duration*sample_rate)),dtype=np.float32)
            if messages: audio[:,5]=8
            return audio
    fake=types.ModuleType('pedalboard');fake.__version__='0.9.26';fake.load_plugin=lambda _:Plugin()
    fake_io=types.ModuleType('pedalboard.io')
    def unexpected_export(*args,**kwargs): pytest.fail('overloaded audio exported')
    fake_io.AudioFile=unexpected_export
    fake_mido=types.ModuleType('mido');fake_mido.MidiFile=lambda **kw:types.SimpleNamespace(tracks=[])
    fake_mido.MidiTrack=list;fake_mido.MetaMessage=lambda *a,**kw:kw
    fake_mido.Message=lambda *a,**kw:kw;fake_mido.bpm2tempo=lambda bpm:500000
    monkeypatch.setitem(sys.modules,'pedalboard',fake)
    monkeypatch.setitem(sys.modules,'pedalboard.io',fake_io)
    monkeypatch.setitem(sys.modules,'mido',fake_mido)
    path=tmp_path/'score.json';path.write_text(json.dumps(fixture_score()))
    with pytest.raises(ValueError,match='source_overload'):
        renderer.render(path,tmp_path/'output')
    failure=json.loads((tmp_path/'output/source-failure.json').read_text())
    assert failure['raw_peak']==8 and failure['track']=='track0'
    assert not (tmp_path/'output/mix.wav').exists()
    assert not (tmp_path/'output/render.json').exists()
