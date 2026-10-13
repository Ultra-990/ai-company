import numpy as np
import pytest
from app.services.music_timing import RATE, analyze_samples, edit_timing


@pytest.mark.parametrize('bpm', [90, 120, 150])
def test_known_metronome_is_measured_from_sound(bpm):
    signal = np.zeros(RATE * 20, dtype=np.float32)
    rng = np.random.default_rng(3)
    click = rng.normal(size=320) * np.exp(-np.arange(320)/60)
    for t in np.arange(.3, 19.9, 60/bpm):
        start = round(t*RATE); signal[start:start+320] += click
    report = analyze_samples(signal)
    assert report['pulse_usable'] and abs(report['tempo_bpm']-bpm)<2
    expected = np.arange(.3, 19.9, 60/bpm)
    errors = [min(abs(expected-t)) for t in report['beat_seconds'][2:-2]]
    assert np.median(errors) < .06


def test_silence_uses_fallback_and_does_not_invent_beats():
    analysis = analyze_samples(np.zeros(RATE*10))
    assert not analysis['pulse_usable'] and analysis['tempo_bpm'] is None
    plan = edit_timing(120, analysis)
    assert plan['shot_count'] == 24 and plan['strategy']=='uniform_fallback'


@pytest.mark.parametrize('duration', [1, 5, 5.01, 6.2, 119.99, 120])
def test_cuts_cover_whole_song_once_on_frames_without_exceeding_source(duration):
    plan = edit_timing(duration, {'pulse_usable':True, 'beat_seconds':np.arange(.3,120,.46).tolist(),
        'energy_per_second':[.1,.2,.8,.9]*30})
    shots = plan['shots']
    assert shots[0]['start_frame']==0 and shots[-1]['end_frame']==round(duration*24)
    assert all(a['end_frame']==b['start_frame'] for a,b in zip(shots,shots[1:]))
    assert all(0 < s['duration_seconds'] <=5 for s in shots)
    assert sum(s['end_frame']-s['start_frame'] for s in shots)==round(duration*24)
    assert plan['shot_count']<=64


def test_energy_changes_shot_density_without_retiming_dancers():
    analysis={'pulse_usable':True,'beat_seconds':np.arange(.5,120,.5).tolist(),
              'energy_per_second':[.1]*60+[.9]*60}
    shots=edit_timing(120,analysis)['shots']
    slow=[s['duration_seconds'] for s in shots if s['start_seconds']<55]
    fast=[s['duration_seconds'] for s in shots if 65<s['start_seconds']<110]
    # Equal values at the high quantile still represent a high-energy plateau.
    assert np.mean(fast)<np.mean(slow)


@pytest.mark.parametrize('duration',[0,901,float('nan'),float('inf')])
def test_invalid_duration_refused(duration):
    with pytest.raises(ValueError):edit_timing(duration)


@pytest.mark.parametrize('kind',['noise','tone'])
def test_sound_without_pulse_does_not_invent_a_tempo(kind):
    samples=(np.random.default_rng(42).normal(0,.1,RATE*15) if kind=='noise' else
             .1*np.sin(np.arange(RATE*15)/RATE*2*np.pi*440))
    assert not analyze_samples(samples)['pulse_usable']
