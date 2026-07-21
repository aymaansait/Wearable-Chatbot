from collections import deque
import numpy as np
from openwakeword.model import Model


class WakeWordDetector:
    """
    Wraps openWakeWord with smoothing + cooldown for stable
    single-shot detection. process(samples) returns True exactly
    once per genuine wake-word event, False otherwise.
    """

    def __init__(
        self,
        model_name="alexa",       # swap to "wakeword/hey_quantum.onnx" later
        threshold=0.3,
        smoothing_window=5,
        cooldown_chunks=15,       # ~1.2s cooldown after a trigger
        chunk_size=1280,          # openWakeWord requires 80ms chunks at 16kHz
        min_abs_mean=80.0,        # Guard against silence / near-silent noise
    ):

        self.model = Model(wakeword_models=[model_name], inference_framework="onnx")
        self.model_name = model_name
        self.threshold = threshold
        self.chunk_size = chunk_size
        self.min_abs_mean = min_abs_mean

        self.recent_scores = deque(maxlen=smoothing_window)
        self.cooldown_chunks = cooldown_chunks
        self.cooldown = 0

        self._buffer = np.zeros(0, dtype=np.int16)

    def process(self, samples):

        detected = False

        self._buffer = np.concatenate([self._buffer, samples])

        while len(self._buffer) >= self.chunk_size:

            chunk = self._buffer[:self.chunk_size]
            self._buffer = self._buffer[self.chunk_size:]

            # Ignore silent or near-silent chunks before scoring. This is the
            # most important guard against the wake detector misfiring after
            # the follow-up timer ends and the mic is just picking up ambient
            # noise or the assistant's own playback.
            chunk_abs_mean = float(np.mean(np.abs(chunk)))
            if chunk_abs_mean < self.min_abs_mean:
                continue

            prediction = self.model.predict(chunk)
            score = prediction[self.model_name]

            self.recent_scores.append(score)
            avg_score = sum(self.recent_scores) / len(self.recent_scores)

            if self.cooldown > 0:
                self.cooldown -= 1
                continue

            if avg_score > self.threshold:
                detected = True
                self.cooldown = self.cooldown_chunks
                self.recent_scores.clear()

        return detected

    def reset(self):
        self.recent_scores.clear()
        self.cooldown = 0
        self._buffer = np.zeros(0, dtype=np.int16)