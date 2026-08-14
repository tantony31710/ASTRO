#!/usr/bin/env python3
"""
Voice Stack Smoke Test.

Run once after installing the extras to confirm every layer of the voice
stack actually works on YOUR machine (mic, STT, TTS, wake-word guard).
Each step is independent — one failing layer doesn't stop the rest.

    python test_voice_stack.py

What it tests:
  1. Dependency imports: speech_recognition, PyAudio, edge-tts, pyttsx3
  2. Microphone detection: can PyAudio open the default input device?
  3. STT: records one utterance and prints the transcript
  4. TTS: speaks a test phrase (edge-tts if online, pyttsx3 otherwise)
  5. Wake-word guard: detects_wake_word() with the console fallback so you
     can type "jarvis" (or your configured keyword) and see it fire
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.voice import detect_wake_word, listen, speak

print("=" * 60)
print("JARVIS VOICE STACK SMOKE TEST")
print("=" * 60)

# 1. Dependency check
layers = [
    ("speech_recognition", "STT (Google Web Speech / Whisper)"),
    ("pyaudio", "microphone access"),
    ("edge_tts", "online TTS (natural voice, needs internet)"),
    ("pyttsx3", "offline TTS (robotic)"),
]
for mod, label in layers:
    try:
        __import__(mod)
        print(f"[OK]   {mod:22s} — {label}")
    except ImportError:
        print(f"[MISS] {mod:22s} — {label} (pip install {mod})")

# 2. Microphone detection
print("-" * 60)
print("Microphone check:")
try:
    import speech_recognition as sr

    r = sr.Recognizer()
    with sr.Microphone() as mic:
        info = mic.__class__.__name__
        print(f"[OK]   default microphone opened ({info})")
        print("       Calibrating ambient noise — stay quiet for a second...")
        r.adjust_for_ambient_noise(mic, duration=1.0)
        print(f"[OK]   ambient calibration passed")
except ImportError:
    print("[SKIP] speech_recognition not installed — falling back to typed input.")
except Exception as e:
    print(f"[FAIL] microphone unavailable: {e}")
    print("       Voice will fall back to typed console input.")

# 3. STT round trip
print("-" * 60)
transcript = listen("Say anything (e.g. 'what time is it'):")
print(f"[STT]  transcript: {transcript!r}")
print(f"[{'OK' if transcript else 'EMPTY'}]    STT round trip")

# 4. TTS
print("-" * 60)
print("[TTS]  Speaking a test phrase — you should hear 'Hello, this is Jarvis.'")
speak("Hello, this is Jarvis.")
print("[OK]   TTS completed")

# 5. Wake-word guard
print("-" * 60)
keyword = os.environ.get("JARVIS_WAKE_WORD", "jarvis")
print(f"[WAKE] Say or type '{keyword}' (timeout 8 s):")
start = time.time()
awake = detect_wake_word(timeout=8)
took = time.time() - start
print(f"[{'OK' if awake else 'TIMEOUT'}]   wake word {'detected' if awake else 'not detected'} in {took:.1f}s")

print("=" * 60)
print("Done. If everything above is [OK], run:")
print(f"    JARVIS_MODE=wake python jarvis.py   (or tray_jarvis.pyw for the tray app)")
