import os
import subprocess
from typing import Optional

# Default music path requested by the user
DEFAULT_MUSIC_PATH = r"C:\Users\Davin\VS project\jarvis\JARVIS START UP - Adrian Martinez.mp3"


def play_music(path: Optional[str] = None):
    """Play a music file. On Windows this uses `os.startfile` to open the file
    with the default media player. Returns a short status message.
    """
    if path is None:
        path = DEFAULT_MUSIC_PATH

    if not os.path.exists(path):
        return f"File not found: {path}"

    try:
        if os.name == "nt":
            os.startfile(path)
            return f"Playing: {path}"

        # Fallback for POSIX systems
        subprocess.Popen(["xdg-open", path])
        return f"Playing: {path}"

    except Exception as e:
        return f"Failed to play {path}: {e}"
