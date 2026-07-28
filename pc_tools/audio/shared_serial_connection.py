import threading
import queue
import struct
import serial


class SharedSerialConnection:
    """
    Owns the single serial connection to the ESP32, which now runs
    both the microphone (I2S RX) and speaker (I2S TX) firmware at
    the same time over one COM port. A background thread reads all
    incoming bytes and demuxes them into two queues:

      - mic frames (binary, marked by FRAME_MAGIC)
      - text lines (PONG / DONE / ERROR..., newline-terminated)

    SerialAudioSource and SerialSpeakerPlayer both pull from this
    one connection instead of each opening their own port.
    """

    FRAME_MAGIC = 0xAA55F00D
    MIC_MARKER = struct.pack("<I", FRAME_MAGIC)
    MIC_PAYLOAD_BYTES = 640  # 320 samples * 2 bytes (int16)

    def __init__(self, port="COM11", baud=460800):

        self.port = port
        self.baud = baud

        print(f"Opening shared connection on {port}...")
        self.ser = serial.Serial(port, baud, timeout=0.05)
        self.ser.dtr = True
        print("Connected!")

        self._write_lock = threading.Lock()

        self._raw_buffer = bytearray()
        self._buffer_lock = threading.Lock()

        self.mic_frame_queue = queue.Queue()
        self.line_queue = queue.Queue()

        self._running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    # -------------------------------------------------
    # Writing (used by SerialSpeakerPlayer for PING / audio)
    # -------------------------------------------------
    def write(self, data):
        with self._write_lock:
            self.ser.write(data)

    def flush(self):
        with self._write_lock:
            self.ser.flush()

    # -------------------------------------------------
    # Background reader + demuxer
    # -------------------------------------------------
    def _reader_loop(self):
        while self._running:
            try:
                waiting = self.ser.in_waiting
                chunk = self.ser.read(waiting if waiting else 1)
            except serial.SerialException:
                break

            if chunk:
                with self._buffer_lock:
                    self._raw_buffer.extend(chunk)
                    self._demux()

    def _demux(self):
        """
        Must be called with _buffer_lock held. Repeatedly extracts
        whichever complete unit (mic frame or text line) appears
        earliest in the buffer, until no more complete units remain.
        """
        while True:
            marker_idx = self._raw_buffer.find(self.MIC_MARKER)
            newline_idx = self._raw_buffer.find(b"\n")

            if marker_idx == -1 and newline_idx == -1:
                # Avoid unbounded growth from stray bytes with no
                # recognizable markers at all.
                if len(self._raw_buffer) > 8192:
                    del self._raw_buffer[:-8]
                return

            if marker_idx != -1 and (newline_idx == -1 or marker_idx <= newline_idx):

                frame_start = marker_idx + len(self.MIC_MARKER)
                frame_end = frame_start + self.MIC_PAYLOAD_BYTES

                if len(self._raw_buffer) < frame_end:
                    # Not fully arrived yet; drop any garbage before
                    # the marker and wait for more bytes.
                    if marker_idx > 0:
                        del self._raw_buffer[:marker_idx]
                    return

                payload = bytes(self._raw_buffer[frame_start:frame_end])
                del self._raw_buffer[:frame_end]

                self.mic_frame_queue.put(payload)
                continue

            else:
                line = bytes(self._raw_buffer[:newline_idx])
                del self._raw_buffer[:newline_idx + 1]

                text = line.decode("utf-8", errors="ignore").strip()
                if text:
                    self.line_queue.put(text)
                continue

    # -------------------------------------------------
    # Consumer APIs
    # -------------------------------------------------
    def get_mic_frame(self):
        try:
            return self.mic_frame_queue.get_nowait()
        except queue.Empty:
            return None

    def get_line(self, timeout=1.0):
        try:
            return self.line_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        self._running = False
        self.ser.close()