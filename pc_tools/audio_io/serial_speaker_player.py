import struct
import subprocess
import time
import serial


class SerialSpeakerPlayer:
    """
    Plays audio through the ESP32 + MAX98357A speaker instead of
    the laptop's speakers. Same .play(filename) interface as
    AudioPlayer, so it can be swapped in without touching
    AudioPlayer or TextToSpeech.

    Takes an mp3 path, converts to 16kHz mono PCM via ffmpeg,
    handshakes with the ESP32, and streams it over serial.
    """

    AUDIO_MAGIC = 0xBEEFCAFE
    PING_BYTE = b"\xF0"
    PONG_BYTE = b"\xF1"

    def __init__(self, port="COM11", baud=460800, volume_db=6):

        self.port = port
        self.baud = baud
        self.volume_db = volume_db

        self.ser = serial.Serial(port, baud, timeout=1, write_timeout=5)
        self.ser.dtr = True
        time.sleep(0.5)

        if not self._wait_for_pong():
            raise RuntimeError(
                f"No response from ESP32 speaker on {port}. "
                "Check wiring/power and that no other program has the port open."
            )

    def _wait_for_pong(self, timeout=20):
        start = time.time()
        while time.time() - start < timeout:
            self.ser.write(self.PING_BYTE)
            self.ser.flush()
            time.sleep(0.1)
            if self.ser.in_waiting > 0:
                resp = self.ser.read(self.ser.in_waiting)
                if self.PONG_BYTE in resp:
                    return True
        return False

    def _mp3_to_pcm(self, mp3_path):

        pcm_path = str(mp3_path) + ".pcm"

        command = [
            "ffmpeg",
            "-y",
            "-i", str(mp3_path),
            "-af", f"volume={self.volume_db}dB",
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "16000",
            pcm_path,
        ]

        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        with open(pcm_path, "rb") as f:
            return f.read()

    def play(self, filename):
        """
        Same interface as AudioPlayer.play(filename) — takes an
        mp3 path, blocks until playback finishes.
        """

        pcm = self._mp3_to_pcm(filename)

        self.ser.reset_input_buffer()

        header = struct.pack("<II", self.AUDIO_MAGIC, len(pcm))
        self.ser.write(header)
        self.ser.flush()
        time.sleep(0.05)

        CHUNK = 256
        PACING_DELAY = 0.003

        for i in range(0, len(pcm), CHUNK):
            chunk = pcm[i:i + CHUNK]
            self.ser.write(chunk)
            self.ser.flush()
            time.sleep(PACING_DELAY)

        start = time.time()
        HARD_TIMEOUT = 30

        while time.time() - start < HARD_TIMEOUT:
            line = self.ser.readline()
            if not line:
                continue

            try:
                line = line.decode("utf-8", errors="ignore").strip()
            except Exception:
                continue

            if line == "DONE":
                return

            if line.startswith("ERROR"):
                raise RuntimeError(f"ESP32 playback error: {line}")

    def close(self):
        self.ser.close()