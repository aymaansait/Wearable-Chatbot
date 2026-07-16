import numpy as np
from silero_vad import load_silero_vad, VADIterator


class VoiceActivityDetector:
    """
    Silero neural VAD, wrapped to expose the same interface as the
    RMS-based version: process(frame) -> "speech_started" |
    "speech_ended" | None, plus a .state attribute.

    Internally buffers incoming 20ms (320-sample) frames into the
    512-sample windows Silero's streaming model expects, since
    scoring isolated 20ms frames (as we tried before) gives
    unreliable results.
    """

    WAITING = 0
    RECORDING = 1

    SILERO_WINDOW = 512  # required chunk size at 16kHz for Silero's streaming iterator

    def __init__(
        self,
        sample_rate=16000,
        threshold=0.5,               # speech probability cutoff, 0-1. Higher = stricter.
        min_silence_duration_ms=700, # how long silence must persist before "speech_ended"
        speech_pad_ms=100,           # padding kept around detected speech
    ):

        self.sample_rate = sample_rate
        self.state = self.WAITING

        model = load_silero_vad()

        self._iterator = VADIterator(
            model,
            sampling_rate=sample_rate,
            threshold=threshold,
            min_silence_duration_ms=min_silence_duration_ms,
            speech_pad_ms=speech_pad_ms,
        )

        # Rolling buffer for accumulating incoming frames into
        # Silero's required fixed window size.
        self._buffer = np.zeros(0, dtype=np.float32)

    def _to_float(self, samples):
        # Silero expects float32 audio normalized to [-1, 1].
        return samples.astype(np.float32) / 32768.0

    def process(self, samples):

        self._buffer = np.concatenate([self._buffer, self._to_float(samples)])

        event = None

        # Feed as many complete 512-sample windows as we have buffered.
        while len(self._buffer) >= self.SILERO_WINDOW:

            chunk = self._buffer[:self.SILERO_WINDOW]
            self._buffer = self._buffer[self.SILERO_WINDOW:]

            result = self._iterator(chunk, return_seconds=False)

            if result is None:
                continue

            if "start" in result and self.state == self.WAITING:
                self.state = self.RECORDING
                event = "speech_started"

            elif "end" in result and self.state == self.RECORDING:
                self.state = self.WAITING
                event = "speech_ended"

        return event

    def reset(self):
        self.state = self.WAITING
        self._buffer = np.zeros(0, dtype=np.float32)
        self._iterator.reset_states()