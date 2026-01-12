import sys
from pathlib import Path

# Ensure project root is on sys.path so package imports work when running this script directly
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

def run_smoke_test():
    print("--- STARTING JARVIS SMOKE TEST ---")
    
    # 1. Test Dependencies
    print("[1/4] Checking Imports...")
    try:
        import speech_recognition
        import pyttsx3
        import ollama
        import whisper
        print("   PASS: All libraries installed.")
    except ImportError as e:
        print(f"   FAIL: Missing library. {e}")
        sys.exit(1)

    # 2. Test The Mouth (TTS)
    print("[2/4] Testing Mouth (Speaker)...")
    try:
        from jarvis_core.core.speak import Speaker
        bot = Speaker()
        # safe check: use speak_output which falls back to print if TTS unavailable
        bot.speak_output("Smoke test active.")
        print("   PASS: Speaker initialized.")
    except Exception as e:
        print(f"   FAIL: Speaker Error. {e}")

    # 3. Test The Ear (STT)
    print("[3/4] Testing Ear (Microphone & Whisper)...")
    try:
        from jarvis_core.core.listen import Listener
        # Use 'tiny' model for smoke test speed
        ear = Listener(model_size="tiny") 
        print("   PASS: Ear initialized (Model loaded).")
    except Exception as e:
        print(f"   FAIL: Ear Error. Is FFmpeg installed? {e}")

    # 4. Test The Brain (Ollama Connection)
    print("[4/4] Testing Brain (Ollama)...")
    try:
        import ollama
        # Just check if we can list models, implies connection is open
        models = ollama.list()
        if models:
            print("   PASS: Connected to Ollama Local Server.")
        else:
            print("   WARN: Connected, but no models found. Run 'ollama pull llama3.2'")
    except Exception as e:
        print(f"   FAIL: Cannot connect to Ollama. Is the app running? {e}")

    print("\n--- SMOKE TEST COMPLETE ---")

if __name__ == "__main__":
    run_smoke_test()