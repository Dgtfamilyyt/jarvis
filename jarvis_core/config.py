import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Wakeword configuration
WAKEWORD_ENABLED = os.getenv("WAKEWORD_ENABLED", "false").lower() in ("1", "true", "yes")
WAKE_WORD = os.getenv("WAKE_WORD", "Jarvis")
MIC_DEVICE_NAME = os.getenv("MIC_DEVICE_NAME", "")
MIC_DEVICE_INDEX = int(os.getenv("MIC_DEVICE_INDEX")) if os.getenv("MIC_DEVICE_INDEX") else None
TTS_BACKEND = os.getenv("TTS_BACKEND", "auto")  # options: auto, edge, pyttsx3
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_IMAGE_API_KEY = os.getenv("OPENROUTER_IMAGE_API_KEY", "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")
# If true, pyttsx3 will save speech to a WAV file and play it with the OS player
# Useful when direct pyttsx3 audio is not audible on some systems
FORCE_PYTTX3_FILE = os.getenv("FORCE_PYTTX3_FILE", "false").lower() in ("1","true","yes")

# ---- Web scraping configuration ----
# Set to true to enable programmatic HTTP scraping via skills/web_ops.py
ENABLE_SCRAPING = os.getenv("ENABLE_SCRAPING", "false").lower() in ("1","true","yes")
# Respect site robots.txt when scraping (recommended)
SCRAPING_RESPECT_ROBOTS = os.getenv("SCRAPING_RESPECT_ROBOTS", "true").lower() in ("1","true","yes")
# Default user agent used for scraping
SCRAPING_USER_AGENT = os.getenv("SCRAPING_USER_AGENT", "JarvisBot/1.0 (+https://example.local)")
# Request timeout (seconds)
SCRAPING_TIMEOUT = float(os.getenv("SCRAPING_TIMEOUT", "10"))
# Max bytes to download from a page (prevents very large downloads)
SCRAPING_MAX_BYTES = int(os.getenv("SCRAPING_MAX_BYTES", "200000"))  # ~200 KB

# ---- Web search configuration ----
# Provider: 'duckduckgo' (default, no API key) or 'bing' (requires BING_SUBSCRIPTION_KEY)
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo").lower()
BING_SUBSCRIPTION_KEY = os.getenv("BING_SUBSCRIPTION_KEY", "")
BING_ENDPOINT = os.getenv("BING_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search")
