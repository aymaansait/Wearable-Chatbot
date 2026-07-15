from pathlib import Path
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


class GeminiChat:

    def _clean_response(self, text: str) -> str:
        """
        Remove timestamps like:
        00:00:15
        0:01:23
        """

        text = re.sub(r"\b\d{1,2}:\d{2}:\d{2}\b", "", text)

        # Remove multiple spaces/newlines
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def ask_audio(self, wav_path: str) -> str:

        wav_path = Path(wav_path)

        if not wav_path.exists():
            raise FileNotFoundError(wav_path)

        with open(wav_path, "rb") as f:
            audio_bytes = f.read()

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text="""
You are an intelligent wearable AI assistant.

The attached WAV file contains the user's speech.

Your job is to:

1. Listen to the audio.
2. Understand what the user is asking.
3. Think carefully.
4. Reply naturally as if you are talking to the user.

IMPORTANT RULES:

- Return ONLY your final answer.
- NEVER return a transcript.
- NEVER include timestamps.
- NEVER include subtitles.
- NEVER include speaker labels.
- NEVER describe the audio.
- NEVER explain what you heard.
- NEVER output markdown.

Your response should be exactly what you would speak back to the user.
"""
                        ),
                        types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type="audio/wav",
                        ),
                    ],
                )
            ],
        )

        raw_text = response.text if response.text else ""

        print("\n================ RAW GEMINI RESPONSE ================\n")
        print(repr(raw_text))
        print("\n=====================================================\n")

        return self._clean_response(raw_text)