# Jarvis Quick Reference

## Running Jarvis

### Text Mode (Recommended for testing)
```powershell
python -m jarvis_core.main --mode text
```
Type your message when prompted with `You (text)> `

### Voice Mode
```powershell
python -m jarvis_core.main --mode voice
```
Speak after the listening prompt

### Both Modes (Voice + Text Concurrent)
```powershell
python -m jarvis_core.main --mode both
```

### Offline Mode (No internet required - local TTS only)
```powershell
python -m jarvis_core.main --mode text --offline
```

## Memory Operations

### Add to Memory
```powershell
python -m jarvis_core.main --remember "Some fact to remember"
```

### View Memories
```powershell
python -m jarvis_core.main --list-memories
```

### Forget a Memory
```powershell
python -m jarvis_core.main --forget "keyword"
```

### Consolidate Old Memories
```powershell
python -m jarvis_core.main --consolidate --keep 200
```

## Diagnostic Commands

### Comprehensive System Check
```powershell
python diagnose.py
```
Checks all modules, configuration, and runs actual TTS tests

### Quick Speaker Test
```powershell
python test_speak.py
```
Tests the Speaker class directly

### Run with Output Capture
```powershell
python -m jarvis_core.main --mode text 2>&1 | Tee-Object -FilePath debug.log
```
Saves all output to `debug.log` file

## Understanding Log Prefixes

| Prefix | Meaning | Module |
|--------|---------|--------|
| `[VOICE]` | Voice input worker | main.py |
| `[TEXT]` | Text input worker | main.py |
| `[DISPATCHER]` | Command routing | main.py |
| `[SPEAK]` | Text-to-speech output | speak.py |
| `Jarvis:` | Assistant response | speak.py |

## Common Commands to Try

- "what time is it?" → Get current time
- "hello" → General greeting
- "open google" → Open website
- "exit" or "goodbye" → Close assistant
- "remember I like coffee" → Save to memory
- "what do you remember about me?" → Retrieve memories

## Troubleshooting

### No Audio Output
1. Check Windows Volume Mixer (Python might be muted)
2. Try offline mode: `--offline` flag
3. Run diagnostic: `python diagnose.py`
4. Check system volume and speaker connection

### No Log Output
1. Ensure virtual environment is activated
2. Check all dependencies: `pip install -r requirements.txt`
3. Verify Python is installed

### API Errors (ElevenLabs)
1. Check `.env` file has `ELEVENLABS_API_KEY`
2. Verify API key is valid and has credits
3. Use `--offline` to skip ElevenLabs

### Ollama Not Running
- Jarvis can still speak (TTS works)
- Brain responses will fail unless Ollama is running
- Start Ollama: `ollama serve`

## File Structure

```
jarvis/
├── jarvis_core/
│   ├── main.py                 # Main entry point
│   ├── config.py               # Configuration
│   ├── core/
│   │   ├── listen.py           # Speech-to-text
│   │   └── speak.py            # Text-to-speech
│   ├── brain/
│   │   └── llm_client.py        # LLM + Memory
│   └── skills/
│       ├── system_ops.py        # System commands
│       ├── weather_ops.py       # Weather info
│       ├── calculator_ops.py    # Math & units
│       ├── file_ops.py          # File operations
│       ├── reminder_ops.py      # Reminders
│       ├── scraper_ops.py       # Web scraping
│       └── knowledge_ops.py     # Wikipedia, news, etc.
├── test_speak.py               # Speaker test
├── diagnose.py                 # Diagnostic tool
├── DIAGNOSTIC_GUIDE.md         # Troubleshooting
├── OUTPUT_FIX_SUMMARY.md       # What was fixed
└── .env                        # Configuration (API keys)
```

## Setup Checklist

- [ ] Python 3.13 installed
- [ ] Virtual environment created: `.venv`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file created with necessary API keys
- [ ] Ollama running (if you want brain responses): `ollama serve`
- [ ] FFmpeg installed (for audio conversion)
- [ ] Windows audio working (test with system sounds)

## Support

For detailed troubleshooting, see:
- `DIAGNOSTIC_GUIDE.md` - Complete troubleshooting guide
- `OUTPUT_FIX_SUMMARY.md` - What was fixed and how
- Run `python diagnose.py` for automated system check

---
Last Updated: 2024
Quick Reference for Jarvis Voice Assistant
