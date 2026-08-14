"""
Tool Registry & Intent Router (Phase 1).

A small, dependency-free command router: JARVIS's "hands." Text comes in,
gets matched against a registry of keyword-triggered tools, and a tool
function runs. Anything that doesn't match a known tool is reported as
unmatched so the caller (the core loop, or the API) can fall back to the
LLM (Phase 3).

Design choices:
- Keyword matching, not NLP — cheap, deterministic, debuggable. An LLM
  intent classifier can replace this later without changing the interface
  (handle_intent still returns the same shape).
- Each tool is (name, keywords, handler, description). Handlers take no
  args and return a plain string result — easy to speak (Phase 2) or
  return as JSON (Phase 5).
"""
import platform
import subprocess
import webbrowser
from urllib.parse import quote
from dataclasses import dataclass, field
SEARCH_QUERY = ""  # trailing text after a matched keyword (e.g. search query)
from typing import Callable, Optional

from src.utils.storage import get_disk_usage, get_zone_sizes, cleanup_scratch_dir
from src.pipelines.process_media import process_media_batch, list_raw_videos, list_proxies
from src.pipelines.train_model import list_model_weights


@dataclass
class Tool:
    name: str
    keywords: list
    handler: Callable[[], str]
    description: str = ""


def _tool_check_disk() -> str:
    d = get_disk_usage(".")
    warning = " Low disk space — proceed with caution." if d["low_space_warning"] else ""
    return (
        f"{d['free_gb']} GB free of {d['total_gb']} GB "
        f"({d['percent_used']}% used).{warning}"
    )


def _tool_zone_report() -> str:
    zones = get_zone_sizes(".")
    parts = [f"{z['zone']}: {z['size_gb']} GB" for z in zones]
    return "Vault zones — " + ", ".join(parts)


def _tool_clean_cache() -> str:
    result = cleanup_scratch_dir()
    if result["cleared_count"] == 0:
        return "Scratch directory is already clean."
    freed_mb = round(result["freed_bytes"] / (1024 * 1024), 1)
    return f"Cleared {result['cleared_count']} file(s), freed {freed_mb} MB."


def _tool_transcode() -> str:
    raw = list_raw_videos()
    pending = [v for v in raw if not v["proxy_exists"]]
    if not pending:
        return "No raw footage is waiting on a proxy."
    result = process_media_batch()
    return f"Transcoded {result['processed']}/{result['total']} file(s). Failures: {result['failures'] or 'none'}."


def _tool_list_proxies() -> str:
    proxies = list_proxies()
    if not proxies:
        return "No proxies have been generated yet."
    return f"{len(proxies)} proxy file(s): " + ", ".join(p["name"] for p in proxies)


def _tool_list_weights() -> str:
    weights = list_model_weights()
    if not weights:
        return "No model weight files found in the vault."
    parts = [f"{w['name']} ({w['size_mb']} MB)" for w in weights]
    return f"{len(weights)} weight file(s): " + ", ".join(parts)


def _tool_open_browser() -> str:
    webbrowser.open("http://localhost:5173")
    return "Opening the vault dashboard."


def _tool_system_stats() -> str:
    return _tool_check_disk() + " " + _tool_zone_report()


def _tool_search_google() -> str:
    """Opens Google — the trailing query text is supplied by handle_intent
    via SEARCH_QUERY (set per-call). Pure webbrowser, no extra deps."""
    query = quote(SEARCH_QUERY or "jarvis assistant")
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return "Opening Google search."


def _tool_open_app(name: str = "") -> str:
    """Open an application by keyword-nicknamed name ('notepad', 'calculator')."""
    known = {
        "notepad": "notepad.exe", "calculator": "calc.exe", "paint": "mspaint.exe",
        "explorer": "explorer.exe", "task manager": "taskmgr.exe",
        "word": "winword.exe", "excel": "excel.exe", "powerpoint": "powerpnt.exe",
        "settings": "ms-settings:", "control panel": "control", "clock": "clock.exe",
    }
    app = known.get(name.lower().strip(), name)
    return open_application(app)


