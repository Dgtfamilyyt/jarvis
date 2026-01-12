import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('ELEVENLABS_API_KEY')
if not key:
    print('No ELEVENLABS_API_KEY found in environment.')
    raise SystemExit(1)

print('Fetching ElevenLabs voices...')
resp = requests.get('https://api.elevenlabs.io/v1/voices', headers={'xi-api-key': key}, timeout=15)
if resp.status_code != 200:
    print('Failed to fetch voices:', resp.status_code, resp.text)
    raise SystemExit(1)

data = resp.json()
voices = data.get('voices') or data.get('voice_list') or []
if not voices:
    print('No voices returned by ElevenLabs API.')
    raise SystemExit(1)

# Choose the first voice
voice = voices[0]
voice_id = voice.get('voice_id') or voice.get('id') or voice.get('unique_id')
voice_name = voice.get('name') or ''
print(f"Selected voice: {voice_name} ({voice_id})")

# Append voice to .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
with open(env_path, 'a', encoding='utf-8') as f:
    f.write(f"ELEVENLABS_VOICE={voice_id}\n")

# Run a TTS test using the project speak module
print('Running TTS test...')
from jarvis_core.core.speak import Speaker
s = Speaker(backend='eleven')
s.speak_output('This is a test from Eleven Labs via Jarvis.')
print('TTS test complete.')
