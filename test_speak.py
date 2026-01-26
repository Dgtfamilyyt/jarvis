#!/usr/bin/env python3
"""
Simple test script to debug TTS output.
Run: python test_speak.py
"""

import sys
sys.path.insert(0, r'c:\Users\Davin\VS project\jarvis')

from jarvis_core.core.speak import Speaker

print("=" * 60)
print("Testing Speaker (TTS) Systems")
print("=" * 60)

# Test 1: Auto backend (should detect what's available)
print("\n[TEST 1] Auto backend initialization:")
speaker_auto = Speaker(offline=False)
print(f"Selected backend: {speaker_auto.backend}")

# Test 2: Attempt to speak
print("\n[TEST 2] Attempting to speak with auto backend:")
try:
    speaker_auto.speak_output("Hello, this is a test of the text to speech system.")
    print("[TEST 2] speak_output() completed")
except Exception as e:
    print(f"[TEST 2] Exception in speak_output: {e}")

# Test 3: Offline mode (pyttsx3 only)
print("\n[TEST 3] Offline mode (pyttsx3 only):")
speaker_offline = Speaker(offline=True)
print(f"Selected backend: {speaker_offline.backend}")

print("\n[TEST 3B] Attempting to speak in offline mode:")
try:
    speaker_offline.speak_output("This is offline mode, using local text to speech.")
    print("[TEST 3B] speak_output() completed")
except Exception as e:
    print(f"[TEST 3B] Exception in speak_output: {e}")

print("\n" + "=" * 60)
print("Test complete. Check above for [SPEAK] prefixed messages.")
print("=" * 60)
