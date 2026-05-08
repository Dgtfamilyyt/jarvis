import os
import tempfile
import threading
import time
import queue as _queue
from .. import config
import requests
import io
import json
import subprocess


class Speaker:
    def __init__(self, backend: str = None, voice: str = None, offline: bool = False):
        """TTS speaker. backend: 'auto'|'edge'|'pyttsx3'|'eleven'.
        When 'auto', prefer edge-tts if available, else pyttsx3.
        If offline=True, only use pyttsx3 (no internet-dependent backends).
        """
        
        self.backend = backend or config.TTS_BACKEND
        self.voice = voice or config.TTS_VOICE
        self.offline = offline
        self._engine = None
        self._play_q = None
        self._play_thread = None

        # If offline mode, skip all online services and use pyttsx3 only
        if self.offline:
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                voices = self._engine.getProperty("voices")
                if voices:
                    try:
                        self._engine.setProperty("voice", voices[0].id)
                    except Exception:
                        pass
                self._engine.setProperty("rate", 175)
                self.backend = "pyttsx3"
                print("Speaker: offline mode - using pyttsx3 backend only.", flush=True)
                # Start worker queue so pyttsx3 runs on a dedicated thread
                try:
                    self._play_q = _queue.Queue()
                    def _pytt_worker_offline():
                        while True:
                            item = self._play_q.get()
                            if item is None:
                                break
                            text, ev = item
                            try:
                                self._engine.say(text)
                                self._engine.runAndWait()
                                if ev:
                                    ev.set()
                            except Exception as e:
                                print(f"[SPEAK] pyttsx3 offline worker error: {e}", flush=True)
                                if ev:
                                    ev.set()
                    self._play_thread = threading.Thread(target=_pytt_worker_offline, daemon=True)
                    self._play_thread.start()
                except Exception as e:
                    print(f"[SPEAK] Failed to start pyttsx3 offline worker: {e}", flush=True)
            except Exception as e:
                self._engine = None
                print(f"Speaker offline init failed: {e}", flush=True)
            return

        # Prefer ElevenLabs if configured (force it)
        self._eleven = False
        if config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE and self.backend in ("auto", None, "eleven"):
            self._eleven = True
            self.backend = "eleven"
            print("Speaker: configured to use ElevenLabs backend.", flush=True)
            return

        # Try to prefer edge-tts when requested or when auto (skip in offline mode)
        if self.backend in ("auto", "edge"):
            try:
                import edge_tts
                self._edge = edge_tts
                self.backend = "edge"
                print("Speaker: using edge-tts backend.", flush=True)
                return
            except Exception:
                self._edge = None

        # Fallback to pyttsx3
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            voices = self._engine.getProperty("voices")
            if voices:
                try:
                    self._engine.setProperty("voice", voices[0].id)
                except Exception:
                    pass
            self._engine.setProperty("rate", 175)
            self.backend = "pyttsx3"
            print("Speaker: using pyttsx3 backend.", flush=True)
            # Create a playback queue and worker so pyttsx3 always runs on its own thread
            try:
                self._play_q = _queue.Queue()
                def _pytt_worker():
                    while True:
                        try:
                            item = self._play_q.get()
                            if item is None:
                                break
                            text, ev = item
                            try:
                                self._engine.say(text)
                                self._engine.runAndWait()
                                if ev:
                                    ev.set()
                            except Exception as e:
                                print(f"[SPEAK] pyttsx3 worker error: {e}", flush=True)
                                if ev:
                                    ev.set()
                        except Exception as e:
                            print(f"[SPEAK] pyttsx3 worker top-level error: {e}", flush=True)
                self._play_thread = threading.Thread(target=_pytt_worker, daemon=True)
                self._play_thread.start()
            except Exception as e:
                print(f"[SPEAK] Failed to start pyttsx3 worker thread: {e}", flush=True)
        except Exception as e:
            self._engine = None
            print(f"Speaker initialization failed: {e}", flush=True)

    def _play_mp3_nonblocking(self, path: str):
        try:
            print(f"[SPEAK] Playing MP3: {path}", flush=True)
            if os.name == "nt":
                os.startfile(path)
            else:
                # POSIX: try xdg-open
                import subprocess
                subprocess.Popen(["xdg-open", path])
            print(f"[SPEAK] MP3 playback initiated", flush=True)

            # Schedule deletion
            def _cleanup():
                time.sleep(8)
                try:
                    os.remove(path)
                except Exception:
                    pass

            threading.Thread(target=_cleanup, daemon=True).start()
        except Exception as e:
            print(f"[SPEAK] Failed to play mp3: {e}", flush=True)

    def _enable_offline_pyttsx3(self):
        """Attempt to initialize pyttsx3 and switch the speaker to offline mode."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            if voices:
                try:
                    engine.setProperty("voice", voices[0].id)
                except Exception:
                    pass
            engine.setProperty("rate", 175)
            self._engine = engine
            self.backend = "pyttsx3"
            self.offline = True
            # clear any online backends to avoid retries
            self._edge = None
            self._eleven = False
            # If worker queue/thread not created yet, create them to ensure proper thread usage
            try:
                if not getattr(self, '_play_q', None):
                    self._play_q = _queue.Queue()

                    def _pytt_worker():
                        while True:
                            try:
                                item = self._play_q.get()
                                if item is None:
                                    break
                                text, ev = item
                                try:
                                    self._engine.say(text)
                                    self._engine.runAndWait()
                                    if ev:
                                        ev.set()
                                except Exception as e:
                                    print(f"[SPEAK] pyttsx3 worker error: {e}", flush=True)
                                    if ev:
                                        ev.set()
                            except Exception as e:
                                print(f"[SPEAK] pyttsx3 worker top-level error: {e}", flush=True)

                    self._play_thread = threading.Thread(target=_pytt_worker, daemon=True)
                    self._play_thread.start()
            except Exception as e:
                print(f"[SPEAK] Failed to start pyttsx3 worker thread during fallback: {e}", flush=True)

            print("[SPEAK] Switched to offline pyttsx3 backend after ElevenLabs failure.", flush=True)
            return True
        except Exception as e:
            print(f"[SPEAK] Failed to initialize pyttsx3 during fallback: {e}", flush=True)
            self._engine = None
            return False

    def speak_output(self, text: str):
        print(f"Jarvis: {text}", flush=True)
        
        # Try TTS backends in priority order: ElevenLabs -> Edge-TTS -> OpenRouter -> gTTS -> pyttsx3
        backends = [
            ("eleven", self._speak_elevenlabs),
            ("edge", self._speak_edge_tts),
            ("openrouter", self._speak_openrouter),
            ("gtts", self._speak_gtts),
            ("pyttsx3", self._speak_pyttsx3)
        ]
        
        for backend_name, speak_func in backends:
            try:
                print(f"[SPEAK] Attempting backend: {backend_name}", flush=True)
                if speak_func(text):
                    print(f"[SPEAK] Successfully spoke using {backend_name}", flush=True)
                    return
                else:
                    print(f"[SPEAK] {backend_name} backend failed or unavailable", flush=True)
            except Exception as e:
                print(f"[SPEAK] {backend_name} backend error: {e}", flush=True)
        
        # All backends failed
        print(f"[SPEAK] All TTS backends failed. Outputting text only: {text}", flush=True)

    def _speak_elevenlabs(self, text: str) -> bool:
        """Attempt to speak using ElevenLabs TTS. Returns True if successful."""
        if not (config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE):
            return False
        
        try:
            print(f"[SPEAK] Calling ElevenLabs API...", flush=True)
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE}"
            headers = {
                "xi-api-key": config.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/wav",
            }
            payload = {"text": text, "voice_settings": {"stability": 0.3, "similarity_boost": 0.75}}
            resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
            print(f"[SPEAK] ElevenLabs response status: {resp.status_code}", flush=True)
            if resp.status_code == 200:
                content = resp.content
                is_wav = (content[:4] == b'RIFF') or ('wav' in (resp.headers.get('content-type') or '').lower())
                wav_bytes = None

                if not is_wav:
                    try:
                        ff = ['ffmpeg', '-i', 'pipe:0', '-f', 'wav', 'pipe:1', '-hide_banner', '-loglevel', 'error']
                        proc = subprocess.run(ff, input=content, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                        if proc.returncode == 0 and proc.stdout:
                            wav_bytes = proc.stdout
                            is_wav = True
                        else:
                            print('ffmpeg conversion failed:', proc.returncode, proc.stderr.decode('utf-8', errors='ignore'))
                    except Exception as e:
                        print('ffmpeg conversion exception:', e)

                if is_wav and wav_bytes is None:
                    wav_bytes = content

                if wav_bytes:
                    try:
                        import wave as _wave
                        with _wave.open(io.BytesIO(wav_bytes), 'rb') as _wr:
                            _nch = _wr.getnchannels()
                            _sampw = _wr.getsampwidth()
                            _fr = _wr.getframerate()
                            _nframes = _wr.getnframes()
                            _comptype = _wr.getcomptype()
                        print(f"[TTS DEBUG] WAV params: nch={_nch}, sampwidth={_sampw}, framerate={_fr}, nframes={_nframes}, comptype={_comptype}")
                    except Exception as _e:
                        print('[TTS DEBUG] Failed to read WAV params:', _e)

                    # Try simpleaudio first
                    try:
                        import wave
                        import simpleaudio as sa
                        print('[TTS DEBUG] Trying simpleaudio playback')
                        with wave.open(io.BytesIO(wav_bytes), 'rb') as wr:
                            wave_obj = sa.WaveObject.from_wave_read(wr)
                            play_obj = wave_obj.play()
                            play_obj.wait_done()
                            print('[TTS DEBUG] simpleaudio playback done')
                            return True
                    except Exception as _e:
                        print('[TTS DEBUG] simpleaudio unavailable/failed:', _e)

                    # Try pygame
                    try:
                        import pygame
                        import tempfile
                        print('[TTS DEBUG] Trying pygame playback')
                        tf = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                        tf.write(wav_bytes)
                        tf.flush()
                        tf.close()
                        try:
                            with wave.open(tf.name, 'rb') as wr:
                                fr = wr.getframerate()
                                chs = wr.getnchannels()
                            pygame.mixer.init(frequency=fr, channels=chs)
                        except Exception:
                            try:
                                pygame.mixer.init()
                            except Exception:
                                pass
                        print('[TTS DEBUG] pygame mixer init:', pygame.mixer.get_init())
                        snd = pygame.mixer.Sound(tf.name)
                        ch = snd.play()
                        while ch.get_busy():
                            pygame.time.wait(50)
                        print('[TTS DEBUG] pygame playback done; temp file:', tf.name)
                        return True
                    except Exception as _e:
                        print('[TTS DEBUG] pygame unavailable/failed:', _e)

                    # Try winsound (Windows)
                    try:
                        import winsound
                        print('[TTS DEBUG] Trying winsound playback')
                        if wav_bytes[:4] == b'RIFF':
                            winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
                            print('[TTS DEBUG] winsound playback done')
                            return True
                    except Exception as _e:
                        print('[TTS DEBUG] winsound unavailable/failed:', _e)

                # Fallback: save file and play
                try:
                    tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                    with open(tmp.name, 'wb') as f:
                        f.write(content)
                    self._play_mp3_nonblocking(tmp.name)
                    return True
                except Exception as e:
                    print('Fallback save/play failed:', e)
            else:
                print(f"[SPEAK] ElevenLabs TTS failed: {resp.status_code} {resp.text}", flush=True)
        except Exception as e:
            print(f"[SPEAK] ElevenLabs error: {e}", flush=True)
        return False

    def _speak_edge_tts(self, text: str) -> bool:
        """Attempt to speak using Edge TTS. Returns True if successful."""
        if not hasattr(self, '_edge') or self._edge is None:
            return False
        
        try:
            print(f"[SPEAK] Using edge-tts backend", flush=True)
            import asyncio
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.close()
            outfile = tmp.name

            async def _save():
                comm = self._edge.Communicate(text, voice=self.voice)
                await comm.save(outfile)

            asyncio.run(_save())
            print(f"[SPEAK] edge-tts generated MP3: {outfile}", flush=True)
            self._play_mp3_nonblocking(outfile)
            return True
        except Exception as e:
            print(f"[SPEAK] edge-tts error: {e}", flush=True)
        return False

    def _speak_openrouter(self, text: str) -> bool:
        """Attempt to speak using OpenRouter GPT Audio. Returns True if successful."""
        if not config.OPENROUTER_API_KEY:
            return False
        
        try:
            print(f"[SPEAK] Calling OpenRouter GPT Audio API...", flush=True)
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://jarvis.local",
                "X-OpenRouter-Title": "Jarvis Voice Assistant"
            }
            payload = {
                "model": "openai/gpt-audio",
                "modalities": ["text", "audio"],
                "audio": {"voice": "alloy", "format": "wav"},
                "stream": True,
                "messages": [
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30, stream=True)
            print(f"[SPEAK] OpenRouter response status: {resp.status_code}", flush=True)
            
            if resp.status_code == 200:
                # Handle streaming response
                audio_data = None
                for line in resp.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            if data == '[DONE]':
                                break
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    choice = chunk["choices"][0]
                                    if "delta" in choice and "audio" in choice["delta"]:
                                        # Accumulate audio data
                                        if audio_data is None:
                                            audio_data = ""
                                        audio_data += choice["delta"]["audio"]["data"]
                            except json.JSONDecodeError:
                                continue
                
                if audio_data:
                    # Decode base64 audio data
                    import base64
                    wav_bytes = base64.b64decode(audio_data)
                    
                    # Try to play the WAV data using the same playback logic as ElevenLabs
                    try:
                        import wave as _wave
                        with _wave.open(io.BytesIO(wav_bytes), 'rb') as _wr:
                            _nch = _wr.getnchannels()
                            _sampw = _wr.getsampwidth()
                            _fr = _wr.getframerate()
                            _nframes = _wr.getnframes()
                            _comptype = _wr.getcomptype()
                        print(f"[TTS DEBUG] OpenRouter WAV params: nch={_nch}, sampwidth={_sampw}, framerate={_fr}, nframes={_nframes}, comptype={_comptype}")
                    except Exception as _e:
                        print('[TTS DEBUG] Failed to read OpenRouter WAV params:', _e)

                        # Try simpleaudio first
                        try:
                            import wave
                            import simpleaudio as sa
                            print('[TTS DEBUG] Trying simpleaudio playback')
                            with wave.open(io.BytesIO(wav_bytes), 'rb') as wr:
                                wave_obj = sa.WaveObject.from_wave_read(wr)
                                play_obj = wave_obj.play()
                                play_obj.wait_done()
                                print('[TTS DEBUG] simpleaudio playback done')
                                return True
                        except Exception as _e:
                            print('[TTS DEBUG] simpleaudio unavailable/failed:', _e)

                        # Try pygame
                        try:
                            import pygame
                            import tempfile
                            print('[TTS DEBUG] Trying pygame playback')
                            tf = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                            tf.write(wav_bytes)
                            tf.flush()
                            tf.close()
                            try:
                                with wave.open(tf.name, 'rb') as wr:
                                    fr = wr.getframerate()
                                    chs = wr.getnchannels()
                                pygame.mixer.init(frequency=fr, channels=chs)
                            except Exception:
                                try:
                                    pygame.mixer.init()
                                except Exception:
                                    pass
                            print('[TTS DEBUG] pygame mixer init:', pygame.mixer.get_init())
                            snd = pygame.mixer.Sound(tf.name)
                            ch = snd.play()
                            while ch.get_busy():
                                pygame.time.wait(50)
                            print('[TTS DEBUG] pygame playback done; temp file:', tf.name)
                            return True
                        except Exception as _e:
                            print('[TTS DEBUG] pygame unavailable/failed:', _e)

                        # Try winsound (Windows)
                        try:
                            import winsound
                            print('[TTS DEBUG] Trying winsound playback')
                            if wav_bytes[:4] == b'RIFF':
                                winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
                                print('[TTS DEBUG] winsound playback done')
                                return True
                        except Exception as _e:
                            print('[TTS DEBUG] winsound unavailable/failed:', _e)

                        # Fallback: save file and play
                        try:
                            tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                            with open(tmp.name, 'wb') as f:
                                f.write(wav_bytes)
                            self._play_mp3_nonblocking(tmp.name)
                            return True
                        except Exception as e:
                            print('OpenRouter fallback save/play failed:', e)
                    else:
                        print(f"[SPEAK] OpenRouter response missing audio data: {response_data}")
                else:
                    print(f"[SPEAK] OpenRouter response missing choices: {response_data}")
            else:
                print(f"[SPEAK] OpenRouter TTS failed: {resp.status_code} {resp.text}", flush=True)
        except Exception as e:
            print(f"[SPEAK] OpenRouter error: {e}", flush=True)
        return False

    def _speak_gtts(self, text: str) -> bool:
        """Attempt to speak using free Google Translate TTS via gTTS."""
        try:
            from gtts import gTTS
        except Exception as e:
            print(f"[SPEAK] gTTS unavailable: {e}", flush=True)
            return False

        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tmp.close()
            tts = gTTS(text=text, lang="en")
            tts.save(tmp.name)
            self._play_mp3_nonblocking(tmp.name)
            return True
        except Exception as e:
            print(f"[SPEAK] gTTS error: {e}", flush=True)
        return False

    def _speak_pyttsx3(self, text: str) -> bool:
        """Attempt to speak using pyttsx3. Returns True if successful."""
        if self._engine is None:
            return False
        
        try:
            print(f"[SPEAK] Using pyttsx3 backend", flush=True)
            if getattr(self, '_play_q', None):
                ev = threading.Event()
                try:
                    self._play_q.put((text, ev))
                    print(f"[SPEAK] pyttsx3 queued (waiting for completion)", flush=True)
                    ev.wait(timeout=8)
                    print(f"[SPEAK] pyttsx3 speech completed (queued)", flush=True)
                    return True
                except Exception as e:
                    print(f"[SPEAK] Failed to queue pyttsx3 speak: {e}", flush=True)
                    try:
                        self._engine.say(text)
                        print(f"[SPEAK] pyttsx3 speaking (direct fallback)...", flush=True)
                        self._engine.runAndWait()
                        print(f"[SPEAK] pyttsx3 speech completed (direct)", flush=True)
                        return True
                    except Exception as e2:
                        print(f"[SPEAK] pyttsx3 direct fallback failed: {e2}", flush=True)
            else:
                self._engine.say(text)
                print(f"[SPEAK] pyttsx3 speaking...", flush=True)
                self._engine.runAndWait()
                print(f"[SPEAK] pyttsx3 speech completed", flush=True)
                return True
        except Exception as e:
            print(f"[SPEAK] pyttsx3 error: {e}", flush=True)
        return False

    def _pytt_save_and_play(self, text: str):
        """Save TTS output to a WAV file using a fresh pyttsx3 engine and play it with OS player/winsound."""
        try:
            import pyttsx3
            import tempfile
            import os
            engine = pyttsx3.init()
            tf = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            tf_name = tf.name
            tf.close()
            try:
                engine.save_to_file(text, tf_name)
                engine.runAndWait()
            except Exception as e:
                # cleanup and re-raise
                try:
                    os.remove(tf_name)
                except Exception:
                    pass
                raise

            # Play the file: prefer winsound on Windows for memory play
            try:
                if os.name == 'nt':
                    import winsound
                    winsound.PlaySound(tf_name, winsound.SND_FILENAME)
                else:
                    # Use default application to open the file
                    try:
                        os.startfile(tf_name)
                    except Exception:
                        # POSIX: fall back to xdg-open
                        import subprocess
                        subprocess.Popen(["xdg-open", tf_name])
            except Exception as e:
                print(f"[SPEAK] Failed to play saved WAV: {e}", flush=True)
            finally:
                # Schedule cleanup
                def _cleanup():
                    time.sleep(6)
                    try:
                        os.remove(tf_name)
                    except Exception:
                        pass
                threading.Thread(target=_cleanup, daemon=True).start()
            return True
        except Exception as e:
            print(f"[SPEAK] _pytt_save_and_play failed: {e}", flush=True)
            return False


# Module-level singleton for convenience
_singleton_speaker = None


def speak_output(text: str):
    global _singleton_speaker
    if _singleton_speaker is None:
        _singleton_speaker = Speaker()
    _singleton_speaker.speak_output(text)


if __name__ == "__main__":
    s = Speaker()
    s.speak_output("Systems are online. How can I help you?")
