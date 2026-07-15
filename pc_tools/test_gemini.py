from ai.gemini_chat import GeminiChat

assistant = GeminiChat()

reply = assistant.ask_audio(
    "../recordings/current.wav"
)

print()
print("=" * 60)
print(reply)
print("=" * 60)