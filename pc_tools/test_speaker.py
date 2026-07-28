import asyncio
import subprocess
import struct
import serial
import edge_tts
import time

PORT = "COM11"
BAUD = 460800

TEXT = "Good morning. This is your wearable assistant speaking."
VOICE = "en-US-AriaNeural"

MP3_FILE = "speaker_test.mp3"
PCM_FILE = "speaker_test.pcm"

AUDIO_MAGIC = 0xBEEFCAFE
PING_BYTE = b"\xF0"
PONG_BYTE = b"\xF1"


async def generate_tts():
    print("Generating speech...")
    communicate = edge_tts.Communicate(text=TEXT, voice=VOICE)
    await communicate.save(MP3_FILE)
    print("Speech generated.")


def convert_pcm():
    print("Converting using FFmpeg...")
    command = [
        "ffmpeg", "-y", "-i", MP3_FILE,"-af", "volume=6dB",
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ac", "1", "-ar", "16000",
        PCM_FILE,
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("Conversion complete.")


def wait_for_pong(ser, timeout=20):
    print("Handshaking with ESP32...")

    start = time.time()

    while time.time() - start < timeout:

        ser.write(PING_BYTE)
        ser.flush()

        time.sleep(0.1)

        if ser.in_waiting > 0:
            resp = ser.read(ser.in_waiting)
            if PONG_BYTE in resp:
                print("ESP32 responded. Ready.")
                return True

    return False


def send_pcm():

    with open(PCM_FILE, "rb") as f:
        pcm = f.read()

    print(f"PCM size: {len(pcm)} bytes")

    print(f"Opening {PORT}...")

    ser = serial.Serial(
        PORT,
        BAUD,
        timeout=1,
        write_timeout=5,
    )

    ser.dtr = True
    time.sleep(0.5)

    if not wait_for_pong(ser):
        print("ERROR: No response from ESP32.")
        ser.close()
        return

    ser.reset_input_buffer()

    print("Sending audio header...")

    header = struct.pack("<II", AUDIO_MAGIC, len(pcm))
    ser.write(header)
    ser.flush()
    time.sleep(0.05)

    CHUNK = 256   # small, paced writes — native USB CDC on this
    PACING_DELAY = 0.003   # board can't absorb a full-speed firehose

    print("Streaming PCM...")

    for i in range(0, len(pcm), CHUNK):
        chunk = pcm[i:i + CHUNK]
        ser.write(chunk)
        ser.flush()
        time.sleep(PACING_DELAY)

        if i % 16384 == 0:
            print(f"Sent {i} / {len(pcm)} bytes")

    print("All bytes sent. Waiting for playback...")

    start = time.time()
    HARD_TIMEOUT = 30   # generous — firmware now buffers fully before playing

    while time.time() - start < HARD_TIMEOUT:

        line = ser.readline()

        if not line:
            continue

        try:
            line = line.decode("utf-8", errors="ignore").strip()
        except Exception:
            continue

        if line:
            print("ESP32:", line)

        if line == "DONE":
            print("Playback complete.")
            break

        if line.startswith("ERROR"):
            print("Playback failed.")
            break

    else:
        print("Timed out waiting for DONE — check speaker/amp wiring or firmware state.")

    ser.close()

def main():
    asyncio.run(generate_tts())
    convert_pcm()
    send_pcm()
    print("\nFinished.")


if __name__ == "__main__":
    main()