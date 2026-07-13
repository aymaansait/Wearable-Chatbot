import wave
import numpy as np
from pathlib import Path
from datetime import datetime


class WavRecorder:

    def __init__(self, sample_rate=16000):

        self.sample_rate = sample_rate

        recordings_dir = Path("../recordings")
        recordings_dir.mkdir(parents=True, exist_ok=True)

        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.wav")
        filepath = recordings_dir / filename

        print(f"Recording to: {filepath}")

        self.wavefile = wave.open(str(filepath), "wb")

        self.wavefile.setnchannels(1)
        self.wavefile.setsampwidth(2)      # 16-bit PCM
        self.wavefile.setframerate(sample_rate)

    def on_audio_frame(self, samples):

        # Samples arrive already scaled to int16 range by the
        # firmware now — no shifting needed here anymore, just
        # make sure the dtype is correct before writing.
        samples = samples.astype(np.int16)

        self.wavefile.writeframes(samples.tobytes())

    def close(self):

        self.wavefile.close()