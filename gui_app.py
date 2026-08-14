"""ASTRO Local AI Desktop — always-on desktop assistant.

A standalone desktop window (customtkinter, no browser, no terminal needed)
that drives the full JARVIS brain: intent routing, local Llama-3 answers,
and spoken replies. Wake-word activation happens in the background — say
"Jarvis" into the mic and the window activates, listens, and speaks.

Run:
    python gui_app.py          # with visible window
    pythonw gui_app.py         # windowless + tray icon (see TrayApp below)

Config comes from my-large-data-vault/.env (LLM backend, wake word, STT) —
add my-large-data-vault to PYTHONPATH or run from the repo root.
"""
import os
import sys
import threading
import time
import traceback
from pathlib import Path

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------------
# Make the vault importable when launched from anywhere (e.g. Desktop
# shortcut, service, startup folder).
# ---------------------------------------------------------------------------
VAULT_CANDIDATES = [
    (Path(__file__).resolve().parent / "my_large_data_vault").as_posix(),  # current name
    (Path(__file__).resolve().parent / "my-large-data-vault").as_posix(),  # legacy name
]
VAULT = next((v for v in VAULT_CANDIDATES if Path(v).is_dir()), "")
if not VAULT:
    # Fallback: search up to three directory levels for the vault folder.
    # Useful when a shortcut or service points at a copy of gui_app.py.
    probe = Path(__file__).resolve().parent
    for _ in range(3):
        probe = probe.parent
        for cand in ("my_large_data_vault", "my-large-data-vault"):
            if (probe / cand).is_dir():
                VAULT = (probe / cand).as_posix()
                break
        if VAULT:
            break
