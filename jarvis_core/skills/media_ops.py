import base64
import os
import subprocess
import tempfile
from typing import Optional

import requests

from .. import config

# Default music path requested by the user
DEFAULT_MUSIC_PATH = r"C:\Users\Davin\VS project\jarvis\JARVIS START UP - Adrian Martinez.mp3"


class MediaSkills:
    def __init__(self):
        pass

    def play_music(self, path: Optional[str] = None):
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

    def generate_sun_image(self, style: Optional[str] = None):
        """Generate a sun-themed image using the OpenRouter image API."""
        prompt = (
            "A bright, glowing sun rising over a dramatic landscape with vivid colors, "
            "high detail, cinematic lighting, and a warm atmosphere."
        )
        if style:
            prompt += f" Rendered in {style} style."

        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_IMAGE_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://jarvis.local",
            "X-OpenRouter-Title": "Jarvis Image Generator",
        }

        body = {
            "model": "openai/gpt-image-1",
            "prompt": prompt,
            "size": "1024x1024",
        }

        urls_to_try = [
            "https://openrouter.ai/api/v1/images/generations",
            "https://openrouter.ai/api/v1/images/generate",
            "https://openrouter.ai/api/v1/images",
        ]

        for url in urls_to_try:
            try:
                resp = requests.post(url, json=body, headers=headers, timeout=30)
                if resp.status_code != 200:
                    print(f"[IMAGE] OpenRouter image generation failed ({url}): {resp.status_code} {resp.text}")
                    continue

                data = resp.json()
                if not data:
                    continue

                image_info = data.get("data")
                if isinstance(image_info, list) and image_info:
                    image_obj = image_info[0]
                    image_url = image_obj.get("url") or image_obj.get("image_url")
                    b64_json = image_obj.get("b64_json") or image_obj.get("base64")

                    if image_url:
                        return f"Sun image generated: {image_url}"
                    if b64_json:
                        image_bytes = base64.b64decode(b64_json)
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        with open(tmp.name, "wb") as f:
                            f.write(image_bytes)
                        return f"Sun image saved to: {tmp.name}"

                # Some OpenRouter image responses use `output` or `image_url`
                if "output" in data:
                    output = data["output"]
                    if isinstance(output, list) and output:
                        first = output[0]
                        if isinstance(first, str) and first.startswith("http"):
                            return f"Sun image generated: {first}"

            except Exception as e:
                print(f"[IMAGE] OpenRouter request error ({url}): {e}")

        return "Sun image generation failed. Check the OpenRouter key or internet connection."
