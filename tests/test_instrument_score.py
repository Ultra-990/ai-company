"""Independent checks of the data-only score and preset boundary."""
import pytest
from app.instruments import score


def fixture_score(bars=4):
    return {'schema':score.SCHEMA, 'title':'Technical fixture', 'bpm':120, 'bars':bars, 'tracks':[
        {'id':'track'+str(i), 'name':'Track '+str(i), 'instrument':instrument, 'gain_db':-12, 'pan':0,
         'patterns':[{'id':'a', 'beats':4, 'notes':[[0,60,1,90],[1,60,1,100]]}],
         'clips':[{'pattern':'a', 'at_bar':0, 'bars':bars, 'transpose':0}]}
        for i,instrument in enumerate(['kick-tech','hat','bass-deep','pluck-trance'])]}


def test_expansion_repeats_transposes_and_orders_note_off_first():
    value=fixture_score();value['tracks'][0]['clips'][0]['transpose']=12
    score.validate(value,bpm=120,bars=4)
    events=score.expand(value['tracks'][0])
    assert len(events)==16 and events[:3]==[(0,1,72,90),(1,0,72,0),(1,1,72,100)]
    assert events[-1]==(14,0,72,0)


@pytest.mark.parametrize('change',[
    lambda s:s.update(bpm=float('nan')),
    lambda s:s.update(bars=True),
    lambda s:s.update(bpm=60,bars=256),
    lambda s:s['tracks'][0].update(id='../escape'),
    lambda s:s['tracks'][0].update(id='mix'),
    lambda s:s['tracks'][0].update(instrument='/tmp/user.vst3'),
    lambda s:s['tracks'][0].update(pan=float('inf')),
    lambda s:s['tracks'][0]['patterns'][0]['notes'].append([.5,60,1,90]),
    lambda s:s['tracks'][0]['patterns'][0]['notes'].append([3,64,2,90]),
    lambda s:s['tracks'][0]['clips'].append({'pattern':'a','at_bar':0,'bars':1,'transpose':0}),
    lambda s:s['tracks'][0]['clips'][0].update(pattern='missing'),
    lambda s:s['tracks'][0]['clips'][0].update(at_bar=1),
    lambda s:s['tracks'][0].update(code='print(1)'),
])
def test_score_rejects_unsafe_or_ambiguous_data(change):
    value=fixture_score();change(value)
    with pytest.raises(ValueError):score.validate(value)


def test_requested_length_and_polyphony_are_enforced():
    value=fixture_score()
    with pytest.raises(ValueError,match='bpm_mismatch'):score.validate(value,bpm=138)
    value['tracks'][0]['patterns'][0]['notes']=[[0,p,1,90] for p in range(60,77)]
    with pytest.raises(ValueError,match='polyphony'):score.validate(value)
    value=fixture_score(256);value['bpm']=138
    assert score.validate(value)['bars']*240/138>420


def test_preset_wrapper_round_trips_and_rejects_modified_bytes(tmp_path,monkeypatch):
    import hashlib
    import struct
    import xml.etree.ElementTree as ET
    from app.instruments import runtime
    # Synthetic binary contract fixture, never a playable preset.
    component=b'sub3'+bytes(range(256))
    header=bytearray(60);header[:4]=b'CcnK';header[8:12]=b'FPCh';header[56:60]=struct.pack('>I',len(component))
    path=tmp_path/'preset.fxp';path.write_bytes(bytes(header)+component)
    monkeypatch.setattr(runtime,'DATA',tmp_path)
    monkeypatch.setattr(runtime,'PRESETS',{'test':('test','preset.fxp')})
    monkeypatch.setattr(runtime,'HASHES',{'test':hashlib.sha256(path.read_bytes()).hexdigest()})
    state=runtime.preset_state('test');length=struct.unpack('<I',state[4:8])[0]
    assert state[:4]==b'VC2!' and state[-1:]==b'\0'
    encoded=ET.fromstring(state[8:8+length]).find('IComponent').text
    size,encoded=encoded.split('.',1);alphabet='.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+'
    bits=''.join(format(alphabet.index(c),'06b')[::-1] for c in encoded)
    decoded=bytes(int(bits[i:i+8][::-1],2) for i in range(0,int(size)*8,8))
    assert decoded==component
    path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):runtime.preset_state('test')
    with pytest.raises(ValueError,match='unknown'):runtime.preset_state('../../escape')
