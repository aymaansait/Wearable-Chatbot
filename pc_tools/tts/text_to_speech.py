import asyncio
import time
from pathlib import Path
import edge_tts


class TextToSpeech:

    def __init__(self):

        self.voice = "en-US-AriaNeural"

        self.output_dir = Path("../responses")
        self.output_dir.mkdir(exist_ok=True)

    async def _generate(self, text, output_path):

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
        )

        await communicate.save(
            str(output_path)
        )

    def speak(self, text):

        # Unique filename per call, same pattern as WavRecorder,
        # so concurrent calls (e.g. "Yes" acknowledgement + the
        # real reply, on separate threads) never collide on the
        # same file, and Windows never locks a file mid-write
        # while a previous one is still being read by the player.
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        output_path = self.output_dir / f"response_{timestamp}_{id(text) % 10000}.mp3"

        asyncio.run(
            self._generate(text, output_path)
        )

        return output_path