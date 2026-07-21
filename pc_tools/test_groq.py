from ai.groq_chat import GroqChat

# This file mirrors the original Gemini test shape, but now exercises the
# Groq-based pipeline end-to-end with the same `ask_audio(...)` interface.
assistant = GroqChat()

reply = assistant.ask_audio(
    "../recordings/current.wav"
)

print()
print("=" * 60)
print(reply)
print("=" * 60)
