"""Data-only composition contract. No model-authored code or plugin paths."""
import math
import re

SCHEMA = 'instrument-score.v1'
PRESETS = {
    'kick-tech': ('kick', 'patches_factory/Percussion/Kick Tech 1.fxp'),
    'kick-909': ('kick', 'patches_factory/Percussion/Kick 909ish.fxp'),
    'snare-tight': ('snare', 'patches_factory/Percussion/Snare Tight.fxp'),
    'hat': ('hat', 'patches_3rdparty/Damon Armani/Drums/Hi-Hat.fxp'),
    'bass-deep': ('bass', 'patches_factory/Basses/Deep End.fxp'),
    'bass-square': ('bass', 'patches_factory/Basses/Square Bass.fxp'),
    'pluck-trance': ('arp', 'patches_factory/Plucks/Trancy.fxp'),
    'lead-light': ('lead', 'patches_factory/Leads/Light.fxp'),
    'lead-acid': ('lead', 'patches_factory/Leads/Sine-Saw Acidish.fxp'),
    'pad-warm': ('pad', 'patches_factory/Pads/Winter Warmer.fxp'),
}


def number(value, low, high, integer=False):
    if type(value) not in ((int,) if integer else (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('score_number_out_of_range')
    return value


def fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names.split()):
        raise ValueError('score_fields_invalid: ' + names)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch('[a-z][a-z0-9_-]{0,31}', value):
        raise ValueError('score_identifier_invalid')


def text(value, maximum):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum or any(ord(c) < 32 for c in value):
        raise ValueError('score_text_invalid')


def validate(score, *, bpm=None, bars=None):
    fields(score, 'schema title bpm bars tracks')
    if score['schema'] != SCHEMA: raise ValueError('score_schema_invalid')
    text(score['title'], 120)
    number(score['bpm'], 60, 180, True); number(score['bars'], 4, 256, True)
    if score['bars'] * 240 / score['bpm'] > 898: raise ValueError('score_too_long')
    if bpm is not None and score['bpm'] != bpm: raise ValueError('score_requested_bpm_mismatch')
    if bars is not None and score['bars'] != bars: raise ValueError('score_requested_bars_mismatch')
    if not isinstance(score['tracks'], list) or not 4 <= len(score['tracks']) <= 8: raise ValueError('score_tracks_invalid')
    seen = set(); total = 0
    for track in score['tracks']:
        fields(track, 'id name instrument gain_db pan patterns clips')
        identifier(track['id']); text(track['name'], 80)
        if track['id'] in seen or track['id'] == 'mix': raise ValueError('score_duplicate_track')
        seen.add(track['id'])
        if not isinstance(track['instrument'], str) or track['instrument'] not in PRESETS: raise ValueError('score_instrument_unknown')
        number(track['gain_db'], -30, 0); number(track['pan'], -1, 1)
        if not isinstance(track['patterns'], list) or not 1 <= len(track['patterns']) <= 8: raise ValueError('score_patterns_invalid')
        patterns = {}
        for pattern in track['patterns']:
            fields(pattern, 'id beats notes'); identifier(pattern['id'])
            if pattern['id'] in patterns: raise ValueError('score_duplicate_pattern')
            patterns[pattern['id']] = pattern
            number(pattern['beats'], 1, 16, True)
            if not isinstance(pattern['notes'], list) or not 1 <= len(pattern['notes']) <= 128: raise ValueError('score_notes_invalid')
            for note in pattern['notes']:
                if not isinstance(note, list) or len(note) != 4: raise ValueError('score_note_invalid')
                at, pitch, duration, velocity = note
                number(at, 0, pattern['beats']); number(pitch, 24, 108, True)
                number(duration, .03125, 16); number(velocity, 1, 127, True)
                if at + duration > pattern['beats'] + 1e-8: raise ValueError('score_note_crosses_pattern')
        if not isinstance(track['clips'], list) or not 1 <= len(track['clips']) <= 32: raise ValueError('score_clips_invalid')
        spans = []
        for clip in track['clips']:
            fields(clip, 'pattern at_bar bars transpose')
            if not isinstance(clip['pattern'], str) or clip['pattern'] not in patterns: raise ValueError('score_pattern_unknown')
            number(clip['at_bar'], 0, score['bars'] - 1, True)
            number(clip['bars'], 1, score['bars'], True); number(clip['transpose'], -24, 24, True)
            end = clip['at_bar'] + clip['bars']
            if end > score['bars'] or clip['bars'] * 4 % patterns[clip['pattern']]['beats']: raise ValueError('score_clip_length_invalid')
            if any(max(a, clip['at_bar']) < min(b, end) for a, b in spans): raise ValueError('score_clips_overlap')
            spans.append((clip['at_bar'], end))
        events = expand(track)
        total += len(events) // 2
        if total > 100000: raise ValueError('score_note_budget_exceeded')
        active = set()
        for _, on, pitch, _ in events:
            if not 0 <= pitch <= 127: raise ValueError('score_transposed_pitch_invalid')
            if on:
                if pitch in active: raise ValueError('score_same_pitch_overlap')
                active.add(pitch)
                if len(active) > 16: raise ValueError('score_polyphony_exceeded')
            else:
                if pitch not in active: raise ValueError('score_note_order_invalid')
                active.remove(pitch)
    return score


def expand(track):
    """Return absolute beat events; note-off precedes note-on at equal times."""
    patterns = {p['id']: p for p in track['patterns']}; events = []
    for clip in track['clips']:
        pattern = patterns[clip['pattern']]
        for offset in range(0, clip['bars'] * 4, pattern['beats']):
            for at, pitch, duration, velocity in pattern['notes']:
                start = clip['at_bar'] * 4 + offset + at; pitch += clip['transpose']
                events.extend([(round(start, 8), 1, pitch, velocity), (round(start + duration, 8), 0, pitch, 0)])
    return sorted(events)


def composer_instructions():
    return '''Compose an original instrumental song as JSON data only. Do not output code.
Return exactly schema,title,bpm,bars,tracks. schema="instrument-score.v1".
Use the requested integer bpm and bars, 4/4 meter. 4-8 tracks, each exactly:
id (unique lowercase slug), name, instrument, gain_db (-30..0), pan (-1..1), patterns, clips.
Each pattern: {"id":slug,"beats":integer 1..16,"notes":[[beat,midi_pitch,duration_beats,velocity],...]}
1-8 patterns/track, 1-128 notes/pattern. beat>=0, pitch integer24..108, velocity integer1..127,
duration>=0.03125, beat+duration<=pattern beats. No overlapping notes of the same pitch.
Each clip: {"pattern":pattern id,"at_bar":integer zero-based,"bars":integer,"transpose":integer -24..24}.
1-32 nonoverlapping clips/track; stay inside song bars. Repeat pattern to fill clip;
clip bars*4 must be divisible by pattern beats. Use varied patterns and distinct sections,
coherent harmony, intentional intro, build, contrasting breakdown and resolution/outro.
Preserve kick/bass headroom. Balance instrument gains. These are real melodic synthesizer
presets, not General MIDI drums. Drum presets can be triggered with note60, short durations.
Available instrument IDs and suggested roles: ''' + str({k: v[0] for k, v in PRESETS.items()})
