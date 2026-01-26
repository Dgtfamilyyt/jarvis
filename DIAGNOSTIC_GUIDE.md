# Jarvis Voice Assistant - Diagnostic Guide

## Quick Start

### Activate the virtual environment
```powershell
.venv\Scripts\Activate.ps1
```

### Run in text mode (easiest for debugging)
```powershell
python -m jarvis_core.main --mode text
```

When prompted with `You (text)> `, type a message like:
- "what time is it"
- "hello"
- "exit"

### Expected Output

You should see output like this:

```
Initializing Jarvis Systems...
[TEXT] Text input accepted: what time is it
[DISPATCHER] User (text): what time is it
[DISPATCHER] Time command detected
[DISPATCHER] Time response: The current time is 2:45 PM
[SPEAK] Using backend: eleven
[SPEAK] Calling ElevenLabs API...
```

### Understanding the [SPEAK] Logs

These logs tell you which TTS backend is being used:

- `[SPEAK] Using backend: eleven` → Trying ElevenLabs
- `[SPEAK] Using backend: edge` → Trying edge-tts
- `[SPEAK] Using backend: pyttsx3` → Using local offline TTS (SHOULD PRODUCE SOUND)

## Troubleshooting Output "Mute" Issue

### Step 1: Verify you see [SPEAK] logs

If you DON'T see any `[SPEAK]` output at all, there's a critical error early in initialization. Check:
- Python is installed correctly
- Virtual environment is activated
- All dependencies are installed (`pip install -r requirements.txt`)

### Step 2: Check which backend is selected

Run the test script:
```powershell
python test_speak.py
```

This will show you exactly which backend is being used.

### Step 3: Verify pyttsx3 can produce sound

If the logs show `[SPEAK] Using backend: pyttsx3`, it should produce sound. If you hear nothing:

1. Check Windows Volume Mixer - make sure the Python process isn't muted
2. Try running in offline mode to force pyttsx3:
   ```powershell
   python -m jarvis_core.main --mode text --offline
   ```
3. Verify pyttsx3 with this test:
   ```powershell
   python -c "import pyttsx3; engine = pyttsx3.init(); engine.say('test'); engine.runAndWait(); print('Done')"
   ```

### Step 4: If using ElevenLabs

If logs show `[SPEAK] Calling ElevenLabs API...` but then error:

1. Verify `.env` file has:
   ```
   ELEVENLABS_API_KEY=your_actual_key_here
   ELEVENLABS_VOICE=21m00Tcm4TlvDq8ikWAM
   ```
2. Check your API key is valid (go to elevenlabs.io)
3. Verify you have API credits

### Step 5: Verify audio system works

Test Windows audio directly:
```powershell
[System.IO.File]::ReadAllBytes("C:\Windows\Media\tada.wav") | Out-Null
```

Or test pygame playback:
```powershell
python -c "import pygame; pygame.mixer.init(); print('Pygame audio ready')"
```

## Detailed Logging Output

### Text Mode with Full Logging

Run in text mode to see every step:
```powershell
python -m jarvis_core.main --mode text 2>&1 | Tee-Object -FilePath debug.log
```

This captures all output to both console AND `debug.log` file.

### Expected Log Flow

```
Initializing Jarvis Systems...              ← Main initialized
[TEXT] Text input accepted: hello           ← Your input captured
[DISPATCHER] User (text): hello             ← Input routed to dispatcher
[DISPATCHER] Routing to Brain for response... ← Brain is processing
[DISPATCHER] Brain response: Hello! How can I help?  ← Brain generated response
[SPEAK] Using backend: [BACKEND]            ← TTS backend selected
[SPEAK] Calling ElevenLabs API... (if 11)   ← API call initiated
[SPEAK] ElevenLabs response status: 200     ← API succeeded
[SPEAK] Playing MP3: ...                    ← Audio playback started
[SPEAK] MP3 playback initiated              ← OS audio player started
Jarvis: Hello! How can I help?              ← Displayed to console
```

## Audio Backend Priority

1. **ElevenLabs** (highest quality, internet required, requires API key)
   - Status: `[SPEAK] ElevenLabs response status: 200` = working
   - Status: `[SPEAK] ElevenLabs error:` = check API key in .env

2. **edge-tts** (free, internet required, auto-selected if ElevenLabs unavailable)
   - Status: `[SPEAK] Using edge-tts backend`
   - Should auto-play MP3 file

3. **pyttsx3** (local/offline, always available, SHOULD ALWAYS PRODUCE SOUND)
   - Status: `[SPEAK] Using pyttsx3 backend`
   - Status: `[SPEAK] pyttsx3 speaking...` = engine is processing
   - Status: `[SPEAK] pyttsx3 speech completed` = engine finished
   - If you don't hear sound: check Windows audio volume/mute settings

## Force Offline Mode

To force pyttsx3 (local offline TTS):
```powershell
python -m jarvis_core.main --mode text --offline
```

This completely skips ElevenLabs and edge-tts, ensuring pyttsx3 is used.

## Memory & Persistence

### Add a memory
```powershell
python -m jarvis_core.main --remember "I like Python programming"
```

### List memories
```powershell
python -m jarvis_core.main --list-memories
```

### Clear a memory
```powershell
python -m jarvis_core.main --forget "Python"
```

## Common Issues

### "Output is muted"
→ Check Windows Volume Mixer, verify pyttsx3 with `--offline` mode

### "No [SPEAK] logs appear"
→ Check virtual environment is activated, all dependencies installed

### "ElevenLabs error: 401"
→ API key in `.env` is wrong or expired

### "ElevenLabs error: 429"
→ Rate limited, try again later or use `--offline` mode

### "pyttsx3 error: No module named 'pyttsx3'"
→ Run `pip install pyttsx3`

## Contact & Support

If issues persist:
1. Check the debug log: look for `[SPEAK]` prefixed messages
2. Try offline mode: `--offline` flag forces pyttsx3
3. Try text mode: `--mode text` is easier to debug than voice mode
4. Review the log file for the exact error message

---
Generated for troubleshooting Jarvis audio output issues.
