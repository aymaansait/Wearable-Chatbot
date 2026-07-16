import numpy as np
from audio.serial_audio_source import SerialAudioSource
from vad.voice_activity_detector import VoiceActivityDetector

source = SerialAudioSource(port="COM11")
source.connect()

vad = VoiceActivityDetector()

print("Silero VAD test. Stay silent, then speak normally, then cough/blow near mic to test rejection.\n")

while True:

    frame = source.get_frame()

    if frame is None:
        continue

    event = vad.process(frame)

    state_label = "RECORDING" if vad.state == VoiceActivityDetector.RECORDING else "waiting"

    if event == "speech_started":
        print(f"[{state_label}] >>> SPEECH STARTED")

    elif event == "speech_ended":
        print(f"[{state_label}] >>> SPEECH ENDED")