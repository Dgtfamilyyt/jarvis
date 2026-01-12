import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WAKER_WORD = os.getenv("WAKE_WORD", "jarvis")
TTS_BACKEND = os.getenv("TTS_BACKEND", "auto")  # options: auto, edge, pyttsx3
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "")
