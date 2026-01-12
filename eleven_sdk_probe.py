import os
import io
import json
import wave
import requests
from dotenv import load_dotenv
load_dotenv()
try:
    try:
        import simpleaudio as sa
        _HAS_SIMPLEAUDIO = True
    except Exception:
        sa = None
        _HAS_SIMPLEAUDIO = False
        import winsound
    import tempfile
    import os
    _HAS_SIMPLEAUDIO = True
except Exception:
    sa = None
    _HAS_SIMPLEAUDIO = False
    import winsound

API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = os.getenv('ELEVENLABS_VOICE')
TEXT = 'Probe: generating short test for ElevenLabs (in-memory).'

"""
ARCHIVED: eleven_sdk_probe.py

Probe helper archived. See `jarvis_core/core/speak.py` for the
production TTS implementation and fallbacks.
"""
try:
    os.startfile(tf.name)
except Exception as e:
    print('Failed to open temp MP3:', e)
    print('Probe complete (HTTP fallback)')
except Exception as e:
    print('HTTP TTS failed:', e)
