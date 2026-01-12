import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
MP3_NAME = "JARVIS START UP - Adrian Martinez.mp3"
MP3_PATH = PROJECT_ROOT / MP3_NAME

STARTUP_DIR = Path(os.getenv("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
BAT_NAME = "start_jarvis.bat"
BAT_PATH = STARTUP_DIR / BAT_NAME

PY_EXE = sys.executable

bat_contents = f"""@echo off
REM Play startup sound and launch Jarvis
start "" "{MP3_PATH}"
REM Wait a couple seconds for the sound to start
ping -n 3 127.0.0.1 > nul
REM Launch Jarvis (opens in new window)
start "" "{PY_EXE}" -m jarvis_core.main
exit
"""


def install():
    if not MP3_PATH.exists():
        print(f"MP3 not found at {MP3_PATH}. Please ensure the file exists.")
        return

    if not STARTUP_DIR.exists():
        print(f"Startup folder not found: {STARTUP_DIR}")
        return

    try:
        with open(BAT_PATH, "w", encoding="utf-8") as f:
            f.write(bat_contents)
        print(f"Created startup batch at: {BAT_PATH}")
    except Exception as e:
        print(f"Failed to write batch file: {e}")


if __name__ == "__main__":
    install()
