import time
import threading

from audio.audio_engine import AudioEngine
from audio.serial_audio_source import SerialAudioSource

from visualization.oscilloscope import Oscilloscope
from audio_io.wav_recorder import WavRecorder
from audio_io.audio_player import AudioPlayer
from audio_io.tone_generator import generate_shutdown_tone

from ai.gemini_chat import GeminiChat
from tts.text_to_speech import TextToSpeech

from vad.voice_activity_detector import VoiceActivityDetector
from wakeword.wake_word_detector import WakeWordDetector


# ------------------------------------
# States
# ------------------------------------
SLEEPING = "SLEEPING"
LISTENING = "LISTENING"
PROCESSING = "PROCESSING"
FOLLOWUP = "FOLLOWUP"

FOLLOWUP_WINDOW_SECONDS = 6


def main():

    # ------------------------------------
    # Create Core Components
    # ------------------------------------
    audio = AudioEngine()

    scope = Oscilloscope()
    recorder = WavRecorder()
    vad = VoiceActivityDetector()
    wake_detector = WakeWordDetector(model_name="alexa")  # swap later to "wakeword/hey_quantum.onnx"

    gemini = GeminiChat()
    tts = TextToSpeech()
    player = AudioPlayer()

    shutdown_tone_path = generate_shutdown_tone()

    state = {"current": SLEEPING, "followup_deadline": None}

    # ------------------------------------
    # Background handlers
    # ------------------------------------
    def say(text):
        mp3 = tts.speak(text)
        player.play(mp3)

    def wake_acknowledged():
        # Say "Yes" in the background while we're already listening,
        # so we don't lose the start of the user's next sentence.
        # Known limitation: the mic may briefly pick up "Yes" itself
        # during playback, same caveat as assistant-hears-itself
        # during full replies.
        threading.Thread(target=lambda: say("Yes"), daemon=True).start()

    def process_and_open_followup(wav_path):

        if wav_path is None:
            state["current"] = SLEEPING
            print("\n😴 Sleeping. Say the wake word to start.\n")
            return

        print("\n🤖 Thinking...\n")

        reply = gemini.ask_audio(str(wav_path))

        print("=" * 60)
        print(reply)
        print("=" * 60)

        mp3 = tts.speak(reply)
        player.play(mp3)

        vad.reset()
        state["followup_deadline"] = time.time() + FOLLOWUP_WINDOW_SECONDS
        state["current"] = FOLLOWUP
        print(f"\n👂 Listening for follow-up ({FOLLOWUP_WINDOW_SECONDS}s)...\n")

    def go_to_sleep():
        player.play(shutdown_tone_path)
        wake_detector.reset()
        state["current"] = SLEEPING
        print("\n😴 Sleeping. Say the wake word to start.\n")

    # ------------------------------------
    # Frame routing based on current state
    # ------------------------------------
    def on_frame(samples):

        current = state["current"]

        if current == SLEEPING:

            if wake_detector.process(samples):
                print("\n✨ Wake word detected!")
                vad.reset()
                state["current"] = LISTENING
                wake_acknowledged()

        elif current == LISTENING:

            event = vad.process(samples)

            if event == "speech_started":
                recorder.start_recording()
                print("🎙️  Recording...")

            elif event == "speech_ended":
                wav_path = recorder.stop_recording()
                state["current"] = PROCESSING
                threading.Thread(
                    target=process_and_open_followup,
                    args=(wav_path,),
                    daemon=True,
                ).start()

        elif current == FOLLOWUP:

            if time.time() > state["followup_deadline"]:
                go_to_sleep()
                return

            event = vad.process(samples)

            if event == "speech_started":
                recorder.start_recording()
                state["current"] = LISTENING
                print("🎙️  Recording follow-up...")

        # PROCESSING: ignore incoming frames while Gemini/TTS/playback
        # are running in the background, to avoid picking up the
        # assistant's own reply as new input.

    # ------------------------------------
    # Register Listeners
    # ------------------------------------
    audio.register_listener(scope.on_audio_frame)
    audio.register_listener(recorder.on_audio_frame)
    audio.register_listener(on_frame)

    # ------------------------------------
    # Audio Source
    # ------------------------------------
    source = SerialAudioSource()
    source.connect()

    print()
    print("====================================")
    print("     Wearable AI Assistant")
    print("====================================")
    print("😴 Sleeping. Say the wake word to start.")
    print("Press Ctrl+C to exit.\n")

    # ------------------------------------
    # Main Loop
    # ------------------------------------
    try:

        while True:

            frame = source.get_frame()

            if frame is None:
                continue

            audio.add_frame(frame)

    except KeyboardInterrupt:

        print("\nShutting down...")


if __name__ == "__main__":
    main()