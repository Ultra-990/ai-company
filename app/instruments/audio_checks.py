"""Conservative source checks before gain can conceal synth overload.

Passing these checks says nothing about musical quality, melody or balance.
The ceiling deliberately rejects unusually hot presets instead of repairing
them by attenuation after an upstream artifact has already occurred.
"""
import numpy as np

RAW_PEAK_LIMIT = 4.0


def inspect_source(audio, *, sample_rate, frame_offset):
    if audio.ndim != 2 or audio.shape[1] != 2 or not len(audio) or sample_rate <= 0 or frame_offset < 0:
        raise ValueError('instrument_source_shape_invalid')
    finite = np.isfinite(audio).all(axis=1)
    overload = np.any(np.abs(audio) >= RAW_PEAK_LIMIT, axis=1)
    bad = np.flatnonzero(~finite | overload)
    return {'passed': not len(bad), 'finite': bool(finite.all()),
            'raw_peak': float(np.max(np.abs(audio[finite]))) if finite.any() else None,
            'overload_frames': int(overload.sum()), 'nonfinite_frames': int((~finite).sum()),
            'first_bad_seconds': float((frame_offset + bad[0])/sample_rate) if len(bad) else None,
            'raw_peak_limit': RAW_PEAK_LIMIT,
            'scope': 'source_integrity_only_not_musical_quality'}
