import speech_recognition as sr
try:
    import whisper
except Exception as e:
    whisper = None
    print(f"Whisper import failed: {e}")
import os
import tempfile
import warnings
from jarvis_core import config

# Filter out some persistent warnings from Whisper regarding FP16 on CPUs
warnings.filterwarnings("ignore", category=UserWarning)


class Listener:
    def __init__(self, model_size="medium"):
        """
        Initialize the listener.
        model_size: 'tiny', 'base', 'small', 'medium', 'large'.
        'base' is a good balance of speed and accuracy for laptops.
        """
        if whisper is None:
            print("Whisper backend unavailable; SpeechRecognition fallback will be used.")
            self.model = None
        else:
            print(f"Loading Whisper model: {model_size}...")
            try:
                self.model = whisper.load_model(model_size)
            except Exception as e:
                print(f"Failed to load Whisper model: {e}")
                self.model = None
        
        # Initialize the recognizer for microphone handling
        self.recognizer = sr.Recognizer()
        
        # Adjust sensitivity for silence detection
        # Dynamic energy threshold is usually better, but you can hardcode if needed
        self.recognizer.energy_threshold = 300 
        self.recognizer.pause_threshold = 0.8  # Seconds of silence to consider the phrase complete
        self.recognizer.dynamic_energy_threshold = True
        
        print("Listener Ready.")

    def listen_input(self):
        """
        Listens to the microphone, saves to a temp file, and transcribes using Whisper.
        Returns: String (the transcribed text)
        """
        device_index = self._resolve_device_index()
        if device_index is not None:
            print(f"Using microphone device index {device_index} (MIC_DEVICE_NAME='{config.MIC_DEVICE_NAME}')")

        try:
            with sr.Microphone(device_index=device_index) as source:
                print("\nListening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

                try:
                    # 1. Capture Audio
                    # phrase_time_limit prevents it from getting stuck listening forever
                    audio_data = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

                    print("Processing audio...")
                    
                    # 2. Save to temporary WAV file
                    # Whisper works best with file paths or numpy arrays. Files are safer for prototypes.
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                        temp_audio.write(audio_data.get_wav_data())
                        temp_filename = temp_audio.name

                    # 3. Transcribe audio
                    if self.model is not None:
                        # fp16=False is crucial if you are running on CPU (prevents errors)
                        try:
                            result = self.model.transcribe(temp_filename, fp16=False)
                            text = result["text"].strip()
                        except Exception as e:
                            # Common failure: ffmpeg executable missing on Windows -> WinError 2
                            print(f"Whisper transcription failed: {e}")
                            text = None
                    else:
                        text = None

                    if text is None:
                        try:
                            # Fallback: try SpeechRecognition's Google recognizer (requires internet)
                            print("Falling back to SpeechRecognition (Google) for transcription...")
                            r = sr.Recognizer()
                            text = r.recognize_google(audio_data)
                        except Exception as e2:
                            print(f"Fallback STT failed: {e2}")
                            text = ""

                    # 4. Cleanup
                    try:
                        os.remove(temp_filename)
                    except Exception:
                        pass

                    print(f"You said: {text}")
                    return text
                except sr.WaitTimeoutError:
                    print("No speech detected before timeout.")
                    return "" # Returns empty string if no speech detected
                except Exception as e:
                    print(f"Error in listen module: {e}")
                    return ""
        except OSError as e:
            print(f"Microphone initialization failed: {e}")
            print("Available microphone devices:")
            for idx, name in enumerate(sr.Microphone.list_microphone_names()):
                print(f"  {idx}: {name}")
            return ""

    def _resolve_device_index(self):
        if config.MIC_DEVICE_INDEX is not None:
            return config.MIC_DEVICE_INDEX
        if config.MIC_DEVICE_NAME:
            query = config.MIC_DEVICE_NAME.lower()
            for idx, name in enumerate(sr.Microphone.list_microphone_names()):
                if query in name.lower():
                    return idx
            print(f"MIC_DEVICE_NAME '{config.MIC_DEVICE_NAME}' was not found in available devices.")
            print("Available microphone devices:")
            for idx, name in enumerate(sr.Microphone.list_microphone_names()):
                print(f"  {idx}: {name}")
        return None


_singleton_listener = None

def listen_input():
    global _singleton_listener
    if _singleton_listener is None:
        try:
            _singleton_listener = Listener(model_size="medium")
        except Exception as e:
            print(f"Failed to initialize Whisper listener: {e}")
            # Fall back to typed input
            return input("You (type): ").strip()

    return _singleton_listener.listen_input()
