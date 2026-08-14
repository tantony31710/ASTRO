#!/usr/bin/env python3
"""
JARVIS Core Engine Loop (Phase 4).

Separate entry point from main.py on purpose: main.py runs the vault's
batch pipelines once and exits (storage check -> cleanup -> media ->
weights). This file runs the assistant as a continuous listen/act/speak
loop. Run whichever one fits what you're doing:

    python main.py     # one-shot pipeline run
    python jarvis.py    # interactive assistant loop

Loop shape:
    listen() -> handle_intent() -> [matched: run tool | unmatched: ask_llm()] -> speak()

Startup runs the same boot checks main.py does (disk check, scratch
cleanup) so the assistant reports vault health as soon as it wakes up.

Keys and config are loaded automatically from a `.env` file in this
directory (see `.env.example`) — importing `src.utils.llm` triggers the
load, so no manual env-var dance is needed.
"""
import os

from src.utils.storage import check_disk_space, cleanup_scratch_dir
from src.utils.tools import handle_intent, is_exit_command
from src.utils.llm import ask_llm
from src.utils.voice import listen, speak


def boot_check() -> str:
    free_gb = check_disk_space(".")
    cleanup_scratch_dir()
    if free_gb < 10.0:
        return f"Vault online. Warning — only {free_gb:.1f} GB free."
    return f"Vault online. {free_gb:.1f} GB free."


def run_once(text: str) -> str:
    """Processes a single utterance/command and returns the response text. No I/O side effects beyond the tool itself — used by both the loop and tests."""
    intent = handle_intent(text)
    if intent["matched"]:
        return intent["result"]
    return ask_llm(text)


def main_loop():
    speak(boot_check())

    while True:
        text = listen("Say a command, or type it:")
        if not text:
            continue
        if is_exit_command(text):
            speak("Going to sleep.")
            break
        response = run_once(text)
        speak(response)


def wake_loop():
    """
    Wake-word mode: JARVIS idles listening for "jarvis" (configurable via
    JARVIS_WAKE_WORD), then speaks, takes a full command, answers, and
    returns to ambient listening. Driven by voice.listen_loop() — see that
    docstring for the guard's degradation policy.

    Usage:
        JARVIS_MODE=wake python jarvis.py      # wake-word mode
        python jarvis.py                       # classic prompt mode
    """
    from src.utils.voice import listen_loop

    speak(boot_check())
    listen_loop(run_once)


if __name__ == "__main__":
    try:
        if os.environ.get("JARVIS_MODE", "").lower() == "wake":
            wake_loop()
        else:
            main_loop()
    except KeyboardInterrupt:
        speak("Interrupted. Shutting down.")
