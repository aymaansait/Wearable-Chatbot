import numpy as np


class RingBuffer:
    def __init__(self, size):
        self.size = size
        self.buffer = np.zeros(size, dtype=np.int32)
        self.write_index = 0
        self.count = 0

    def append(self, data):
        data = np.asarray(data, dtype=np.int32)

        n = len(data)

        # If incoming data is larger than the buffer,
        # keep only the newest samples.
        if n >= self.size:
            self.buffer[:] = data[-self.size:]
            self.write_index = 0
            self.count = self.size
            return

        end = self.write_index + n

        if end <= self.size:
            self.buffer[self.write_index:end] = data
        else:
            first = self.size - self.write_index
            self.buffer[self.write_index:] = data[:first]
            self.buffer[:end % self.size] = data[first:]

        self.write_index = end % self.size
        self.count = min(self.count + n, self.size)

    def get(self):
        if self.count < self.size:
            return self.buffer[:self.count].copy()

        return np.concatenate((
            self.buffer[self.write_index:],
            self.buffer[:self.write_index]
        ))