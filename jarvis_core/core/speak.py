import os
import tempfile
import threading
import time
from .. import config
import requests
import io


class Speaker:
    def __init__(self, backend: str = None, voice: str = None):
        """TTS speaker. backend: 'auto'|'edge'|'pyttsx3'.
        When 'auto', prefer edge-tts if available, else pyttsx3.
        """
        self.backend = backend or config.TTS_BACKEND
        self.voice = voice or config.TTS_VOICE
        self._engine = None

        # Prefer ElevenLabs if configured (force it)
        self._eleven = False
        if config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE and self.backend in ("auto", None, "eleven"):
            self._eleven = True
            self.backend = "eleven"
            print("Speaker: configured to use ElevenLabs backend.")
            return

        # Try to prefer edge-tts when requested or when auto
        if self.backend in ("auto", "edge"):
            try:
                import edge_tts
                self._edge = edge_tts
                self.backend = "edge"
                print("Speaker: using edge-tts backend.")
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
            print("Speaker: using pyttsx3 backend.")
        except Exception as e:
            self._engine = None
            print(f"Speaker initialization failed: {e}")

    def _play_mp3_nonblocking(self, path: str):
        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                # POSIX: try xdg-open
                import subprocess
                subprocess.Popen(["xdg-open", path])

            # Schedule deletion
            def _cleanup():
                time.sleep(8)
                try:
                    os.remove(path)
                except Exception:
                    pass

            threading.Thread(target=_cleanup, daemon=True).start()
        except Exception as e:
            print(f"Failed to play mp3: {e}")

    def speak_output(self, text: str):
        print(f"Jarvis: {text}")
        # ElevenLabs TTS via REST (preferred if configured)
        if self.backend in ("eleven", "auto") and config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE:
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE}"
                # Request WAV so we can play in-memory without ffmpeg
                headers = {
                    "xi-api-key": config.ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "audio/wav",
                }
                payload = {"text": text, "voice_settings": {"stability": 0.3, "similarity_boost": 0.75}}
                resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
                if resp.status_code == 200:
                    try:
                        # Play WAV directly from memory using wave + simpleaudio
                        import wave
                        try:
                            import simpleaudio as sa
                            wav_bytes = io.BytesIO(resp.content)
                            with wave.open(wav_bytes, 'rb') as wr:
                                wave_obj = sa.WaveObject.from_wave_read(wr)
                                play_obj = wave_obj.play()
                                play_obj.wait_done()
                                return
                        except Exception:
                            # Try winsound (Windows) as a no-build-tools fallback
                            try:
                                import winsound
                                if resp.content[:4] == b'RIFF':
                                    winsound.PlaySound(resp.content, winsound.SND_MEMORY)
                                    return
                            except Exception:
                                pass
                    except Exception as e:
                        print(f"In-memory WAV playback failed: {e}, falling back to MP3/temp file")
                        # Fallback: save mp3 or content to temp file and play
                        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                        with open(tmp.name, "wb") as f:
                            f.write(resp.content)
                        self._play_mp3_nonblocking(tmp.name)
                        return
                else:
                    print(f"ElevenLabs TTS failed: {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"ElevenLabs error: {e}")
        # Edge-TTS path
        if getattr(self, "_edge", None):
            try:
                import asyncio
                tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                tmp.close()
                outfile = tmp.name

                async def _save():
                    comm = self._edge.Communicate(text, voice=self.voice)
                    await comm.save(outfile)

                asyncio.run(_save())
                self._play_mp3_nonblocking(outfile)
                return
            except Exception as e:
                print(f"edge-tts error, falling back: {e}")

        # pyttsx3 fallback
        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                return
            except Exception as e:
                print(f"pyttsx3 error: {e}")

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
