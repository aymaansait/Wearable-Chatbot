from audio.audio_engine import AudioEngine
from audio.serial_audio_source import SerialAudioSource

from visualization.oscilloscope import Oscilloscope
from audio_io.wav_recorder import WavRecorder

from ai.gemini_chat import GeminiChat


def main():

    # ------------------------------------
    # Audio
    # ------------------------------------
    audio = AudioEngine()

    scope = Oscilloscope()
    recorder = WavRecorder()

    audio.register_listener(scope.on_audio_frame)
    audio.register_listener(recorder.on_audio_frame)

    source = SerialAudioSource()

    source.connect()

    print()
    print("====================================")
    print("     Wearable AI Assistant")
    print("====================================")
    print("Speak...")
    print("Press Ctrl+C when finished.\n")

    try:

        while True:

            frame = source.get_frame()

            if frame is None:
                continue

            audio.add_frame(frame)

    except KeyboardInterrupt:

        print("\nProcessing...")

    finally:

        recorder.close()

    print()
    print("Thinking...\n")

    gemini = GeminiChat()

    reply = gemini.ask_audio("../recordings/current.wav")
    from tts.text_to_speech import TextToSpeech
    from audio_io.audio_player import AudioPlayer
    print("=" * 60)
    print(reply)
    tts = TextToSpeech()
    player = AudioPlayer()
    mp3 = tts.speak(reply)
    player.play(mp3)
    print("=" * 60)


if __name__ == "__main__":
    main()