def open_application(app_name: str) -> str:
    """
    Best-effort local app launcher. Windows uses `start`, macOS uses `open`,
    Linux uses `xdg-open`. Kept separate from the registry since it needs an
    argument (the app name) rather than being a bare keyword trigger.
    """
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=False)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", app_name])
        else:
            subprocess.Popen(["xdg-open", app_name])
        return f"Launching {app_name}."
    except Exception as e:
        return f"Couldn't launch {app_name}: {e}"


# Order matters only in that the first keyword match wins if a phrase could
# match two tools — keep more specific phrases above more general ones.
TOOL_REGISTRY: list = [
    Tool("clean_cache", ["clean cache", "clear scratch", "clear cache"], _tool_clean_cache,
         "Deletes temp files in 02_build_cache/temp_scratch."),
    Tool("transcode", ["transcode", "generate proxies", "make proxies"], _tool_transcode,
         "Generates 720p proxies for pending raw footage."),
    Tool("list_proxies", ["list proxies", "show proxies"], _tool_list_proxies,
         "Lists already-generated proxies."),
    Tool("list_weights", ["list weights", "list models", "model weights"], _tool_list_weights,
         "Lists model weight assets and sizes."),
    Tool("zone_report", ["zone report", "vault zones", "zone sizes"], _tool_zone_report,
         "Reports size on disk per vault zone."),
    Tool("check_disk", ["disk space", "check disk", "free space"], _tool_check_disk,
         "Reports free/used disk space."),
    Tool("system_stats", ["system stats", "system status", "status report"], _tool_system_stats,
         "Combined disk + zone report."),
    Tool("open_dashboard", ["open dashboard", "open browser", "show dashboard"], _tool_open_browser,
         "Opens the vault dashboard in the default browser."),
    Tool("open_notepad", ["open notepad", "launch notepad", "start notepad"], lambda: _tool_open_app("notepad"),
         "Launches Windows Notepad."),
    Tool("open_calc", ["open calculator", "launch calculator"], lambda: _tool_open_app("calculator"),
         "Launches the Windows Calculator."),
    Tool("search_google", ["search google", "google search", "search the web for"], _tool_search_google,
         "Opens a Google search in the default browser with the trailing query text."),
    Tool("open_task_manager", ["open task manager", "show running apps"], lambda: _tool_open_app("task manager"),
         "Opens Windows Task Manager."),
    Tool("open_settings", ["open settings", "windows settings"], lambda: _tool_open_app("settings"),
         "Opens Windows Settings."),
]

EXIT_KEYWORDS = ["shutdown", "exit", "quit", "go to sleep", "goodnight"]


def is_exit_command(text: str) -> bool:
    lowered = text.lower().strip()
    return any(kw in lowered for kw in EXIT_KEYWORDS)


def handle_intent(text: str) -> dict:
    """
    Matches free text against the tool registry.

    Returns {"matched": True, "tool": name, "result": str} on a hit, or
    {"matched": False, "text": text} so the caller can fall back to the LLM.
    """
    lowered = text.lower().strip()
    if not lowered:
        return {"matched": False, "text": text}

    # Allow keyword tools that need trailing text (e.g. a search query) to
    # see the part of the command after their keyword match. Leading filler
    # words ("for", "about") after the keyword are stripped.
    global SEARCH_QUERY
    SEARCH_QUERY = ""
    _FILLER = ("for ", "about ", "on ")
    for tool in TOOL_REGISTRY:
        for kw in tool.keywords:
            if kw in lowered:
                tail = lowered.split(kw, 1)[1].strip()
                for f in _FILLER:
                    if tail.startswith(f):
                        tail = tail[len(f):].strip()
                if tail:
                    SEARCH_QUERY = tail
                break

    for tool in TOOL_REGISTRY:
        if any(kw in lowered for kw in tool.keywords):
            try:
                result = tool.handler()
            except Exception as e:
                result = f"Tool '{tool.name}' failed: {e}"
            return {"matched": True, "tool": tool.name, "result": result}

    return {"matched": False, "text": text}


def list_tools() -> list:
    """Returns tool metadata for the dashboard's /api/status or a help command."""
    return [{"name": t.name, "keywords": t.keywords, "description": t.description} for t in TOOL_REGISTRY]
