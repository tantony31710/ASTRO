"""
Persistent Conversation Memory.

A lightweight, dependency-free memory so JARVIS remembers what was said
earlier in the session and across restarts — no Honcho/Claude API needed.

Design:
- Memory lives in ``02_build_cache/conversation_memory.json`` (inside the
  existing cache zone so cleanup routines can sweep it).
- Each turn appends {"role": "you"|"jarvis", "text": ..., "ts": ...}.
- The sliding window keeps the last MAX_TURNS entries in memory for
  history-aware prompts; older turns persist on disk indefinitely so you
  can query "what did I ask this morning?"
- get_history_messages() formats the window as LLM chat messages so the
  caller just prepends them before the new user prompt.
"""
import json
import time
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
MEMORY_FILE = VAULT_ROOT / "02_build_cache" / "conversation_memory.json"
MAX_TURNS = 40  # kept in the LLM context window
MAX_STORED = 2000  # max entries kept on disk before trimming

MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load() -> list:
    if not MEMORY_FILE.is_file():
        return []
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list) -> None:
    MEMORY_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")


def record(role: str, text: str) -> None:
    """Record one turn. role is 'you' or 'jarvis'."""
    if not text or not text.strip():
        return
    entries = _load()
    entries.append({"role": role.lower(), "text": text.strip(), "ts": time.time()})
    if len(entries) > MAX_STORED:
        entries = entries[-MAX_STORED // 2:]  # trim, keep the newer half
    _save(entries)


def get_history_messages() -> list:
    """Return the recent sliding window formatted as LLM chat messages."""
    entries = _load()[-MAX_TURNS:]
    return [{"role": "user" if e["role"] == "you" else "assistant", "content": e["text"]} for e in entries]


def recall_recent(limit: int = 5) -> str:
    """Plain-language summary of the last `limit` exchanges — speakable."""
    entries = _load()[-limit * 2:]
    if not entries:
        return "I have no memory of previous conversations."
    parts = []
    for e in entries:
        label = "You said" if e["role"] == "you" else "I said"
        parts.append(f"{label}: {e['text']}")
    return " | ".join(parts)


def clear_memory() -> str:
    _save([])
    return "Conversation memory cleared."
