from pathlib import Path
import os
import re

from dotenv import load_dotenv
from groq import Groq

# Keep the existing .env loading pattern so the new client reads the same
# environment configuration the rest of the project already uses.
load_dotenv()

# Do not fail at import time: the wearable app should still import this class
# cleanly, and only attempt the Groq API call when ask_audio(...) is invoked.
# This preserves the existing architecture while still reading the key from
# the project's existing .env file.


class GroqChat:

    def __init__(self):
        # Use a fast, production-friendly chat model for the text reply step.
        self.chat_model = "llama-3.3-70b-versatile"

        # Use Groq's supported speech-to-text endpoint for WAV transcription.
        self.stt_model = "whisper-large-v3-turbo"

        # Keep a small in-memory conversation history so follow-up questions
        # can refer back to the previous user/assistant turns in the same run.
        self.conversation_memory = []

        # Add the current project facts to the system prompt so the assistant
        # can answer questions about the wearable AI assistant built by the
        # QuantumCLK Technologies interns team.
        self.project_context = """
You are the wearable AI assistant for the project built by an Intern at QuantumCLK Technologies and the wakeword used to activate you is "Alexa".
Key project facts:
- The assistant is a wearable AI assistant running on a Python PC toolchain.
- The audio pipeline is: ESP32 microphone -> recorded WAV -> speech-to-text -> Groq chat completion -> Edge TTS -> speaker.
- The main wearable entrypoint is pc_tools/wearable.py.
- The Groq backend is implemented in pc_tools/ai/groq_chat.py.
- The original Gemini backend is preserved in pc_tools/ai/gemini_chat.py for fallback.
- The project team members are Aymaan Sait, under the mentorship of Mr. Pramod.
- The assistant must answer questions about the project, its architecture, its team, and current implementation details.
- Keep answers concise, natural, and directly useful.
"""

    def _get_client(self) -> Groq:
        """
        Build the official Groq SDK client only when the assistant is actually
        asked to process audio. This keeps the class import-safe while still
        honoring the GROQ_API_KEY environment variable from the existing .env.
        """

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to the existing .env file.")

        return Groq(api_key=api_key)

    def _clean_response(self, text: str) -> str:
        """
        Remove timestamps like:
        00:00:15
        0:01:23
        """

        # Keep the same cleanup behavior as the original Gemini class so the
        # wearable flow does not need any downstream changes.
        text = re.sub(r"\b\d{1,2}:\d{2}:\d{2}\b", "", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _build_messages(self, user_text: str):
        """
        Build the chat request using the project context plus lightweight
        conversation memory, without changing the public call interface.
        """

        system_message = {
            "role": "system",
            "content": self.project_context + """
You are an intelligent wearable AI assistant.

Listen to the user's speech.
Understand what they asked.
Reply naturally and conversationally.

IMPORTANT RULES:
- Return ONLY your final answer.
- NEVER return a transcript.
- NEVER include timestamps.
- NEVER include subtitles.
- NEVER include speaker labels.
- NEVER describe the audio.
- NEVER explain what you heard.
- NEVER output markdown.
- If the user says something short or ambiguous like "uhuh", "hmm", "okay", "nothing", or a very brief acknowledgment, reply naturally and briefly as a conversational assistant, not as a transcript or a generic system message.
- If the user has not asked a clear question, respond in a helpful, natural way such as: "I'm here. What can I help with?"
- Keep replies compact, warm, and human-sounding.

Your response should be exactly what you would speak back to the user.
""",
        }

        # Keep only the recent memory to avoid growing the prompt forever.
        memory = self.conversation_memory[-8:]
        return [system_message, *memory, {"role": "user", "content": user_text}]

    def _transcribe_audio(self, wav_path: Path) -> str:
        """
        Convert the recorded WAV file into text using Groq's official audio
        transcription endpoint. This is the most reliable path when a model
        does not natively support direct audio input in the same way Gemini did.
        """

        with open(wav_path, "rb") as wav_file:
            audio_bytes = wav_file.read()

        # Groq's official SDK exposes speech-to-text via audio.transcriptions.
        # We keep the file upload simple and use the existing WAV recording.
        client = self._get_client()
        transcription = client.audio.transcriptions.create(
            file=(wav_path.name, audio_bytes, "audio/wav"),
            model=self.stt_model,
            language="en",
            response_format="text",
        )

        # Groq's transcription endpoint returns a plain string when
        # response_format="text" is used, so handle both the raw string and
        # any object-shaped response defensively.
        if isinstance(transcription, str):
            return transcription.strip()

        return transcription.text.strip()

    def ask_audio(self, wav_path: str) -> str:
        """
        Keep the same public method signature as the existing Gemini wrapper so
        the rest of the project can continue calling:
            reply = assistant.ask_audio("../recordings/current.wav")
        """

        wav_path = Path(wav_path)

        if not wav_path.exists():
            raise FileNotFoundError(wav_path)

        # Step 1: transcribe the user's speech from the recorded WAV.
        user_text = self._transcribe_audio(wav_path)

        if not user_text.strip():
            raise ValueError("Groq transcription returned an empty result.")

        # Step 2: send the cleaned user text to Groq's chat completion endpoint.
        # This preserves the existing architecture: the assistant still exposes
        # one method that returns only the final spoken reply.
        client = self._get_client()
        messages = self._build_messages(user_text)
        completion = client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=0.2,
            max_tokens=256,
        )

        raw_text = completion.choices[0].message.content

        # Persist the latest exchange in memory so follow-up questions can be
        # resolved against the same conversation thread during the current run.
        self.conversation_memory.append({"role": "user", "content": user_text})
        self.conversation_memory.append({"role": "assistant", "content": raw_text})

        print("\n================ RAW GROQ RESPONSE ================\n")
        print(repr(raw_text))
        print("\n====================================================\n")

        return self._clean_response(raw_text)
