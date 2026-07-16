from openwakeword.model import Model
from audio.serial_audio_source import SerialAudioSource
import numpy as np
from collections import deque

source = SerialAudioSource(port="COM11")
source.connect()

MODEL_NAME = "alexa"
THRESHOLD = 0.75
SMOOTHING_WINDOW = 3        # average over last N chunks (~240ms)
COOLDOWN_CHUNKS = 15        # ~1.2s cooldown after a trigger, avoid double-fires

model = Model(wakeword_models=[MODEL_NAME], inference_framework="onnx")

recent_scores = deque(maxlen=SMOOTHING_WINDOW)
cooldown = 0

buffer = np.zeros(0, dtype=np.int16)
CHUNK = 1280  # openWakeWord wants 80ms chunks at 16kHz

print(f"Say '{MODEL_NAME}'...\n")

while True:
    frame = source.get_frame()
    if frame is None:
        continue

    buffer = np.concatenate([buffer, frame])

    while len(buffer) >= CHUNK:
        chunk = buffer[:CHUNK]
        buffer = buffer[CHUNK:]

        prediction = model.predict(chunk)
        score = prediction[MODEL_NAME]

        recent_scores.append(score)
        avg_score = sum(recent_scores) / len(recent_scores)

        if cooldown > 0:
            cooldown -= 1
            continue

        if avg_score > THRESHOLD:
            print(f"Wake word detected! (avg score {avg_score:.2f})")
            cooldown = COOLDOWN_CHUNKS
            recent_scores.clear()