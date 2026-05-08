import os
import webbrowser
import platform
import datetime
import subprocess
from typing import Dict


class SystemSkills:
    def __init__(self):
        # Detect the Operating System (Windows, macOS, or Linux)
        self.os_name = platform.system()
        print(f"System Skills loaded for {self.os_name}")

    def open_website(self, url: str):
        """Opens a website in the default browser."""
        if not url.startswith("http"):
            url = f"https://{url}"
        print(f"Opening {url}...")
        webbrowser.open(url)
        return f"Opening {url}"

    def launch_app(self, app_name: str):
        """
        Attempts to open an application.
        Note: Exact app names depend on your OS installed programs.
        """
        if not app_name:
            return "No app specified"

        app_name_key = app_name.lower().replace(" ", "")

        # Mappings: user says -> system command
        app_map = {
            "chrome": "chrome" if self.os_name == "Windows" else "Google Chrome",
            "spotify": "spotify" if self.os_name == "Windows" else "Spotify",
            "calculator": "calc" if self.os_name == "Windows" else "Calculator",
            "notepad": "notepad" if self.os_name == "Windows" else "TextEdit",
            "terminal": "cmd" if self.os_name == "Windows" else "Terminal",
        }

        system_app_name = app_map.get(app_name_key, app_name)

        try:
            if self.os_name == "Windows":
                os.system(f"start {system_app_name}")
            elif self.os_name == "Darwin":  # macOS
                os.system(f"open -a '{system_app_name}'")
            elif self.os_name == "Linux":
                os.system(f"{system_app_name}")

            return f"Opening {app_name}"
        except Exception as e:
            return f"Failed to open {app_name}. Error: {e}"

    def get_time(self):
        """Returns the current time."""
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {now}"

    def run_terminal_command(self, command: str):
        """
        Runs a terminal command and returns the result.
        Use with caution - only run trusted commands.
        """
        if not command:
            return "No command specified"

        try:
            print(f"Running command: {command}")
            # Run the command and capture output
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode == 0:
                if output:
                    return f"Command executed successfully: {output}"
                else:
                    return "Command executed successfully (no output)"
            else:
                if error:
                    return f"Command failed: {error}"
                else:
                    return f"Command failed with return code {result.returncode}"
                    
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Failed to run command: {e}"


# Module-level instance for simple routing
_system_skills = SystemSkills()


def execute_function(payload: Dict):
    """Backward-compatible router that calls SystemSkills methods based on payload.

    Expected payload keys:
    - `tool`: qualified tool name like 'system_ops.open_app' or 'system_ops.launch_app'
    - other keys: `name`, `url`, `path`, etc.
    """
    tool = payload.get("tool", "")

    # Launch an application
    if tool.endswith("open_app") or tool.endswith("launch_app") or tool.endswith("launch_app"):
        name = payload.get("name") or payload.get("app") or ""
        return _system_skills.launch_app(name)

    # Open a website
    if "website" in tool or "open_url" in tool or "open_website" in tool:
        url = payload.get("url") or payload.get("name") or ""
        return _system_skills.open_website(url)

    # Get time
    if tool.endswith("get_time") or tool.endswith("time"):
        return _system_skills.get_time()

    # Run terminal command
    if tool.endswith("run_terminal_command") or tool.endswith("run_command"):
        command = payload.get("command") or payload.get("cmd") or ""
        return _system_skills.run_terminal_command(command)

    return f"Unknown tool: {tool}"
