import wave
import numpy as np
from pathlib import Path


def generate_shutdown_tone(path="assets/shutdown_tone.wav", sample_rate=16000):

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        return str(path)

    notes = [600, 450, 300]   # descending tones, Hz
    note_duration = 0.15      # seconds each
    fade_samples = 200

    audio = np.array([], dtype=np.float32)

    for freq in notes:
        t = np.linspace(0, note_duration, int(sample_rate * note_duration), endpoint=False)
        tone = 0.3 * np.sin(2 * np.pi * freq * t)

        # simple fade in/out to avoid clicks
        tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
        tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)

        audio = np.concatenate([audio, tone])

    pcm = (audio * 32767).astype(np.int16)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())

    return str(path)