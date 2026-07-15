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