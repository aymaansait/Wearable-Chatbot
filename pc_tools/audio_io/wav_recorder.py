import wave
import shutil
import numpy as np
from pathlib import Path
from datetime import datetime


class WavRecorder:

    def __init__(
        self,
        sample_rate=16000,
        target_level=10000.0,
        attack_rate=0.5,
        release_rate=0.02,
        min_gain=0.5,
        max_gain=8.0,
    ):

        self.sample_rate = sample_rate

        self.target_level = target_level
        self.attack_rate = attack_rate
        self.release_rate = release_rate
        self.min_gain = min_gain
        self.max_gain = max_gain

        self.current_gain = 1.0
        self.envelope = 0.0

        self.recordings_dir = Path("../recordings")
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.wav")

        self.filepath = self.recordings_dir / filename

        print(f"Recording to: {self.filepath}")

        self.wavefile = wave.open(str(self.filepath), "wb")

        self.wavefile.setnchannels(1)
        self.wavefile.setsampwidth(2)
        self.wavefile.setframerate(sample_rate)

    def on_audio_frame(self, samples):

        samples = samples.astype(np.float32)

        frame_peak = np.max(np.abs(samples)) if samples.size > 0 else 0.0

        if frame_peak > self.envelope:
            self.envelope += (
                frame_peak - self.envelope
            ) * self.attack_rate
        else:
            self.envelope += (
                frame_peak - self.envelope
            ) * self.release_rate

        if self.envelope > 1.0:
            desired_gain = self.target_level / self.envelope
        else:
            desired_gain = self.max_gain

        desired_gain = float(
            np.clip(
                desired_gain,
                self.min_gain,
                self.max_gain
            )
        )

        if desired_gain < self.current_gain:
            self.current_gain += (
                desired_gain - self.current_gain
            ) * self.attack_rate
        else:
            self.current_gain += (
                desired_gain - self.current_gain
            ) * self.release_rate

        adjusted = samples * self.current_gain

        adjusted = np.clip(
            adjusted,
            -32768,
            32767
        )

        adjusted = adjusted.astype(np.int16)

        self.wavefile.writeframes(
            adjusted.tobytes()
        )

    def close(self):

        self.wavefile.close()

        latest_file = self.recordings_dir / "current.wav"

        shutil.copy2(
            self.filepath,
            latest_file
        )

        print(f"Latest recording saved as: {latest_file}")