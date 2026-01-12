import os
import subprocess
from dotenv import load_dotenv
import requests
load_dotenv()
API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = os.getenv('ELEVENLABS_VOICE')
if not API_KEY or not VOICE_ID:
    print('ELEVENLABS_API_KEY or ELEVENLABS_VOICE not set')
    raise SystemExit(1)

url = f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}'
headers = {
    'xi-api-key': API_KEY,
    'Content-Type': 'application/json',
}
payload = {'text': 'In-memory ffmpeg conversion test', 'voice_settings': {'stability': 0.3, 'similarity_boost': 0.75}}
print('Requesting MP3 from ElevenLabs...')
resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
print('Status', resp.status_code, 'content-type', resp.headers.get('content-type'))
resp.raise_for_status()

ff = ['ffmpeg', '-i', 'pipe:0', '-f', 'wav', '-ar', '24000', '-ac', '1', 'pipe:1', '-hide_banner', '-loglevel', 'error']
print('Downloading full MP3 response into memory...')
mp3_bytes = resp.content
print('Downloaded', len(mp3_bytes), 'bytes; invoking ffmpeg...')
try:
    proc = subprocess.run(ff, input=mp3_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        print('ffmpeg failed, returncode', proc.returncode)
        print('ffmpeg stderr:', proc.stderr.decode('utf-8', errors='ignore'))
        raise RuntimeError('ffmpeg conversion failed')
    wav_bytes = proc.stdout
    print('ffmpeg produced', len(wav_bytes), 'bytes')
except BrokenPipeError as e:
    print('Broken pipe while writing to ffmpeg:', e)
    raise
except Exception as e:
    print('Error running ffmpeg:', e)
    raise

# Play with winsound
try:
    import winsound
    print('Playing via winsound SND_MEMORY...')
    winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
    print('Playback finished')
except Exception as e:
    print('winsound playback failed:', e)
    # Save to temp file as fallback
    import tempfile
    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    tf.write(wav_bytes)
    tf.close()
    print('Saved WAV to', tf.name)
