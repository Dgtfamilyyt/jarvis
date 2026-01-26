import os
import tempfile
import threading
import time
from .. import config
import requests
import io
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

    def speak_output(self, text: str):
        print(f"Jarvis: {text}", flush=True)
        print(f"[SPEAK] Using backend: {self.backend}", flush=True)
        # ElevenLabs TTS via REST (preferred if configured)
        if self.backend in ("eleven", "auto") and config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE:
            try:
                print(f"[SPEAK] Calling ElevenLabs API...", flush=True)
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE}"
                # Request WAV so we can play in-memory without ffmpeg
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
                    # Detect WAV by RIFF header or content-type
                    is_wav = (content[:4] == b'RIFF') or ('wav' in (resp.headers.get('content-type') or '').lower())
                    wav_bytes = None

                    if not is_wav:
                        # Try to convert MP3 (or other audio) to WAV using ffmpeg in-memory
                        try:
                            # Preserve original sample rate/channels; don't force resampling
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
                        # Diagnostic: report WAV params
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
                                return
                        except Exception as _e:
                            print('[TTS DEBUG] simpleaudio unavailable/failed:', _e)

                        # Try pygame (prefer loading from temp file to avoid buffer format issues)
                        try:
                            import pygame
                            import tempfile
                            print('[TTS DEBUG] Trying pygame playback')
                            # write WAV to temp file and load via filename to ensure correct interpretation
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
                            return
                        except Exception as _e:
                            print('[TTS DEBUG] pygame unavailable/failed:', _e)

                        # Try winsound (Windows) as final in-memory option
                        try:
                            import winsound
                            print('[TTS DEBUG] Trying winsound playback')
                            if wav_bytes[:4] == b'RIFF':
                                winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
                                print('[TTS DEBUG] winsound playback done')
                                return
                        except Exception as _e:
                            print('[TTS DEBUG] winsound unavailable/failed:', _e)

                    # If we reach here, play fallback: save file and open
                    try:
                        tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                        with open(tmp.name, 'wb') as f:
                            f.write(content)
                        self._play_mp3_nonblocking(tmp.name)
                        return
                    except Exception as e:
                        print('Fallback save/play failed:', e)
                else:
                    print(f"[SPEAK] ElevenLabs TTS failed: {resp.status_code} {resp.text}", flush=True)
            except Exception as e:
                print(f"[SPEAK] ElevenLabs error: {e}", flush=True)
        # Edge-TTS path
        if getattr(self, "_edge", None):
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
                return
            except Exception as e:
                print(f"[SPEAK] edge-tts error, falling back: {e}", flush=True)

        # pyttsx3 fallback
        if self._engine:
            try:
                print(f"[SPEAK] Using pyttsx3 backend", flush=True)
                self._engine.say(text)
                print(f"[SPEAK] pyttsx3 speaking...", flush=True)
                self._engine.runAndWait()
                print(f"[SPEAK] pyttsx3 speech completed", flush=True)
                return
            except Exception as e:
                print(f"[SPEAK] pyttsx3 error: {e}", flush=True)

        # Final fallback: print only
        print(text)


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
