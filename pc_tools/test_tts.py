from tts.text_to_speech import TextToSpeech
from audio_io.audio_player import AudioPlayer


tts = TextToSpeech()

player = AudioPlayer()

mp3 = tts.speak(
    "Hello Aymaan. Your wearable assistant is now speaking."
)

player.play(mp3)