for _p in (VAULT, str(Path(VAULT).parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from my_large_data_vault.src.utils.voice import detect_wake_word, listen, speak  # noqa: E402
    from my_large_data_vault.jarvis import run_once as astro_respond  # noqa: E402
except ImportError:
    raise RuntimeError(
        "ASTRO desktop app: cannot find the vault modules. "
        "Make sure gui_app.py lives in the ASTRO repo root next to the "
        f"my-large-data-vault/ folder (looked at: {VAULT}). "
        "If you copied gui_app.py elsewhere, copy the whole repo instead."
    )

import dotenv  # noqa: E402
dotenv.load_dotenv(Path(VAULT) / ".env", override=False)


def _set_status(app, text: str, color: str) -> None:
    """Thread-safe status update — always call from the UI thread."""
    app.after(0, lambda: app.status_label.configure(text=text, text_color=color))


# ---------------------------------------------------------------------------
# Glowing pulse animation — a soft breathing glow on the status label (and
# mic button) while listening or speaking. Implemented purely with
# tkinter after() timers and text-color cycling, so it works on any Windows
# machine with no extra packages.
# ---------------------------------------------------------------------------
_PULSE_COLORS = ("#00E676", "#00B359", "#009A4C", "#00B359")
_PULSE_INTERVAL_MS = 320


def _start_pulsing(app, text: str, color: str) -> None:
    """Begin the breathing glow for the given status text and accent color."""
    app._pulse_text = text
    app._pulse_color = color
    app._pulse_index = 0
    _pulse_step(app)


def _pulse_step(app) -> None:
    color = _PULSE_COLORS[app._pulse_index % len(_PULSE_COLORS)]
    app._pulse_index += 1
    try:
        app.status_label.configure(text=app._pulse_text, text_color=color)
        if hasattr(app, "mic_btn"):
            app.mic_btn.configure(fg_color=color)
    except Exception:
        pass
    # Keep pulsing only while the widget still exists (app may have closed).
    if getattr(app, "_pulsing", False):
        app.after(_PULSE_INTERVAL_MS, lambda: _pulse_step(app))


def _stop_pulsing(app, text: str, color: str) -> None:
    app._pulsing = False
    try:
        app.status_label.configure(text=text, text_color=color)
        if hasattr(app, "mic_btn"):
            app.mic_btn.configure(fg_color="#1f538d")
    except Exception:
        pass


def _start_speaking_pulse(app) -> None:
    """A second accent color for the speaking state — amber breathing glow."""
    _start_pulsing(app, "Status: Speaking...", "#FFB300")


def _listen_with_retries(attempts: int = 2, extra_timeout: int = 4) -> str:
    """STT with retry: Google's recognizer occasionally returns empty or
    raises on the first attempt (ambient noise, mic warmup). A second pass
    with a longer timeout usually recovers."""
    last_error = None
    for i in range(attempts):
        try:
            text = listen()
            if text and text.strip():
                return text
        except Exception as e:
            last_error = e
        time.sleep(1.0)
    return ""


class AstroDesktopApp(ctk.CTk):
    """Main assistant window.

    Features:
      - text or voice commands (mic button)
      - automatic wake-word guard: say "Jarvis" anytime, the window pops to
        front, listens to the full command, answers, and speaks it aloud
      - live processing indicator and per-message timestamps
      - minimize-to-tray (the window is always reachable; use the tray icon
        to quit)
      - on-top toggle so it stays above other windows while you work
    """

    def __init__(self):
        super().__init__()
        self.title("ASTRO — Local AI Desktop")
        self.geometry("560x640")
        self.minsize(480, 560)

        # ---- header --------------------------------------------------------
        self.header = ctk.CTkLabel(
            self, text="ASTRO AI ASSISTANT",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self.header.pack(pady=(14, 2))

        self.status_label = ctk.CTkLabel(
            self, text="Status: Ready", font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.status_label.pack(pady=(0, 6))

        # ---- controls row --------------------------------------------------
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=12)

        self.tray_var = ctk.BooleanVar(value=False)
        self.on_top_var = ctk.BooleanVar(value=False)

        self.wake_toggle = ctk.CTkSwitch(
            self.ctrl_frame, text="Wake-word listening (say 'Jarvis')",
            command=self.toggle_wake_guard,
        )
        self.wake_toggle.pack(side="left", padx=(0, 12))

        self.on_top_cb = ctk.CTkCheckBox(
            self.ctrl_frame, text="Always on top",
            variable=self.on_top_var, command=self.toggle_on_top,
        )
        self.on_top_cb.pack(side="left")

        self.quit_btn = ctk.CTkButton(
            self.ctrl_frame, text="Minimize to tray", width=140,
            fg_color="#555555", command=self.minimize_to_tray,
        )
        self.quit_btn.pack(side="right")

        # ---- output box ----------------------------------------------------
        self.output_box = ctk.CTkTextbox(self, width=520, height=330)
        self.output_box.pack(pady=10, padx=12)
        self.output_box.insert(
            "0.0",
            "Welcome to ASTRO Local Desktop.\n"
            "Type a command, click the mic, or just say 'Jarvis' — "
            "I'll listen and answer out loud.\n\n",
        )
        self.output_box.configure(state="disabled")

        # ---- input row -----------------------------------------------------
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.entry = ctk.CTkEntry(
            self.input_frame, placeholder_text="Type command here...",
            height=38,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda _e: self.send_text_command())

        self.send_btn = ctk.CTkButton(
            self.input_frame, text="Send", width=72, height=38,
            command=self.send_text_command,
        )
        self.send_btn.pack(side="left", padx=(0, 8))

        self.mic_btn = ctk.CTkButton(
            self.input_frame, text="Mic", width=72, height=38,
            fg_color="#1f538d", hover_color="#2a6db8",
            command=self.start_voice_thread,
        )
        self.mic_btn.pack(side="left")

        self.busy = False
        self._pulsing = False

        # ---- wake-word background guard ------------------------------------
        self.wake_guard = None

    # ------------------------------------------------------------------ text
    def append_text(self, text: str) -> None:
        self.after(0, lambda: self._append(text))

    def _append(self, text: str) -> None:
        self.output_box.configure(state="normal")
        self.output_box.insert("end", text + "\n")
        self.output_box.configure(state="disabled")
        self.output_box.see("end")

    def send_text_command(self) -> None:
        cmd = self.entry.get().strip()
        if not cmd or self.busy:
            return
        self.entry.delete(0, "end")
        threading.Thread(target=self.process, args=(cmd,), daemon=True).start()

    # ------------------------------------------------------------------ voice
    def start_voice_thread(self) -> None:
        if self.busy:
            return
        threading.Thread(target=self.listen_once, daemon=True).start()

    def listen_once(self) -> None:
        _start_pulsing(self, "Status: Listening...", "#00E676")
        try:
            text = _listen_with_retries()
            if text:
                self.append_text(f"You (voice): {text}")
                self.process(text)
            else:
                self.append_text("[System] Didn't catch that — try again.")
        except Exception as e:
            self.append_text(f"[System] Couldn't hear audio clearly: {e}")
        finally:
            _stop_pulsing(self, "Status: Ready", "gray")

    # ------------------------------------------------------------- processing
    def process(self, cmd: str) -> None:
        if self.busy:
            return
        self.busy = True
        self.after(0, lambda: self.send_btn.configure(state="disabled"))
        stamp = time.strftime("%H:%M:%S")
        self.append_text(f"[{stamp}] You: {cmd}")
        _set_status(self, "Status: Thinking...", "#FFC107")
        try:
            response = astro_respond(cmd)
            self.append_text(f"ASTRO: {response}")
            # Speak the reply aloud (voice.py handles missing TTS deps);
            # the status glows amber while audio plays.
            _start_speaking_pulse(self)
            threading.Thread(target=lambda: (speak(response), self.after(0, lambda: None)), daemon=True).start()
            # Stop the speaking glow a moment after the call returns. edge-tts
            # is synchronous, so schedule the stop after the speak thread.
            threading.Thread(target=self._delayed_stop_speaking, daemon=True).start()
        except Exception as e:
            self.append_text(f"[System] Error: {e}")
            traceback.print_exc()
        finally:
            self.busy = False
            _set_status(self, "Status: Ready", "gray")
            self.after(0, lambda: self.send_btn.configure(state="normal"))

    # ------------------------------------------------------------ wake guard
    def toggle_wake_guard(self) -> None:
        if self.wake_guard is not None:
            self.wake_guard.stop = True
            self.wake_guard = None
            self.append_text("[System] Wake-word listening off.")
            return
        self.wake_guard = _WakeGuard(self)
        self.wake_guard.start()
        self.append_text(
            f"[System] Wake-word listening on. Say '{os.environ.get('JARVIS_WAKE_WORD', 'jarvis')}' "
            f"into the mic to wake me up."
        )

    def wake_activation(self) -> None:
        """Called by the background guard when 'Jarvis' is heard."""
        self.after(0, lambda: self._activate_window())
        _start_pulsing(self, "Status: Wake word heard — listening...", "#00E676")
        try:
            text = _listen_with_retries()
            if not text:
                self.append_text("[System] Wake word heard, but no command — "
                                 "saying my name again works too.")
                return
            self.append_text(f"You (wake): {text}")
            self.process(text)
        except Exception as e:
            self.append_text(f"[System] Couldn't hear audio clearly: {e}")
        finally:
            _stop_pulsing(self, "Status: Ready", "gray")

    def _delayed_stop_speaking(self) -> None:
        """Let the spoken reply finish, then return the status to Ready."""
        time.sleep(1.5)  # generous buffer; glow is cosmetic
        _stop_pulsing(self, "Status: Ready", "gray")

    def _activate_window(self) -> None:
        try:
            self.attributes("-topmost", True)
            self.focus_force()
            self.after(500, lambda: self.attributes("-topmost", self.on_top_var.get()))
        except Exception:
            pass  # not supported on all platforms

    # ----------------------------------------------------------------- on top
    def toggle_on_top(self) -> None:
        try:
            self.attributes("-topmost", self.on_top_var.get())
        except Exception:
            pass

    # ----------------------------------------------------------------- tray
    def minimize_to_tray(self) -> None:
        try:
            self.withdraw()
            self._tray = TrayApp(self)
            self.append_text("[System] Minimized to tray — click the "
                             "notification-area icon to restore.")
        except Exception as e:
            self.append_text(f"[System] Tray unavailable: {e}")


class _WakeGuard(threading.Thread):
    """Background wake-word guard.

    Loops: sleep a bit -> check the wake word -> on a hit, call
    app.wake_activation() once and return. A small cooldown avoids the
    guard re-firing on the STT echo of the user's own follow-up utterance.
    """

    def __init__(self, app: AstroDesktopApp):
        super().__init__(daemon=True)
        self.app = app
        self.stop = False

    def run(self) -> None:
        cooldown = 0
        while not self.stop:
            try:
                hit = detect_wake_word(timeout=4.0)
            except Exception:
                hit = False
            if hit and cooldown <= 0:
                cooldown = 8  # seconds before the guard listens again
                try:
                    self.app.wake_activation()
                except Exception as e:
                    self.app.append_text(f"[System] Wake guard error: {e}")
            else:
                cooldown -= 1
            time.sleep(1)


class TrayApp:
    """Notification-area tray icon (Windows). Pystray only."""

    def __init__(self, app: AstroDesktopApp):
        from pystray import Icon, Menu, MenuItem
        from PIL import Image

        icon = Image.new("RGB", (64, 64), "#1f538d")
        menu = Menu(
            MenuItem("Show ASTRO", action=self._show),
            MenuItem("Quit", action=self._quit),
        )
        self._icon = Icon("ASTRO", icon, "ASTRO — Local AI Desktop", menu)
        self.app = app
        threading.Thread(target=self._icon.run, daemon=True).start()

    def _show(self, *_a) -> None:
        self._icon.stop()
        self.app.deiconify()
        self.app.attributes("-topmost", True)
        self.app.after(300, lambda: self.app.attributes("-topmost", self.app.on_top_var.get()))

    def _quit(self, *_a) -> None:
        self._icon.stop()
        try:
            self.app.wake_guard.stop = True
        except Exception:
            pass
        self.app.quit()


if __name__ == "__main__":
    app = AstroDesktopApp()
    # Wake-word guard can also start enabled by default when the .env says so:
    if os.environ.get("JARVIS_MODE", "").lower() == "wake":
        app.after(1500, lambda: app.wake_toggle.select())
    app.mainloop()
