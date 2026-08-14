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
VAULT = (Path(__file__).resolve().parent / "my-large-data-vault").as_posix()
for _p in (VAULT, str(Path(VAULT).parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from my_large_data_vault.src.utils.voice import detect_wake_word, listen, speak  # noqa: E402

from my_large_data_vault.jarvis import run_once as astro_respond  # noqa: E402

import dotenv  # noqa: E402
dotenv.load_dotenv(Path(VAULT) / ".env", override=False)


def _set_status(app, text: str, color: str) -> None:
    """Thread-safe status update — always call from the UI thread."""
    app.after(0, lambda: app.status_label.configure(text=text, text_color=color))


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
        _set_status(self, "Status: Listening...", "#00E676")
        self.after(0, lambda: self.mic_btn.configure(fg_color="#00BFA5"))
        try:
            text = listen()
            if text:
                self.append_text(f"You (voice): {text}")
                self.process(text)
            else:
                self.append_text("[System] Didn't catch that — try again.")
        except Exception as e:
            self.append_text(f"[System] Couldn't hear audio clearly: {e}")
        finally:
            _set_status(self, "Status: Ready", "gray")
            self.after(0, lambda: self.mic_btn.configure(fg_color="#1f538d"))

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
            # Speak the reply aloud (voice.py handles missing TTS deps)
            threading.Thread(target=speak, args=(response,), daemon=True).start()
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
        _set_status(self, "Status: Wake word heard — listening...", "#00E676")
        try:
            text = listen()
            if not text:
                self.append_text("[System] Wake word heard, but no command — "
                                 "saying my name again works too.")
                return
            self.append_text(f"You (wake): {text}")
            self.process(text)
        except Exception as e:
            self.append_text(f"[System] Couldn't hear audio clearly: {e}")
        finally:
            _set_status(self, "Status: Ready", "gray")

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
