"""MOSS music-only soundtrack, retaining the approved gain and fades."""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import wave
import os
import imageio_ffmpeg
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "video"
SOURCE = Path(os.environ['MOSS_MUSIC'])  # Supply your own licensed music file.
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR, DURATION = 48000, 42
MUSIC_GAIN = 1.4 * .33
ROOT.mkdir(parents=True, exist_ok=True)

audio_bytes = subprocess.check_output([FFMPEG, '-v', 'error', '-i', str(SOURCE),
    '-t', str(DURATION), '-ar', str(SR), '-ac', '2', '-f', 'f32le', '-'])
raw = np.frombuffer(audio_bytes, dtype='<f4').reshape(-1, 2).astype(np.float64)
assert len(raw) >= SR*DURATION, len(raw)
music = raw[:SR*DURATION] * MUSIC_GAIN
events = []

envelope = np.ones(len(music))
fade_in = round(.5*SR)
envelope[:fade_in] = np.sin(np.linspace(0, np.pi/2, fade_in))**2
fade_out = round(40.5*SR)
envelope[fade_out:] = np.cos(np.linspace(0, np.pi/2, len(music)-fade_out))**2
music *= envelope[:,None]
mix = music
peak = float(np.max(np.abs(mix)))
assert peak < 10**(-1/20), f'Less than 1 dB of headroom: {peak}'
pcm = np.round(mix*32767).astype('<i2')
output = ROOT / 'AUDIO_MIX.wav'
with wave.open(str(output), 'wb') as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(SR)
    wav.writeframes(pcm.tobytes())

def stats(samples):
    return {'peak_dbfs': float(20*np.log10(max(np.max(np.abs(samples)),1e-15))),
            'rms_dbfs': float(20*np.log10(max(np.sqrt(np.mean(samples**2)),1e-15)))}

with wave.open(str(output), 'rb') as wav:
    assert wav.getnframes() == SR*DURATION
    assert wav.getframerate() == SR and wav.getnchannels() == 2
    decoded = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(float).reshape(-1,2)/32768
report = {'file': str(output), 'duration_seconds': DURATION, 'sample_rate': SR,
    'channels': 2, 'sample_format': 'PCM signed 16-bit',
    'music_source': str(SOURCE), 'source_interval_seconds': [0,42],
    'previous_music_gain': 1.4, 'requested_relative_music_gain': .33,
    'music_gain': MUSIC_GAIN, 'music_change_db': float(20*np.log10(.33)),
    'music': stats(music), 'effects': {'present': False}, 'mix_float': stats(mix),
    'mix_wav_readback': stats(decoded), 'clipped_samples': int(np.sum(np.abs(pcm.astype(np.int32))>=32767)),
    'first_sample': pcm[0].tolist(), 'last_sample': pcm[-1].tolist(),
    'fades_seconds': {'in': [0,.5], 'out': [40.5,42]},
    'effects_original_synthesis': False, 'speech_or_tts': False,
    'events': events, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
(ROOT/'AUDIO_QA.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['file','duration_seconds','music_gain','mix_wav_readback','clipped_samples']},indent=2))
