from audio.ring_buffer import RingBuffer


class AudioEngine:

    def __init__(
        self,
        sample_rate=16000,
        buffer_duration=2,
    ):

        self.sample_rate = sample_rate
        self.buffer_duration = buffer_duration

        self.buffer = RingBuffer(
            sample_rate * buffer_duration
        )

        self.frames_received = 0

        self.listeners = []

    def register_listener(self, listener):

        self.listeners.append(listener)

    def add_frame(self, samples):

        self.buffer.append(samples)

        self.frames_received += 1

        for listener in self.listeners:

            listener(samples)

    def get_audio(self):

        return self.buffer.get()

    def get_frame_count(self):

        return self.frames_received