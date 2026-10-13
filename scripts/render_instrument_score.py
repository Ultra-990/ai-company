"""Private, bounded VST3 worker. Render data-only scores, never model code."""
import json
import math
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.instruments import runtime
from app.instruments.score import validate, expand, PRESETS
from scripts.generation_limits import verify_limits, cgroup_path, UNIT


def render(score_path, output, mix_profile='transparent.v1'):
    if cgroup_path().name != UNIT: raise ValueError('instrument_unbounded_renderer')
    limits = verify_limits(); receipt = runtime.preflight()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'): os.environ.pop(key, None)
    os.environ['SURGE_DATA_HOME'] = str(runtime.DATA)
    import numpy as np
    import pedalboard
    from app.instruments.audio_checks import inspect_source
    from app.instruments.mixing import PROFILES, TRANCE, HIGH_PASS, LevelMeter, balance_plan, kick_ducking
    from pedalboard.io import AudioFile
    import mido
    if pedalboard.__version__ != '0.9.26': raise ValueError('instrument_host_version_changed')
    if mix_profile not in PROFILES: raise ValueError('mix_profile_unknown')
    score = validate(json.loads(score_path.read_text()))
    output.mkdir(mode=0o700, exist_ok=False)
    rate = 96000; beat = 60 / score['bpm']; duration = score['bars'] * 4 * beat + 2
    frames = round(duration * rate); chunk = rate * 4
    mix = np.memmap(output / 'mix.f32', dtype='float32', mode='w+', shape=(frames, 2)); mix[:] = 0
    midi = mido.MidiFile(ticks_per_beat=960)
    tempo = mido.MidiTrack(); midi.tracks.append(tempo)
    tempo.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(score['bpm'])))
    tempo.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))
    tempo.append(mido.MetaMessage('end_of_track', time=score['bars'] * 4 * 960))
    tracks = []; maximum = 0.
    kicks = sorted({round(at * beat * rate) for t in score['tracks'] if PRESETS[t['instrument']][0] == 'kick'
                    for at, on, _, _ in expand(t) if on})
    for track in score['tracks']:
        events = expand(track); channel = len(tracks)
        mt = mido.MidiTrack(); midi.tracks.append(mt)
        mt.append(mido.MetaMessage('track_name', name=track['name']))
        mt.append(mido.MetaMessage('text', text='Surge XT preset: ' + track['instrument']))
        last = 0
        for at, on, pitch, velocity in events:
            tick = round(at * 960)
            mt.append(mido.Message('note_on' if on else 'note_off', channel=channel, note=pitch, velocity=velocity, time=tick-last)); last = tick
        mt.append(mido.MetaMessage('end_of_track', time=score['bars'] * 4 * 960-last))
        plugin = pedalboard.load_plugin(str(runtime.PLUGIN))
        if not plugin.is_instrument or plugin.name != 'Surge XT': raise ValueError('instrument_plugin_mismatch')
        plugin.raw_state = runtime.preset_state(track['instrument'])
        # Surge applies deferred patch initialization on its first audio block.
        # Warm up with silence BEFORE beat zero; otherwise the first notes vanish.
        plugin([], duration=.1, sample_rate=rate, num_channels=2, buffer_size=512)
        (output / (track['id'] + '.vst3state')).write_bytes(plugin.raw_state)
        data = np.memmap(output / (track['id'] + '.f32'), dtype='float32', mode='w+', shape=(frames, 2))
        gain = 10 ** (track['gain_db'] / 20)
        pan = track['pan']; balance = np.array([min(1, 1-pan), min(1, 1+pan)], dtype=np.float32)
        sample_events = [(round(at * beat * rate), bytes([144 if on else 128, pitch, velocity])) for at, on, pitch, velocity in events]
        role = PRESETS[track['instrument']][0]
        highpass = pedalboard.HighpassFilter(HIGH_PASS.get(role, 24.)) if mix_profile == TRANCE else None
        meter = LevelMeter(rate)
        cursor = 0; source_peak = 0.
        for start in range(0, frames, chunk):
            end = min(start + chunk, frames); messages = []
            while cursor < len(sample_events) and sample_events[cursor][0] < end:
                sample, message = sample_events[cursor]; cursor += 1
                messages.append((message, (sample-start)/rate))
            block = plugin(messages, duration=(end-start)/rate, sample_rate=rate, num_channels=2, buffer_size=512, reset=False).T.copy()
            if block.shape != (end-start, 2): raise ValueError('instrument_audio_invalid')
            check = inspect_source(block, sample_rate=rate, frame_offset=start)
            if not check['passed']:
                (output / 'source-failure.json').write_text(json.dumps({
                    'track':track['id'], 'instrument':track['instrument'], **check}, indent=2))
                raise ValueError('instrument_source_overload: ' + track['id'])
            source_peak = max(source_peak, check['raw_peak'])
            if highpass is not None:
                block = highpass(block.T, sample_rate=rate, reset=False).T.copy()
            block *= gain * balance
            positions = np.arange(start, end)
            envelope = np.minimum(1., (frames-1-positions)/(rate*.02)).clip(0, 1)
            block *= envelope[:, None]
            meter.add(block)
            data[start:end] = block
        plan = balance_plan(role, meter.active_dbfs(), mix_profile)
        correction = 10 ** (plan['balance_gain_db']/20)
        peak = squares = 0.
        minimum_ducking = 1.
        for start in range(0, frames, chunk):
            end = min(start+chunk, frames)
            block = np.asarray(data[start:end]).copy() * correction
            if mix_profile == TRANCE and role == 'bass':
                ducking = kick_ducking(start, end-start, rate, kicks, score['bpm'])
                minimum_ducking = min(minimum_ducking, float(ducking.min()))
                block *= ducking[:, None]
            if not np.isfinite(block).all(): raise ValueError('instrument_mix_nonfinite')
            peak = max(peak, float(np.max(np.abs(block)))); squares += float(np.sum(block.astype('float64')**2))
            data[start:end] = block; mix[start:end] += block
        data.flush(); del data, plugin, highpass
        if peak < 1e-5: raise ValueError('instrument_silent_track: ' + track['id'])
        maximum = max(maximum, peak)
        tracks.append({'id': track['id'], 'name': track['name'], 'instrument': track['instrument'],
                       'preset_sha256': runtime.HASHES[track['instrument']], 'peak_before_master': peak,
                       'rms_before_master': math.sqrt(squares/(frames*2)), 'notes': len(events)//2,
                       'source_peak_before_gain': source_peak, 'mixing': plan | {
                           'max_sidechain_reduction_db': -20*math.log10(minimum_ducking)}})
    mix.flush()
    mix_peak = max(float(np.max(np.abs(mix[start:start+chunk]))) for start in range(0, frames, chunk))
    if mix_peak < 1e-5: raise ValueError('instrument_silent_mix')
    # Common attenuation keeps both mix and stems below -1 dBFS without clipping
    # and lets the editor reconstruct the mix by summing stems at unity gain.
    scale = min(1., 10**(-1/20) / max(maximum, mix_peak))
    del mix
    for name in [t['id'] for t in tracks] + ['mix']:
        data = np.memmap(output / (name + '.f32'), dtype='float32', mode='r', shape=(frames, 2))
        with AudioFile(str(output / (name + '.wav')), 'w', samplerate=rate, num_channels=2, bit_depth=24) as target:
            for start in range(0, frames, chunk): target.write((data[start:start+chunk] * scale).T)
        del data
        (output / (name + '.f32')).unlink()
    midi.save(output / 'score.mid')
    for track in tracks:
        track.update(file=track['id']+'.wav', sha256=runtime.sha256(output/(track['id']+'.wav')))
    report = {'engine': receipt, 'limits': limits, 'sample_rate': rate, 'bits': 24, 'duration_seconds': frames/rate,
              'mix_profile': mix_profile, 'score_sha256': runtime.sha256(score_path),
              'tracks': tracks, 'master_gain_db': 20*math.log10(scale), 'mix_sample_peak': mix_peak*scale,
              'mix_sha256': runtime.sha256(output/'mix.wav'), 'quality_accepted': False,
              'limitations': ['Odsłuch i ocena muzyczna są wymagane.',
                             'Automatyczny balans trance jest eksperymentalny; pomiar RMS nie ocenia melodii ani brzmienia.',
                             'Efekty zsynchronizowane wewnątrz presetów używają tempa hosta, które może różnić się od tempa nut.']}
    (output / 'render.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--mix-profile', choices=('transparent.v1', 'trance-auto.v1'), default='transparent.v1')
    args = parser.parse_args()
    render(args.score, args.output, args.mix_profile)
