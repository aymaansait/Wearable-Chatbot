from audio.audio_engine import AudioEngine
from audio.serial_audio_source import SerialAudioSource

from visualization.oscilloscope import Oscilloscope
from audio_io.wav_recorder import WavRecorder


def main():

    # ==========================================
    # Create Audio Engine
    # ==========================================
    audio = AudioEngine()

    # ==========================================
    # Create Listeners
    # ==========================================
    scope = Oscilloscope()
    recorder = WavRecorder()

    # Register listeners
    audio.register_listener(scope.on_audio_frame)
    audio.register_listener(recorder.on_audio_frame)

    # ==========================================
    # Create Audio Source
    # ==========================================
    source = SerialAudioSource()

    source.connect()

    print()
    print("===================================")
    print(" Wearable Chatbot Audio Engine ")
    print("===================================")
    print("Press Ctrl+C to stop recording.\n")

    # ==========================================
    # Main Loop
    # ==========================================
    try:

        while True:

            frame = source.get_frame()

            # Check for None BEFORE touching frame.dtype/min/max,
            # otherwise a single bad/unsynced frame crashes the app.
            if frame is None:
                continue

            if audio.get_frame_count() % 50 == 0:
                print("dtype :", frame.dtype)
                print("Min   :", frame.min())
                print("Max   :", frame.max())
                print("First :", frame[:10])

            audio.add_frame(frame)

    except KeyboardInterrupt:

        print("\nStopping Audio Engine...")

    finally:

        recorder.close()

        print("Recording saved successfully.")


if __name__ == "__main__":
    main()