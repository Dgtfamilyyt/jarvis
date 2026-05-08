@echo off
REM Launch Jarvis from the repository root with a single command.
cd /d "%~dp0"
"%~dp0\.venv\Scripts\python.exe" -m jarvis_core.main --mode both
