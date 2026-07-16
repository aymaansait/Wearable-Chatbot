from pathlib import Path
import pygame
import time


class AudioPlayer:

    def __init__(self):

        pygame.init()
        pygame.mixer.init()

    def play(self, filename):

        filename = Path(filename)

        pygame.mixer.music.load(
            str(filename)
        )

        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

        # Explicitly unload so pygame releases its file handle.
        # Without this, Windows can keep the file locked even
        # after playback finishes, which caused PermissionError
        # on the next TTS write.
        pygame.mixer.music.unload()