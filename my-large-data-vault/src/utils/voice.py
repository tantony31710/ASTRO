"""
Voice & Speech Integration (Phase 2).

Both directions degrade gracefully to text if the optional voice deps
aren't installed — the core loop (Phase 4) can run in pure text-CLI mode
with zero extra packages, or in full voice mode once you `pip install`
the extras below.

STT: speech_recognition (Google Web Speech by default) with an optional
     local Whisper backend if `openai-whisper` is installed and
     JARVIS_STT_BACKEND=whisper is set.
TTS: edge-tts (natural, streaming, needs internet) with a pyttsx3
     fallback (fully offline, more robotic) if edge-tts isn't available.

Generated audio clips are written to 02_build_cache/temp_scratch/, which
main.py's cleanup_scratch_dir() already sweeps on boot — no separate
cleanup logic needed here.
"""
import asyncio
import os
import time
from pathlib import Path

SCRATCH_DIR = Path("02_build_cache/temp_scratch")


def listen(prompt: str = "Listening...") -> str:
    """
    Captures one utterance from the microphone and returns transcribed text.
    Falls back to console input() if speech_recognition (or a mic) isn't
    available, so the loop still runs on a machine with no audio setup.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        return input(f"{prompt} (voice deps not installed, type instead) > ")

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print(prompt)
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)
    except Exception as e:
        return input(f"{prompt} (mic unavailable: {e}, type instead) > ")

    backend = os.environ.get("JARVIS_STT_BACKEND", "google")
    try:
        if backend == "whisper":
            return _transcribe_whisper(recognizer, audio)
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"[VOICE] STT failed ({e}), falling back to typed input.")
        return input("> ")


def _transcribe_whisper(recognizer, audio) -> str:
    import whisper
    import tempfile

    model = whisper.load_model("base")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio.get_wav_data())
        tmp_path = tmp.name
    result = model.transcribe(tmp_path)
    os.unlink(tmp_path)
    return result.get("text", "").strip()


def speak(text: str) -> None:
    """
    Speaks `text` aloud. Tries edge-tts (natural voice, needs internet),
    then pyttsx3 (offline), then just prints if neither is installed.
    Audio clips land in the scratch dir so the existing cleanup routine
    handles them automatically.
    """
    if not text:
        return

    try:
        _speak_edge_tts(text)
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"[VOICE] edge-tts failed ({e}), trying offline TTS.")

    try:
        _speak_pyttsx3(text)
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"[VOICE] pyttsx3 failed ({e}).")

    print(f"JARVIS: {text}")


def _speak_edge_tts(text: str) -> None:
    import edge_tts
    import subprocess
    import shutil

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SCRATCH_DIR / f"tts_{int(time.time() * 1000)}.mp3"

    async def _gen():
        communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
        await communicate.save(str(out_path))

    asyncio.run(_gen())
    print(f"JARVIS: {text}")

    player = shutil.which("ffplay") or shutil.which("mpv")
    if player:
        subprocess.run([player, "-nodisp", "-autoexit", str(out_path)] if "ffplay" in player else [player, str(out_path)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _speak_pyttsx3(text: str) -> None:
    import pyttsx3

    print(f"JARVIS: {text}")
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def detect_wake_word(
    keyword: str = "jarvis",
    threshold: float = 0.6,
    timeout: float = 5.0,
) -> bool:
    """
    Listens for a wake-word phrase (default "jarvis") in the microphone and
    returns True when it hears it within `timeout` seconds. This is the
    "ambient guard": speech_recognition in continuous-listen mode with
    ``recognize_google`` (same STT backend as ``listen()``), but only the
    transcript is checked for the keyword — no full command parsing happens
    until the wake word fires, so background chatter is ignored.

    Graceful degradation (same policy as ``listen``):
      - no speech_recognition package        -> console prompt asking to type the wake word
      - no microphone / audio backend error  -> console prompt
      - Google STT can't match anything      -> returns False (keep waiting)

    The wake word itself is matched case-insensitively as a substring with
    basic phonetic tolerance for common misrecognitions (``jarvis`` may
    arrive as ``jervis``, ``garvis``, ``jarvis sir`` …). Configure
    ``JARVIS_WAKE_WORD`` and ``JARVIS_WAKE_THRESHOLD`` in .env to change
    the keyword and looseness of the match.
    """
    import os
    import re

    keyword = (os.environ.get("JARVIS_WAKE_WORD") or keyword).strip().lower()
    threshold = float(os.environ.get("JARVIS_WAKE_THRESHOLD", threshold))
    tolerance = {
        "jarvis": ["jervis", "garvis", "jarvis sir", "jeff"],
    }.get(keyword, [])
    patterns = [re.compile(r"\b" + re.escape(keyword) + r"\b", re.I)] + [
        re.compile(r"\b" + re.escape(t) + r"\b", re.I) for t in tolerance
    ]

    try:
        import speech_recognition as sr
    except ImportError:
        hit = input(f"[WAKE] voice deps not installed — type '{keyword}' to wake > ")
        return any(p.search(hit or "") for p in patterns)

    recognizer = sr.Recognizer()
    deadline = time.time() + timeout
    # The mic can be temporarily busy right after a previous STT session
    # (Windows holds it for a moment). Retry opening a few times before
    # giving up — a fresh process is unaffected, but the ambient guard
    # calls this in a loop next to other listeners.
    source = None
    for attempt in range(3):
        try:
            source = sr.Microphone()
            break
        except Exception:
            time.sleep(1.0)
    if source is None:
        print(f"[WAKE] mic still unavailable, falling back to typed input.")
        hit = input(f"[WAKE] type '{keyword}' to wake > ")
        return any(p.search(hit or "") for p in patterns)
    try:
        with source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            while time.time() < deadline:
                remaining = max(0.5, deadline - time.time())
                try:
                    audio = recognizer.listen(source, timeout=remaining, phrase_time_limit=8)
                except sr.WaitTimeoutError:
                    continue
                try:
                    transcript = recognizer.recognize_google(audio).lower()
                except sr.UnknownValueError:
                    continue
                if any(p.search(transcript) for p in patterns):
                    return True
                # Wake word not heard yet — keep listening until the deadline.
                continue
    except Exception as e:
        print(f"[WAKE] mic unavailable ({e}), falling back to typed input.")
        hit = input(f"[WAKE] type '{keyword}' to wake > ")
        return any(p.search(hit or "") for p in patterns)

    return False


def listen_loop(callback):
    """
    Ambience loop: repeatedly wait for the wake word, then hand one full
    ``listen()`` utterance to `callback(text)` and speak its return value.
    This is the "Hey Jarvis"-style replacement for the prompt-driven
    ``main_loop`` — no Enter key needed, ever.

    The callback receives the transcribed command and must return the
    response text (speak() happens here so run_once() stays side-effect-free).
    Pass ``callback=None`` to use ``jarvis.run_once``.
    """
    from jarvis import run_once

    callback = callback or run_once
    from src.utils.tools import is_exit_command

    speak("I'm awake. Say my name to get my attention.")
    while True:
        if not detect_wake_word():
            continue
        speak("I'm listening.")
        text = listen()
        if not text:
            continue
        if is_exit_command(text):
            speak("Going to sleep.")
            break
        response = callback(text)
        speak(response)
