import time
import threading

import numpy as np

from audio.audio_engine import AudioEngine
from audio.serial_audio_source import SerialAudioSource

from visualization.oscilloscope import Oscilloscope
from audio_io.wav_recorder import WavRecorder

#from audio_io.audio_player import AudioPlayer
from audio_io.serial_speaker_player import SerialSpeakerPlayer

from audio_io.tone_generator import generate_shutdown_tone

# Keep the wearable architecture unchanged, but swap the backend class so
# the call site still uses the same ask_audio(...) interface.
from ai.groq_chat import GroqChat
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
WAKEWORD_MIN_ABS_MEAN = 80.0


def main():

    # ------------------------------------
    # Create Core Components
    # ------------------------------------
    audio = AudioEngine()

    scope = Oscilloscope()
    recorder = WavRecorder()
    vad = VoiceActivityDetector()
    # Keep the same wake-word architecture, but make the detector less eager
    # after a follow-up window so it does not self-trigger on ambient noise
    # or the assistant's own post-response audio.
    wake_detector = WakeWordDetector(
        model_name="alexa",
        threshold=0.75,
        smoothing_window=3,
        cooldown_chunks=30,
    )  # swap later to "wakeword/hey_quantum.onnx"

    groq = GroqChat()
    tts = TextToSpeech()
    
    #player = AudioPlayer()
    player = SerialSpeakerPlayer(port="COM11")

    shutdown_tone_path = generate_shutdown_tone()

    # Keep the existing state structure, but add one more timeout so that
    # if the wake word is heard and no speech follows within 6 seconds,
    # the device automatically returns to sleep instead of staying armed.
    state = {
        "current": SLEEPING,
        "followup_deadline": None,
        "wake_wait_deadline": None,
    }

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
        # Reset the wake-word detector immediately after a real trigger so
        # the assistant's own acknowledgement audio does not immediately
        # feed back into the detector as a second wake event.
        wake_detector.reset()
        threading.Thread(target=lambda: say("Yes"), daemon=True).start()

    def process_and_open_followup(wav_path):

        if wav_path is None:
            state["current"] = SLEEPING
            print("\n😴 Sleeping. Say the wake word to start.\n")
            return

        print("\n🤖 Thinking...\n")

        # Clear detector state once the reply is being processed so the
        # assistant's own playback and subsequent ambient silence do not
        # re-trigger the wake-word model in the same conversation window.
        wake_detector.reset()

        reply = groq.ask_audio(str(wav_path))

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
        # Clear the detector before playing the shutdown tone so the
        # assistant's own audio does not get fed back into the wake-word
        # model while the state is still in the sleeping branch. Keep a
        # short post-sleep cooldown so the detector cannot instantly retrigger
        # from the same silence/playback boundary after follow-up ends.
        wake_detector.reset()
        wake_detector.cooldown = 30
        state["current"] = PROCESSING
        player.play(shutdown_tone_path)
        state["current"] = SLEEPING
        state["wake_wait_deadline"] = None
        print("\n😴 Sleeping. Say the wake word to start.\n")

    # ------------------------------------
    # Frame routing based on current state
    # ------------------------------------
    def on_frame(samples):

        current = state["current"]

        if current == SLEEPING:

            # Ignore near-silent frames before feeding them into the wake-word
            # model. This prevents false detections from residual mic noise or
            # silence after the assistant has already responded.
            if np.mean(np.abs(samples)) < WAKEWORD_MIN_ABS_MEAN:
                return

            if wake_detector.process(samples):
                print("\n✨ Wake word detected!")
                vad.reset()
                state["current"] = LISTENING
                # Start a 6-second window after wake-word detection. If no
                # actual speech starts in that time, the device should return
                # to sleep automatically instead of staying armed.
                state["wake_wait_deadline"] = time.time() + FOLLOWUP_WINDOW_SECONDS
                wake_acknowledged()

        elif current == LISTENING:

            # If the wake word was heard but no user speech follows within the
            # 6-second wait window, drop back to sleep automatically.
            if state["wake_wait_deadline"] is not None and time.time() > state["wake_wait_deadline"]:
                go_to_sleep()
                return

            event = vad.process(samples)

            if event == "speech_started":
                state["wake_wait_deadline"] = None
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

        # PROCESSING: ignore incoming frames while Groq/TTS/playback
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