"""Bounded CPU analysis of musical pulse and frame-aligned edit planning.

The pulse estimate is heuristic, not a semantic verse/chorus classifier or
an audio-conditioned choreography model. Unclear pulse uses uniform cuts.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import subprocess

import numpy as np

RATE = 16000
HOP = 160
WINDOW = 1024
FPS = 24


def analyze_samples(samples, rate=RATE):
    if rate != RATE:
        raise ValueError('timing_sample_rate_invalid')
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim != 1 or len(samples) > RATE * 121 or not np.isfinite(samples).all():
        raise ValueError('timing_audio_invalid')
    length = len(samples) / RATE
    if length < 1:
        raise ValueError('timing_audio_too_short')
    frames = np.lib.stride_tricks.sliding_window_view(samples, WINDOW)[::HOP]
    window = np.hanning(WINDOW).astype(np.float32)
    envelope = []
    previous = np.zeros(WINDOW // 2 + 1)
    # Batched FFT keeps two-minute input well below the panel memory budget.
    for start in range(0, len(frames), 128):
        spectra = np.log1p(np.abs(np.fft.rfft(frames[start:start+128] * window)) * 10)
        difference = np.diff(np.vstack((previous, spectra)), axis=0)
        envelope.extend(np.maximum(difference, 0).mean(axis=1))
        previous = spectra[-1]
    onset = np.asarray(envelope)
    baseline = np.convolve(onset, np.ones(31) / 31, mode='same')
    onset = np.maximum(onset - baseline, 0)
    scale = float(np.max(onset))
    rms = [float(np.sqrt(np.mean(samples[i:i+RATE] ** 2)))
           for i in range(0, len(samples), RATE)]
    result = {'method': 'spectral-flux-autocorrelation.v1', 'duration_seconds': length,
              'tempo_bpm': None, 'pulse_confidence': 0.0, 'pulse_usable': False,
              'beat_seconds': [], 'energy_per_second': rms,
              'limitations': 'Estimated pulse; half/double tempo ambiguity; no verse/chorus or dance-step recognition'}
    if scale < 1e-5 or len(onset) < 300 or max(rms) < 1e-4:
        return result
    onset /= scale
    lags = np.arange(33, 101)  # Candidate tempo approximately 60–180 BPM.
    def correlation_at(lag):
        if lag >= len(onset)-1:
            return 0.0
        return float(np.dot(onset[lag:], onset[:-lag])) / max(
            1e-12, float(np.linalg.norm(onset[lag:]) * np.linalg.norm(onset[:-lag])))
    correlation = np.array([correlation_at(lag) for lag in lags])
    # Accents may be stronger every third beat. Score several pulse periods,
    # not just the largest isolated autocorrelation peak.
    regularity = np.array([sum(correlation_at(lag*k)/k for k in (1,2,3,4)) for lag in lags])
    # Prefer plausible central tempi, while preserving the raw confidence.
    preference = np.exp(-0.5 * (np.log2((6000 / lags) / 120) / .8) ** 2)
    best = int(np.argmax(regularity * preference))
    period = int(lags[best]); confidence = float(correlation[best])
    if confidence < .25:
        result['pulse_confidence'] = round(confidence, 4)
        return result
    phase = max(range(period), key=lambda p: float(np.mean(onset[p::period])))
    beat_times = []
    radius = max(1, round(period * .12))
    for center in range(phase, len(onset), period):
        left = max(0, center-radius); right = min(len(onset), center+radius+1)
        peak = left + int(np.argmax(onset[left:right]))
        # Window centre compensates for the non-centred analysis window.
        time = (peak * HOP + WINDOW / 2) / RATE
        if time < length and (not beat_times or time-beat_times[-1] > .2):
            beat_times.append(round(time, 4))
    result.update(tempo_bpm=round(6000 / period, 2), pulse_confidence=round(confidence, 4),
                  pulse_usable=True, beat_seconds=beat_times)
    return result


def analyze_audio(path: Path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024**2:
        raise ValueError('timing_audio_invalid')
    result = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-threads', '1',
        '-protocol_whitelist', 'file,pipe', '-i', str(path), '-t', '121', '-vn',
        '-ac', '1', '-ar', str(RATE), '-threads', '1', '-f', 'f32le', 'pipe:1'],
        capture_output=True, timeout=30, check=True)
    if len(result.stdout) > RATE * 121 * 4:
        raise ValueError('timing_audio_too_long')
    report = analyze_samples(np.frombuffer(result.stdout, dtype='<f4'))
    report['source_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return report


def edit_timing(duration, analysis=None):
    if not math.isfinite(duration) or not 1 <= duration <= 120:
        raise ValueError('timing_duration_invalid')
    total_frames = round(duration * FPS)
    usable = bool(analysis and analysis.get('pulse_usable'))
    beats = sorted({round(t * FPS) for t in (analysis or {}).get('beat_seconds', [])
                    if isinstance(t, (int, float)) and math.isfinite(t) and 0 < t < duration})
    energy = (analysis or {}).get('energy_per_second', [])
    upper = float(np.quantile(energy, .65)) if energy else 0
    lower = float(np.quantile(energy, .3)) if energy else 0
    cuts = [0]; aligned = []
    while total_frames - cuts[-1] > 5 * FPS:
        start = cuts[-1]
        current_energy = float(energy[min(len(energy)-1, start // FPS)]) if energy else 0
        target_seconds = 3 if usable and current_energy >= upper and upper > lower else 4 if usable else 5
        candidates = [b for b in beats if start + 2*FPS <= b <= min(start+5*FPS, total_frames-FPS)] if usable else []
        end = min(candidates, key=lambda b: abs(b-start-target_seconds*FPS)) if candidates else min(start+5*FPS, total_frames-FPS)
        cuts.append(end); aligned.append(bool(candidates))
    cuts.append(total_frames)
    shots = []
    for index, (start, end) in enumerate(zip(cuts, cuts[1:])):
        e = float(energy[min(len(energy)-1, start // FPS)]) if energy else 0
        shots.append({'index': index, 'start_frame': start, 'end_frame': end,
            'start_seconds': start/FPS, 'duration_seconds': (end-start)/FPS,
            'energy': 'high' if e >= upper and upper > lower else 'low' if e <= lower and lower < upper else 'medium',
            'cut_on_estimated_beat': aligned[index] if index < len(aligned) else False})
    if len(shots) > 64:
        raise ValueError('timing_shot_budget_exceeded')
    return {'fps': FPS, 'duration_seconds': total_frames/FPS, 'shots': shots,
            'shot_count': len(shots), 'scene_count': math.ceil(len(shots)/3),
            'strategy': 'estimated_pulse_and_energy' if usable else 'uniform_fallback',
            'tempo_bpm': (analysis or {}).get('tempo_bpm'),
            'pulse_confidence': (analysis or {}).get('pulse_confidence', 0),
            'scene_grouping': 'up_to_three_shots_per_scene_not_semantic_song_sections'}
