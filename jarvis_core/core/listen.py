import speech_recognition as sr
import whisper
import os
import tempfile
import warnings

# Filter out some persistent warnings from Whisper regarding FP16 on CPUs
warnings.filterwarnings("ignore", category=UserWarning)


class Listener:
    def __init__(self, model_size="base"):
        """
        Initialize the listener.
        model_size: 'tiny', 'base', 'small', 'medium', 'large'.
        'base' is a good balance of speed and accuracy for laptops.
        """
        print(f"Loading Whisper model: {model_size}...")
        # Load the model once to avoid reloading it every time we listen
        self.model = whisper.load_model(model_size)
        
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
        with sr.Microphone() as source:
            print("\nListening...")
            
            # Optional: Adjust for ambient noise (good for noisy rooms)
            # self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
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

                # 3. Transcribe with Whisper
                # fp16=False is crucial if you are running on CPU (prevents errors)
                try:
                    result = self.model.transcribe(temp_filename, fp16=False)
                    text = result["text"].strip()
                except Exception as e:
                    # Common failure: ffmpeg executable missing on Windows -> WinError 2
                    print(f"Whisper transcription failed: {e}")
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
                return "" # Returns empty string if no speech detected
            except Exception as e:
                print(f"Error in listen module: {e}")
                return ""


# For compatibility with the rest of the demo scaffold, provide a simple function wrapper
_singleton_listener = None

def listen_input():
    global _singleton_listener
    if _singleton_listener is None:
        try:
            _singleton_listener = Listener(model_size="base")
        except Exception as e:
            print(f"Failed to initialize Whisper listener: {e}")
            # Fall back to typed input
            return input("You (type): ").strip()

    return _singleton_listener.listen_input()
