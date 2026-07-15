from speech.speech_to_text import SpeechToText

stt = SpeechToText()

text = stt.transcribe(
    "../recordings/current.wav"
)

print()
print("========== TRANSCRIPT ==========")
print(text)
print("================================")