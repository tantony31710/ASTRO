#!/usr/bin/env python3
"""
JARVIS Windows Tray App.

A borderless system-tray (notification-area) launcher for JARVIS on
Windows. It keeps JARVIS awake in the background as a long-running
process, opens the vault dashboard in the default browser on demand,
and can start/stop the assistant loop — all without a visible terminal
window.

Requirements (Windows):
    pip install pystray Pillow

Install:
    1. Put `tray_jarvis.pyw` next to `jarvis.py` in my-large-data-vault/.
    2. Copy my-large-data-vault/.env.example to .env and fill in keys.
    3. Run with pythonw (no console window):
           pythonw my-large-data-vault\tray_jarvis.pyw
    4. Add a shortcut to the file in shell:startup for boot-time launch.

Run order on this machine (from the repo root):
    uvicorn api.main:app --port 8000        # the API the dashboard talks to
    cd frontend && npm run dev              # React dashboard (vite, :5173)
    pythonw my-large-data-vault\tray_jarvis.pyw   # tray app + assistant loop
"""
import sys
import threading
import webbrowser
from pathlib import Path

VAULT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(VAULT_DIR))
sys.path.insert(0, str(VAULT_DIR.parent))

DASHBOARD_URL = "http://localhost:5173"


def _run_assistant_loop():
    """The JARVIS listen/act/speak loop, running in its own thread."""
    from jarvis import main_loop

    main_loop()


def _ensure_api_server():
    """Start the FastAPI backend if it isn't reachable yet."""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", 8000))
        return  # already up
    except OSError:
        pass
    finally:
        sock.close()

    import subprocess

    repo_root = VAULT_DIR.parent
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8000"],
        cwd=str(repo_root),
        creationflags=0x08000000 if sys.platform == "win32" else 0,  # CREATE_NO_WINDOW
    )


def build_tray():
    import pystray
    from PIL import Image, ImageDraw

    # A simple 64x64 blue circle icon (swap for a real .ico if you like).
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill=(45, 90, 170, 255))

    def _on_start(icon=None, item=None):
        threading.Thread(target=_run_assistant_loop, daemon=True).start()

    def _on_dashboard(icon=None, item=None):
        webbrowser.open(DASHBOARD_URL)

    def _on_quit(icon=None, item=None):
        icon.stop()
        sys.exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("JARVIS awake (start loop)", _on_start),
        pystray.MenuItem("Open dashboard", _on_dashboard),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit JARVIS", _on_quit),
    )
    return pystray.Icon("JARVIS", img, "JARVIS — ASTRO Vault", menu)


if __name__ == "__main__":
    _ensure_api_server()
    # Start the assistant loop immediately (voice falls back to text CLI
    # if no microphone is attached). The tray icon stays available to
    # open the dashboard or quit.
    threading.Thread(target=_run_assistant_loop, daemon=True).start()
    build_tray().run()
