import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Wakeword configuration
WAKEWORD_ENABLED = os.getenv("WAKEWORD_ENABLED", "true").lower() in ("1", "true", "yes")
WAKE_WORD = os.getenv("WAKE_WORD", "jarvis")
TTS_BACKEND = os.getenv("TTS_BACKEND", "auto")  # options: auto, edge, pyttsx3
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "")
# If true, pyttsx3 will save speech to a WAV file and play it with the OS player
# Useful when direct pyttsx3 audio is not audible on some systems
FORCE_PYTTX3_FILE = os.getenv("FORCE_PYTTX3_FILE", "false").lower() in ("1","true","yes")
