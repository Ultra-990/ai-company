# Instrument score and offline renderer

The additional music engine accepts a data-only score and renders its parts
through a real Surge XT VST3 instrument. A local model authors musical notes
and arrangement; the host validates and plays them. Technical validation does
not establish musical quality or grant permission to train on uploaded songs.

`app/instruments/score.py` defines `instrument-score.v1`: 4/4 meter, 60–180 BPM,
4–256 bars, 4–8 tracks, named presets, gain, balance, bounded note patterns and
nonoverlapping arrangement clips with transposition. Each note has a beat,
MIDI pitch, duration and velocity. Expansion orders note-offs before note-ons.
No executable code, arbitrary plugin paths or user-supplied native state is
accepted. The maximum arrangement is 898 seconds plus a two-second tail.

`scripts/render_instrument_score.py` runs only in the shared generation unit
with verified memory/swap limits. It produces stereo PCM24/96 kHz stems and
mix, a type-1 MIDI file, individual synth states and a render receipt. Disk
backed float buffers and four-second processing chunks bound working memory.
Common attenuation keeps the mix and each stem below -1 dBFS sample peak;
this is neither perceptual mastering nor a true-peak guarantee. The stems
retain the applied gain/balance so summing them reconstructs the mix.

Surge defers some patch initialization until processing. A silent warm-up
precedes beat zero, with processing state preserved across chunks. Without
this, the initial notes can disappear. The private host translates verified
FXP component state to the JUCE VST3 state wrapper; arbitrary FXP imports
are intentionally unsupported.

## Provisioning and provenance

`scripts/provision_instrument_runtime.py --install` downloads the pinned
official Linux x64 Surge XT 1.3.4 package, verifies its SHA-256, extracts it
without executing system package scripts, and creates a private Python venv.
Without `--install` it checks the existing runtime. The root and preset paths
are server-owned constants in `app/instruments/runtime.py`. Plugin and preset
hashes are checked before rendering. Dependencies: Pedalboard 0.9.26,
NumPy 2.2.6, Mido 1.3.3, Packaging 25.0.

- [Surge XT release](https://github.com/surge-synthesizer/releases-xt/releases/tag/1.3.4)
- [Surge source and license](https://github.com/surge-synthesizer/surge/tree/release_xt_1.3.4)
- [Pedalboard instrument API](https://spotify.github.io/pedalboard/reference/pedalboard.html)
- [Pedalboard source and license](https://github.com/spotify/pedalboard)

Surge XT and Pedalboard are GPL-3.0 projects. Preserve the upstream notices
in the private installation. The package contains Surge's copyright text at
`surge/usr/share/surge-xt/doc/copyright`; Python distributions retain their
own license metadata. This repository does not bundle their binaries,
presets, user audio or model weights. Preset names denote Surge sounds, not
official Yamaha, Roland or Korg instruments.

## Current limits

MIDI exports notes, tempo and instrument labels, not audio or licensed plugins.
The native WAV render is separate from any lower-precision editor preview.
Tempo-synchronized effects inside presets may use the host's default tempo
rather than the note tempo; transport synchronization needs further work.
The renderer does not yet provide automated EQ, sidechain, compression,
parameter automation, vocals or imported-audio remixing. A saved seed/score
does not guarantee bit-identical modulation in another synth rendering.

Independent tests cover unsafe data, requested tempo/length, overlap,
polyphony, event ordering, transposition and binary state encoding. Real local
pilots additionally checked short and seven-minute compositions, aligned
stems, native resolution and agreement between stems and mix. Human listening
remains required before accepting the music.
