import numpy as np
import sounddevice as sd

pcm = np.fromfile("speaker_test.pcm", dtype=np.int16)

sd.play(pcm, 16000)
sd.wait()