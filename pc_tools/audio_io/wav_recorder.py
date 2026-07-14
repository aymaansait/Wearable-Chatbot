import wave
import numpy as np
from pathlib import Path
from datetime import datetime


class WavRecorder:

    def __init__(
        self,
        sample_rate=16000,
        target_level=10000.0,       # desired "normal speech" peak level, out of 32767
        attack_rate=0.5,           # how fast gain reacts DOWN to loud peaks (0-1, higher = faster)
        release_rate=0.02,         # how fast gain recovers UP for quiet audio (0-1, lower = slower/smoother)
        min_gain=0.5,
        max_gain=8.0,
    ):

        self.sample_rate = sample_rate

        self.target_level = target_level
        self.attack_rate = attack_rate
        self.release_rate = release_rate
        self.min_gain = min_gain
        self.max_gain = max_gain

        # Current gain multiplier, adjusted smoothly frame-by-frame.
        # Starts at 1.0 (no adjustment) and eases toward whatever
        # level keeps speech near target_level.
        self.current_gain = 1.0

        # Smoothed envelope of recent signal level (a running
        # estimate of "how loud is the audio right now", updated
        # slowly so it doesn't react to individual sample spikes).
        self.envelope = 0.0

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

        samples = samples.astype(np.float32)

        # -------------------------------------------------
        # 1. Update the slow envelope estimate for this frame.
        # -------------------------------------------------
        frame_peak = np.max(np.abs(samples)) if samples.size > 0 else 0.0

        if frame_peak > self.envelope:
            # Loud sound arrived: rise toward it quickly (attack),
            # so we don't clip before reacting.
            self.envelope += (frame_peak - self.envelope) * self.attack_rate
        else:
            # Sound got quieter: fall back down slowly (release),
            # so gain doesn't pump/jitter between words or pauses.
            self.envelope += (frame_peak - self.envelope) * self.release_rate

        # -------------------------------------------------
        # 2. Compute the gain that would bring the current
        #    envelope to the target level, and smoothly move
        #    current_gain toward it (rather than snapping).
        # -------------------------------------------------
        if self.envelope > 1.0:
            desired_gain = self.target_level / self.envelope
        else:
            desired_gain = self.max_gain

        desired_gain = float(np.clip(desired_gain, self.min_gain, self.max_gain))

        # Ease current_gain toward desired_gain smoothly, same
        # attack/release logic, so gain changes are gradual and
        # inaudible rather than jumpy.
        if desired_gain < self.current_gain:
            self.current_gain += (desired_gain - self.current_gain) * self.attack_rate
        else:
            self.current_gain += (desired_gain - self.current_gain) * self.release_rate

        # -------------------------------------------------
        # 3. Apply gain and write out.
        # -------------------------------------------------
        adjusted = samples * self.current_gain

        # Safety clip in case any peak still slips past target
        # (e.g. sudden very loud transient like a clap).
        adjusted = np.clip(adjusted, -32768, 32767)

        adjusted = adjusted.astype(np.int16)

        self.wavefile.writeframes(adjusted.tobytes())

    def close(self):

        self.wavefile.close()