import asyncio
from pathlib import Path
import edge_tts


class TextToSpeech:

    def __init__(self):

        self.voice = "en-US-AriaNeural"

        self.output_file = (
            Path("../responses") / "response.mp3"
        )

        self.output_file.parent.mkdir(
            exist_ok=True
        )

    async def _generate(self, text):

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
        )

        await communicate.save(
            str(self.output_file)
        )

    def speak(self, text):

        asyncio.run(
            self._generate(text)
        )

        return self.output_file