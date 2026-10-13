"""Use Demucs unchanged for inference, with a bounded standard-library WAV writer.

The installed TorchCodec ABI cannot encode with the installed PyTorch. This
adapter replaces only WAV serialization, keeping Demucs' clamp policy and PCM16.
"""
from pathlib import Path
import wave
import numpy as np


def save_wav(samples,path,samplerate,clip='clamp',bits_per_sample=16,as_float=False,**kwargs):
    if Path(path).suffix!='.wav' or clip!='clamp' or bits_per_sample!=16 or as_float:
        raise ValueError('unsupported_demucs_audio_export')
    channels,length=samples.shape
    if not 1<=channels<=2:raise ValueError('invalid_channel_count')
    with Path(path).open('xb') as handle, wave.open(handle,'wb') as output:
        output.setnchannels(channels);output.setsampwidth(2);output.setframerate(samplerate)
        for start in range(0,length,65536):
            block=samples[:,start:start+65536].detach().cpu().numpy().T
            if not np.isfinite(block).all():raise ValueError('invalid_audio_samples')
            output.writeframes((np.clip(block,-.99,.99)*32768).round().astype('<i2').tobytes())


if __name__=='__main__':
    import demucs.separate
    demucs.separate.save_audio=save_wav
    demucs.separate.main()
