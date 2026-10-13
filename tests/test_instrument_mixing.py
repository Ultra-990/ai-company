"""Signal checks, not acceptance tests for musical taste."""
import numpy as np
import pytest
from app.instruments.mixing import (LevelMeter, balance_plan, kick_ducking,
                                    profile_for_style, TRANCE, TRANSPARENT)


def test_active_level_ignores_long_silent_intro_and_chunk_boundaries():
    rate=1000
    audio=np.concatenate((np.zeros((2000,2)), np.full((1000,2), .1), np.zeros((2000,2))))
    whole=LevelMeter(rate); whole.add(audio)
    split=LevelMeter(rate)
    for start in range(0,len(audio),137): split.add(audio[start:start+137])
    assert whole.active_dbfs()==pytest.approx(-20)
    assert split.active_dbfs()==pytest.approx(whole.active_dbfs())
    silent=LevelMeter(rate);silent.add(np.zeros((1000,2)))
    assert silent.active_dbfs() is None


def test_balance_is_bounded_and_transparent_preserves_faders():
    assert balance_plan('bass',-40,TRANCE)['balance_gain_db']==12
    assert balance_plan('bass',-40,TRANCE)['level_target_reached'] is False
    assert balance_plan('lead',0,TRANCE)['balance_gain_db']==-18
    assert balance_plan('bass',-24,TRANCE)['balance_gain_db']==6
    assert balance_plan('bass',None,TRANCE)['balance_gain_db']==0
    assert balance_plan('bass',-40,TRANSPARENT)['balance_gain_db']==0
    assert profile_for_style('Uplifting Trance')==TRANCE
    assert profile_for_style('Jazz')==TRANSPARENT
    with pytest.raises(ValueError): balance_plan('bass',float('nan'),TRANCE)


def test_sidechain_follows_kick_events_and_preserves_every_chunk_boundary():
    rate=10000; kicks=[2500,2650,8900]  # includes an overlapping roll
    whole=kick_ducking(0,15000,rate,kicks,138)
    split=np.concatenate([kick_ducking(start,min(733,15000-start),rate,kicks,138)
                          for start in range(0,15000,733)])
    np.testing.assert_array_equal(whole,split)
    assert np.all(whole[:2500]==1) and whole.min()==pytest.approx(10**(-6/20))
    assert np.all(whole[12000:]==1)
    # A repeated kick cannot reset the existing ducking and introduce a click.
    assert whole[2650]==pytest.approx(whole[2649])
    assert np.max(np.abs(np.diff(whole)))<.055
    assert np.all(kick_ducking(0,500,rate,[],138)==1)
    with pytest.raises(ValueError): kick_ducking(0,100,rate,[10,5],138)


def test_stereo_linked_ducking_keeps_pan_and_never_increases_level():
    gain=kick_ducking(0,2000,10000,[0],120)
    signal=np.column_stack((np.full(2000,.2),np.full(2000,.1)))
    output=signal*gain[:,None]
    np.testing.assert_allclose(output[:,0]/output[:,1],2)
    assert np.max(output)<=np.max(signal)
