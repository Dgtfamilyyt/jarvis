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

print('Voice id:', VOICE_ID)

def play_wav_bytes(wav_bytes: bytes):
    try:
        wf = wave.open(io.BytesIO(wav_bytes), 'rb')
        if _HAS_SIMPLEAUDIO and sa is not None:
            wave_obj = sa.WaveObject.from_wave_read(wf)
            play_obj = wave_obj.play()
            play_obj.wait_done()
            print('Played WAV bytes via simpleaudio')
        else:
            # winsound requires the raw WAV bytes and SND_MEMORY
            try:
                winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
                print('Played WAV bytes via winsound')
            except Exception as e:
                print('winsound play failed:', e)
    except Exception as e:
        print('Failed to play WAV bytes:', e)

# Try SDK import first (best-effort)
try:
    import elevenlabs
    print('elevenlabs module found at', getattr(elevenlabs, '__file__', 'unknown'))
    # Try common SDK entry points; adapt to installed SDK where possible
    if hasattr(elevenlabs, 'set_api_key') and hasattr(elevenlabs, 'generate'):
        try:
            elevenlabs.set_api_key(API_KEY)
            print('Using elevenlabs.set_api_key + generate API')
            audio = elevenlabs.generate(text=TEXT, voice=VOICE_ID)
            # If the SDK returns bytes, try to play
            if isinstance(audio, (bytes, bytearray)):
                play_wav_bytes(bytes(audio))
            else:
                print('SDK returned type:', type(audio), '- not playing automatically')
            print('Probe complete (SDK path)')
        except Exception as e:
            print('SDK generation failed:', e)
            raise
    else:
        print('SDK present but expected helpers not found; falling back to HTTP API')
        raise ImportError('Incompatible SDK surface')
except Exception as sdk_err:
    print('SDK path failed:', sdk_err)
    # Fallback: use ElevenLabs HTTP API to generate WAV and play in-memory
    if not API_KEY or not VOICE_ID:
        print('ELEVENLABS_API_KEY or ELEVENLABS_VOICE not set in environment; cannot proceed')
    else:
        print('Falling back to HTTP TTS API...')
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream'
        headers = {
            'Accept': 'audio/wav',
            'xi-api-key': API_KEY,
            'Content-Type': 'application/json'
        }
        payload = {
            'text': TEXT,
            'voice_settings': {
                'stability': 0.5,
                'similarity_boost': 0.75
            }
        }
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), stream=False, timeout=30)
            resp.raise_for_status()
            wav_bytes = resp.content
            print('HTTP TTS returned', len(wav_bytes), 'bytes; playing...')
            # If bytes look like RIFF/WAV, play in-memory; otherwise save as MP3 and open
            if wav_bytes[:4] == b'RIFF':
                play_wav_bytes(wav_bytes)
            else:
                tf = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                tf.write(wav_bytes)
                tf.flush()
                tf.close()
                print('Saved HTTP TTS to', tf.name, '— opening with default player')
                try:
                    os.startfile(tf.name)
                except Exception as e:
                    print('Failed to open temp MP3:', e)
            print('Probe complete (HTTP fallback)')
        except Exception as e:
            print('HTTP TTS failed:', e)
