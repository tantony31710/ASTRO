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
