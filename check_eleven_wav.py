import os
import requests
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('ELEVENLABS_API_KEY')
vid = os.getenv('ELEVENLABS_VOICE')
if not key or not vid:
    print('ELEVENLABS_API_KEY or ELEVENLABS_VOICE not set')
    raise SystemExit(1)
headers = {
    'Accept': 'audio/wav',
    'xi-api-key': key,
    'Content-Type': 'application/json'
}
payload = {
    'text': 'In-memory WAV test',
    'voice_settings': {'stability': 0.3, 'similarity_boost': 0.75}
}
resp = requests.post(f'https://api.elevenlabs.io/v1/text-to-speech/{vid}', headers=headers, json=payload, timeout=30)
print('status:', resp.status_code)
print('content-type:', resp.headers.get('content-type'))
first = resp.content[:16]
print('first bytes:', first)
print('starts RIFF:', first[:4] == b'RIFF')
with open('eleven_sample_head.bin','wb') as f:
    f.write(resp.content[:256])
print('Wrote sample head to eleven_sample_head.bin')
