"""Pinned private Surge XT runtime; only curated, hash-checked presets."""
import hashlib
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
from app.instruments.score import PRESETS

ROOT = Path('/home/marcin/ai-company-workspaces/instrument-runtime')
DATA = ROOT / 'surge/usr/share/surge-xt'
PLUGIN = ROOT / 'surge/usr/lib/vst3/Surge XT.vst3'
PYTHON = ROOT / 'venv/bin/python'
VERSION = 'Surge XT 1.3.4 / Pedalboard 0.9.26'
SOURCE = 'https://github.com/surge-synthesizer/releases-xt/releases/tag/1.3.4'
DEB_SHA256 = 'a6e55064487f624147d515b9ae5fc79a568b69746675b2083abde628ca7bb151'
PLUGIN_SHA256 = 'b8584398f314819241ca7287117d5559ed838d37ef08faab9847f27ba2993cec'
HASHES = {
    'kick-tech': '1a78c5aed3b87a366c7b8bb67351ce99d569d1b20821533ee04a714ff1e4d3e6',
    'kick-909': '89f865c3513ea602aaed5e69ea45fdfd752dff4588a882cc92f09e871a2d8a24',
    'snare-tight': 'd9ea39e87318f50c4ad05aaca773dc469f944098b1f5fcdafa075dc99117e18a',
    'hat': '20eb72d2e826df991a745ccd4f519a3d8e5708a88c704a98a197cddaaf48bdaa',
    'bass-deep': '862f4f56a4a03411de77727cb5384fa0c8675ec35153d71b4e3cf2dc84b9b53f',
    'bass-square': 'c492a61dbb0eb5e47ccd8220ea07fe38c3fa8dfe8d4b15199df1744cd01506dc',
    'pluck-trance': 'cb671206f7933c11cb68c202560519fb7ba991014dd075d45537ea65ff1dfb55',
    'lead-light': '9bcd872dc8386f2530b0fb3c822e76e50b51373019744a2d0f92829d1b3e1c53',
    'lead-acid': 'dfeb1d5cf6e2e70c0321003be468e91fe95d2b4c889e0fe73428268ed3b668c6',
    'pad-warm': 'a96f81733a68eb89740fab72bf3cc56a4c4481a5cf59c1ac59a394e6f86606e2',
}


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024**2), b''): h.update(block)
    return h.hexdigest()


def preflight():
    if not PYTHON.is_file() or sha256(PLUGIN / 'Contents/x86_64-linux/Surge XT.so') != PLUGIN_SHA256:
        raise ValueError('instrument_runtime_changed')
    for key, (_, name) in PRESETS.items():
        if sha256(DATA / name) != HASHES[key]: raise ValueError('instrument_preset_changed')
    return {'engine': VERSION, 'plugin_sha256': PLUGIN_SHA256, 'source': SOURCE,
            'manufacturer': 'Surge Synth Team', 'license': 'GPL-3.0'}


def preset_state(identifier):
    """Convert pinned Surge FXP component bytes to JUCE's VST3 state wrapper.

    Never accept external FXP/state bytes: native plugins deserialize this data.
    JUCE uses little-endian bit packing and a non-RFC4648 base64 alphabet.
    """
    if identifier not in PRESETS: raise ValueError('instrument_preset_unknown')
    path = DATA / PRESETS[identifier][1]
    if sha256(path) != HASHES[identifier]: raise ValueError('instrument_preset_changed')
    fxp = path.read_bytes()
    if fxp[:4] != b'CcnK' or fxp[8:12] != b'FPCh' or fxp[60:64] != b'sub3' or struct.unpack('>I', fxp[56:60])[0] != len(fxp) - 60:
        raise ValueError('instrument_preset_format')
    raw = fxp[60:]; alphabet = '.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+'
    value = bits = 0; chars = []
    for byte in raw:
        value |= byte << bits; bits += 8
        while bits >= 6:
            chars.append(alphabet[value & 63]); value >>= 6; bits -= 6
    if bits: chars.append(alphabet[value & 63])
    root = ET.Element('VST3PluginState')
    ET.SubElement(root, 'IComponent').text = str(len(raw)) + '.' + ''.join(chars)
    xml = ET.tostring(root)
    return b'VC2!' + struct.pack('<I', len(xml)) + xml + b'\0'
