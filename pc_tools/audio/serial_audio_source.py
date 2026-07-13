import struct
import serial
import numpy as np


class SerialAudioSource:

    # Must match FRAME_MAGIC in the ESP32 firmware.
    FRAME_MAGIC = 0xAA55F00D
    MARKER = struct.pack("<I", FRAME_MAGIC)

    def __init__(
        self,
        port="COM12",
        baud=460800,
        sample_rate=16000,
        frame_duration_ms=20,
    ):

        self.port = port
        self.baud = baud

        self.frame_size = (
            sample_rate * frame_duration_ms // 1000
        )

        # Samples are now int16 (2 bytes each), not int32.
        self.frame_bytes = self.frame_size * 2

        self.serial = None

        self._recv_buffer = bytearray()
        self._awaiting_payload = False

    def connect(self):

        print(f"Opening {self.port}...")

        self.serial = serial.Serial(
            self.port,
            self.baud
        )

        print("Connected!")

    def _pull_available(self):

        waiting = self.serial.in_waiting

        if waiting:
            chunk = self.serial.read(waiting)
        else:
            chunk = self.serial.read(1)

        if chunk:
            self._recv_buffer.extend(chunk)

        return bool(chunk)

    def get_frame(self):

        if not self._awaiting_payload:

            if not self._pull_available():
                return None

            idx = self._recv_buffer.find(self.MARKER)

            if idx == -1:
                keep = len(self.MARKER) - 1
                if keep > 0:
                    self._recv_buffer = self._recv_buffer[-keep:]
                else:
                    self._recv_buffer.clear()
                return None

            del self._recv_buffer[:idx + len(self.MARKER)]
            self._awaiting_payload = True

        if len(self._recv_buffer) < self.frame_bytes:
            self._pull_available()

        if len(self._recv_buffer) < self.frame_bytes:
            return None

        payload = bytes(self._recv_buffer[:self.frame_bytes])
        del self._recv_buffer[:self.frame_bytes]

        self._awaiting_payload = False

        return np.frombuffer(
            payload,
            dtype=np.int16   # <-- samples now arrive as int16
        )