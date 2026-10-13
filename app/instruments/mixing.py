"""Bounded, reproducible offline mixing; never edits the composer's notes.

The trance profile is an experimental automatic balance, not mastering or
an assertion of musical quality. The transparent profile preserves faders.
"""
import math
import numpy as np

TRANSPARENT = 'transparent.v1'
TRANCE = 'trance-auto.v1'
PROFILES = (TRANSPARENT, TRANCE)
# Active 100 ms RMS targets, not integrated loudness/LUFS.
TARGETS = {'kick': -18., 'bass': -18., 'lead': -20., 'snare': -23.,
           'arp': -26., 'pad': -28., 'hat': -29.}
HIGH_PASS = {'kick': 24., 'bass': 24., 'lead': 100., 'snare': 80.,
             'arp': 130., 'pad': 140., 'hat': 180.}


def profile_for_style(style):
    return TRANCE if any(word in style.lower() for word in ('trance', 'techno')) else TRANSPARENT


class LevelMeter:
    """Window energies preserve alignment across arbitrary processing blocks."""
    def __init__(self, sample_rate):
        self.window = round(sample_rate * .1)
        if self.window < 1: raise ValueError('mix_sample_rate_invalid')
        self.energies = []
        self.pending = np.empty(0, dtype=np.float64)

    def add(self, audio):
        if audio.ndim != 2 or audio.shape[1] != 2 or not np.isfinite(audio).all():
            raise ValueError('mix_audio_invalid')
        energy = np.mean(np.square(audio, dtype=np.float64), axis=1)
        energy = np.concatenate((self.pending, energy))
        count = len(energy) // self.window * self.window
        if count:
            self.energies.extend(energy[:count].reshape(-1, self.window).mean(axis=1).tolist())
        self.pending = energy[count:].copy()

    def active_dbfs(self):
        # Do not let a partial final window count as a full window.
        values = np.sqrt(self.energies)
        if not len(values) or values.max() < 1e-4: return None
        active = values[values >= max(1e-4, values.max() * 10**(-30/20))]
        return 20 * math.log10(float(np.quantile(active, .75)))


def balance_plan(role, active_dbfs, profile):
    if profile not in PROFILES: raise ValueError('mix_profile_unknown')
    target = TARGETS.get(role) if profile == TRANCE else None
    if active_dbfs is not None and not math.isfinite(active_dbfs):
        raise ValueError('mix_level_invalid')
    correction = 0. if target is None or active_dbfs is None else float(np.clip(target-active_dbfs, -18, 12))
    return {'profile': profile, 'role': role, 'active_rms_dbfs_before_balance': active_dbfs,
            'target_active_rms_dbfs': target, 'balance_gain_db': correction,
            'highpass_hz': HIGH_PASS.get(role, 24.) if profile == TRANCE else None,
            'level_target_reached': None if target is None or active_dbfs is None else abs(active_dbfs+correction-target) < .01}


def kick_ducking(start, count, sample_rate, kick_samples, bpm):
    """Stereo-linked bass gain driven by actual kick onsets, not a free LFO.

    Absolute sample positions make results independent of render chunking.
    Smooth attack/release, at most 6 dB reduction, no makeup gain.
    """
    if count < 0 or start < 0 or sample_rate <= 0 or not 60 <= bpm <= 180:
        raise ValueError('mix_envelope_invalid')
    triggers = np.asarray(kick_samples, dtype=np.int64)
    if len(triggers) and (np.any(triggers < 0) or np.any(np.diff(triggers) <= 0)):
        raise ValueError('mix_kicks_invalid')
    if not len(triggers): return np.ones(count, dtype=np.float32)
    attack = .002; hold = .020; release = min(.220, .8 * 60/bpm)
    elapsed = np.arange(math.ceil((hold+release)*sample_rate)) / sample_rate
    envelope = np.ones(len(elapsed), dtype=np.float64)
    ramp = elapsed < attack
    envelope[ramp] = .5-.5*np.cos(np.pi*elapsed[ramp]/attack)
    tail = elapsed >= hold
    envelope[tail] = .5+.5*np.cos(np.pi*(elapsed[tail]-hold)/release)
    depth = np.zeros(count, dtype=np.float64)
    first = np.searchsorted(triggers, start-len(envelope), side='right')
    last = np.searchsorted(triggers, start+count, side='left')
    for at in triggers[first:last]:
        left = max(start, at); right = min(start+count, at+len(envelope))
        # Overlapping kicks must not reset the previous attenuation to unity.
        np.maximum(depth[left-start:right-start], envelope[left-at:right-at],
                   out=depth[left-start:right-start])
    return np.asarray(10**(-6*depth/20), dtype=np.float32)
