python -m jarvis_core.main --mode voice #!/usr/bin/env python3
"""
Interactive diagnostic tool to debug Jarvis TTS output.
Run: python diagnose.py
"""

import sys
import os

# Add workspace to path
sys.path.insert(0, r'c:\Users\Davin\VS project\jarvis')

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def check_imports():
    """Check if all required modules can be imported"""
    print_section("1. Checking Python Module Availability")
    
    modules = {
        'pyttsx3': 'Local text-to-speech (CRITICAL - should always work)',
        'edge_tts': 'Free online TTS (optional, internet required)',
        'elevenlabs': 'Premium TTS (optional, API key required)',
        'pygame': 'Audio playback (fallback)',
        'simpleaudio': 'Audio playback (optional)',
        'winsound': 'Windows audio (built-in, should always work)',
        'requests': 'HTTP requests (required)',
    }
    
    for module, description in modules.items():
        try:
            __import__(module)
            print(f"✓ {module:20} - OK - {description}")
        except ImportError as e:
            print(f"✗ {module:20} - MISSING - {description}")
            print(f"  Error: {e}")

def check_env():
    """Check environment configuration"""
    print_section("2. Checking Configuration Files")
    
    env_file = r'c:\Users\Davin\VS project\jarvis\.env'
    if os.path.exists(env_file):
        print(f"✓ .env file found at {env_file}")
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            
            from jarvis_core import config
            print(f"  TTS_BACKEND: {config.TTS_BACKEND}")
            print(f"  TTS_VOICE: {config.TTS_VOICE}")
            
            if config.ELEVENLABS_API_KEY:
                # Don't print the full key, just show it's set
                print(f"  ELEVENLABS_API_KEY: {'*' * 20} (SET)")
            else:
                print(f"  ELEVENLABS_API_KEY: NOT SET (ElevenLabs will be skipped)")
                
            if config.ELEVENLABS_VOICE:
                print(f"  ELEVENLABS_VOICE: {config.ELEVENLABS_VOICE} (SET)")
            else:
                print(f"  ELEVENLABS_VOICE: NOT SET")
        except Exception as e:
            print(f"✗ Error reading config: {e}")
    else:
        print(f"✗ .env file NOT found at {env_file}")
        print("  Creating basic .env template...")

def test_pyttsx3():
    """Test pyttsx3 directly"""
    print_section("3. Testing pyttsx3 (Local Offline TTS)")
    
    try:
        import pyttsx3
        print("✓ pyttsx3 module imported successfully")
        
        # Initialize
        engine = pyttsx3.init()
        print("✓ pyttsx3 engine initialized")
        
        # Get voices
        voices = engine.getProperty('voices')
        print(f"✓ Found {len(voices)} voices:")
        for i, voice in enumerate(voices[:3]):
            print(f"    [{i}] {voice.name}")
        
        # Set properties
        engine.setProperty('rate', 175)
        print("✓ Speech rate set to 175")
        
        # Test speech
        print("\n  Testing speech output (you should hear 'Hello from pyttsx3')...")
        print("  [If you hear nothing, check Windows Volume Mixer for Python]")
        engine.say("Hello from pyttsx3")
        engine.runAndWait()
        print("✓ pyttsx3 runAndWait() completed")
        
    except Exception as e:
        print(f"✗ pyttsx3 test failed: {e}")
        import traceback
        traceback.print_exc()

def test_speaker_class():
    """Test the Jarvis Speaker class"""
    print_section("4. Testing Jarvis Speaker Class")
    
    try:
        from jarvis_core.core.speak import Speaker
        
        print("Testing Speaker with offline=True (forces pyttsx3)...")
        speaker = Speaker(offline=True)
        print(f"✓ Speaker initialized with backend: {speaker.backend}")
        
        print("\n  Testing speak_output (you should hear 'Testing Jarvis speaker class')...")
        speaker.speak_output("Testing Jarvis speaker class")
        print("✓ speak_output() completed")
        
    except Exception as e:
        print(f"✗ Speaker test failed: {e}")
        import traceback
        traceback.print_exc()

def test_full_pipeline():
    """Test the full Jarvis pipeline"""
    print_section("5. Testing Full Jarvis Pipeline")
    
    try:
        from jarvis_core.core.speak import Speaker
        from jarvis_core.brain.llm_client import Brain
        
        print("Initializing Speaker...")
        speaker = Speaker(offline=True)
        
        print(f"Speaker backend: {speaker.backend}")
        
        print("\nInitializing Brain (Ollama)...")
        print("  (Ollama should be running locally)")
        try:
            brain = Brain(model="llama3.2")
            print("✓ Brain initialized")
        except Exception as brain_err:
            print(f"⚠ Brain initialization warning: {brain_err}")
            print("  This is OK if Ollama is not running - speaker still works")
        
        print("\nTesting full response pipeline...")
        test_text = "What is the capital of France?"
        
        print(f"  Input: '{test_text}'")
        print("  Processing...")
        
        try:
            # This might fail if Ollama is down, but that's OK for this test
            response = brain.think(test_text)
            print(f"  Response: {response[:100]}...")
            
            print("  Speaking response...")
            speaker.speak_output(response)
            print("✓ Full pipeline completed")
        except Exception as pipeline_err:
            print(f"⚠ Pipeline warning: {pipeline_err}")
            print("  This is likely because Ollama is not running")
            print("  Testing speaker only...")
            speaker.speak_output("This is a test of the speaker system")
            print("✓ Speaker test completed")
        
    except Exception as e:
        print(f"✗ Full pipeline test failed: {e}")
        import traceback
        traceback.print_exc()

def print_instructions():
    """Print next steps"""
    print_section("Next Steps")
    print("""
If you can HEAR audio output:
  ✓ The TTS system is working correctly
  ✓ Run: python -m jarvis_core.main --mode text
  ✓ Type messages and listen for audio responses

If you CANNOT hear audio output:
  1. Check Windows Volume Mixer - make sure Python isn't muted
  2. Try adjusting system volume
  3. Test a Windows sound directly to ensure audio works
  4. Verify speakers/headphones are connected
  5. Try the offline mode: python -m jarvis_core.main --mode text --offline

If you see ERROR messages:
  1. Read the [SPEAK] prefixed error messages carefully
  2. Look for API key issues (ElevenLabs)
  3. Check that required modules are installed
  4. Review the DIAGNOSTIC_GUIDE.md file
  """)

if __name__ == "__main__":
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  JARVIS VOICE ASSISTANT - DIAGNOSTIC TOOL".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        check_imports()
        check_env()
        test_pyttsx3()
        test_speaker_class()
        test_full_pipeline()
        print_instructions()
    except Exception as e:
        print(f"\nFatal error during diagnostics: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("  Diagnostic complete. Check output above for issues.")
    print("="*70 + "\n")
