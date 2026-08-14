#!/usr/bin/env python3
"""
JARVIS HUD — the Iron Man-style dashboard from the build-along videos.

Replicates the three-reel result in one window:
  - Central animated radar ring that breathes BLUE while listening/idle
    and shifts to RED/PINK while speaking — pure tkinter canvas math,
    no extra packages.
  - Left panel: live system metrics (CPU %, RAM %, Disk %) refreshed
    every 2 seconds using stdlib-only subprocess calls (psutil is a
    bonus, not a requirement).
  - Right panel: chat log of everything you said and JARVIS answered,
    with timestamps.
  - Bottom: status line ("LISTENING" / "THINKING" / "SPEAKING" / "READY"),
    typed command box, mic button, and the wake-word switch.
  - On-top toggle + minimize-to-tray for the 24/7 always-on use case.

Run:
    python jarvis_hud.py          # from the repo root
    pythonw jarvis_hud.py         # windowless; the tray icon brings it back

Wake word "Jarvis" activates it: the window pops to front, listens, the
ring turns blue while it listens, and pink while the reply is spoken.
All answers run through the vault brain (intent router + local Llama-3
or API, with conversation memory) — zero browser tab, zero terminal
needed.
"""
import math
import os
import sys
import threading
import time
import traceback
from pathlib import Path

import tkinter as tk

# ---------------------------------------------------------------------------
# Resolve the vault so the HUD can be launched from anywhere (shortcut,
# service, startup folder).
# ---------------------------------------------------------------------------
VAULT_CANDIDATES = [
    (Path(__file__).resolve().parent).as_posix(),  # lives inside the vault
    (Path(__file__).resolve().parent.parent).as_posix(),
]
VAULT = next((v for v in VAULT_CANDIDATES if (Path(v) / "src").is_dir()), "")
if not VAULT:
    probe = Path(__file__).resolve().parent
    for _ in range(3):
        probe = probe.parent
        for cand in ("my_large_data_vault", "my-large-data-vault"):
            if (probe / cand).is_dir() and (probe / cand / "src").is_dir():
                VAULT = (probe / cand).as_posix()
                break
        if VAULT:
            break
for _p in (VAULT, str(Path(VAULT).parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from src.utils.voice import detect_wake_word, listen, speak  # noqa: E402
    from jarvis import run_once as respond  # noqa: E402
except ImportError:
    raise RuntimeError(
        "JARVIS HUD: cannot find the vault modules. "
        f"Looked at: {VAULT}. Run from the repo root: python my-large-data-vault/jarvis_hud.py"
    )

try:
    import dotenv

    dotenv.load_dotenv(Path(VAULT) / ".env", override=False)
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Palette — the JARVIS look: deep navy bg, electric blue, speaking pink.
# ---------------------------------------------------------------------------
BG = "#0a0e1a"
PANEL = "#101828"
ACCENT = "#3377ff"
ACCENT_DIM = "#1a3d73"
SPEAK = "#ff3366"
READY_GRAY = "#5a7aa8"
TEXT = "#d8e4f5"

IDLE_BLUE = (0x33, 0x77, 0xFF)
SPEAK_PINK = (0xFF, 0x33, 0x66)
THINK_AMBER = (0xFF, 0xA6, 0x22)


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


# ---------------------------------------------------------------------------
# System metrics — stdlib only (psutil if present, else taskmgr/wmic calls).
# ---------------------------------------------------------------------------
def _get_metrics() -> dict:
    cpu, ram, disk = "—", "—", "—"
    try:
        import psutil

        cpu = int(round(psutil.cpu_percent(interval=0.1)))
        m = psutil.virtual_memory()
        ram = int(round(m.percent))
        d = psutil.disk_usage("/")
        disk = int(round(d.percent))
    except ImportError:
        import platform
        import subprocess

        if platform.system() == "Windows":
            try:
                out = subprocess.run(
                    ["wmic", "os", "get", "FreePhysicalMemory,TotalVisibleMemorySize"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.split()
                nums = [x for x in out if x.isdigit()]
                if len(nums) == 2:
                    ram = int(round(100 - 100 * int(nums[0]) / int(nums[1])))
            except Exception:
                pass
        else:
            try:
                out = subprocess.run(
                    ["vmstat", "1", "2"], capture_output=True, text=True, timeout=5,
                ).stdout.split()
                nums = [x for x in out if x.isdigit()]
                if nums:
                    cpu = int(nums[-3]) if len(nums) >= 3 else cpu
            except Exception:
                pass
    return {"cpu": cpu, "ram": ram, "disk": disk}


# ---------------------------------------------------------------------------
# The HUD window.
# ---------------------------------------------------------------------------
class JarvisHUD(tk.Tk):
    """Iron Man-style HUD: radar ring + metrics + chat log + voice input."""

    def __init__(self):
        super().__init__()
        self.title("JARVIS — ASTRO Local Desktop")
        self.geometry("900x640")
        self.minsize(820, 580)
        self.configure(bg=BG)

        # ---- header ---------------------------------------------------------
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=16, pady=(10, 2))
        tk.Label(
            hdr, text="J.A.R.V.I.S.", bg=BG, fg=ACCENT,
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")
        self.status_var = tk.StringVar(value="READY")
        tk.Label(
            hdr, textvariable=self.status_var, bg=BG, fg=READY_GRAY,
            font=("Consolas", 13),
        ).pack(side="right")

        # ---- body: metrics | radar | chat -----------------------------------
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=4)

        # Metrics panel (left)
        self.metric_frame = tk.Frame(body, bg=PANEL, padx=14, pady=12)
        self.metric_frame.pack(side="left", fill="y", padx=(0, 8))
        tk.Label(
            self.metric_frame, text="SYSTEM", bg=PANEL, fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        self.metric_labels = {}
        for name in ("CPU", "RAM", "DISK"):
            f = tk.Frame(self.metric_frame, bg=PANEL)
            f.pack(anchor="w", pady=6)
            tk.Label(f, text=name, bg=PANEL, fg=TEXT, font=("Segoe UI", 10)).pack(side="left")
            v = tk.StringVar(value="—")
            bar = tk.Label(f, textvariable=v, bg=PANEL, fg=ACCENT, font=("Consolas", 10))
            bar.pack(side="left", padx=8)
            self.metric_labels[name] = v

        # Radar canvas (center)
        self.canvas = tk.Canvas(
            body, bg=BG, width=340, height=340, highlightthickness=0,
        )
        self.canvas.pack(side="left", padx=8)

        # Chat log (right)
        self.chat_frame = tk.Frame(body, bg=PANEL, padx=12, pady=12)
        self.chat_frame.pack(side="right", fill="both", expand=True)
        tk.Label(
            self.chat_frame, text="CHAT LOG", bg=PANEL, fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        self.chat_box = tk.Text(
            self.chat_frame, bg=BG, fg=TEXT, insertbackground=TEXT,
            font=("Consolas", 10), wrap="word", bd=0, relief="flat",
        )
        self.chat_box.pack(fill="both", expand=True, padx=4, pady=6)
        self.chat_box.insert("end", "J.A.R.V.I.S. online. Say 'Jarvis', use the mic, or type below.\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.config(state="normal")
        self.chat_box.configure(bg=BG, fg=TEXT)
        self.chat_box.configure(state="disabled")

        # ---- footer ---------------------------------------------------------
        foot = tk.Frame(self, bg=BG)
        foot.pack(fill="x", padx=16, pady=(0, 10))

        self.entry = tk.Entry(
            foot, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat",
            bd=1, font=("Consolas", 11),
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.entry.bind("<Return>", lambda _e: self._send())

        tk.Button(
            foot, text="Send", command=self._send, bg=ACCENT, fg="white",
            activebackground="#5590ff", relief="flat", font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(0, 8), ipadx=14, ipady=3)

        self.mic_btn = tk.Button(
            foot, text="Mic", command=self._voice_thread, bg=ACCENT_DIM,
            fg="white", activebackground="#3a5d99", relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        self.mic_btn.pack(side="left", padx=(0, 8), ipadx=14, ipady=3)

        self.wake_var = tk.BooleanVar()
        tk.Checkbutton(
            foot, text="Wake-word ('Jarvis')", bg=BG, fg=TEXT,
            selectcolor=PANEL, variable=self.wake_var, command=self._toggle_wake,
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(0, 8))

        self.tray_btn = tk.Button(
            foot, text="To tray", command=self._to_tray, bg="#333a4a",
            fg=TEXT, relief="flat", font=("Segoe UI", 10),
        )
        self.tray_btn.pack(side="right", ipadx=12, ipady=3)

        # ---- state -----------------------------------------------------------
        self.busy = False
        self.ring_angle = 0.0
        self.target_color = IDLE_BLUE
        self.current_color = IDLE_BLUE
        self.sweep_speed = 1.6          # rad/s while idle
        self.ring_speed = 0.0
        self.ring_color_override = None
        self.wake_guard = None
        self.on_top = False

        self.after(100, self._animate)
        self.after(2000, self._refresh_metrics)
        self.after(600, self._boot_speak)

    # ------------------------------------------------------------------ speak
    def _boot_speak(self) -> None:
        try:
            from jarvis import boot_check

            speak(boot_check())
        except Exception:
            speak("J.A.R.V.I.S. online.")

    # ------------------------------------------------------------------ radar
    def _animate(self) -> None:
        """One animation frame: rotating sweep + color cross-fade."""
        w = h = 340
        cx = cy = w // 2
        self.canvas.delete("all")

        # cross-fade toward the target state color
        self.current_color = _lerp(self.current_color, self.target_color, 0.08)

        self.ring_angle = (self.ring_angle + self.sweep_speed * 0.03) % (2 * math.pi)

        color = _hex(self.current_color)
        dim = _hex(_lerp(self.current_color, (0x0a, 0x0e, 0x1a), 0.75))

        # outer reference rings
        for r in (160, 130, 100):
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=dim, width=1)

        # cross-hairs
        for dx in (-160, 0, 160):
            self.canvas.create_line(cx + dx, cy - 160, cx + dx, cy + 160, fill=dim, width=1)
            self.canvas.create_line(cx - 160, cy + dx, cx + 160, cy + dx, fill=dim, width=1)

        # rotating sweep wedge
        wedge = self.ring_angle
        self.canvas.create_arc(
            cx - 160, cy - 160, cx + 160, cy + 160,
            start=math.degrees(wedge) - 30, extent=35,
            style="pieslice", fill=dim, outline="",
        )
        # leading edge (the bright line)
        x1 = cx + 160 * math.cos(wedge)
        y1 = cy + 160 * math.sin(wedge)
        self.canvas.create_line(cx, cy, x1, y1, fill=color, width=2)

        # center label
        self.canvas.create_text(cx, cy - 8, text="J.A.R.V.I.S.", fill=color, font=("Segoe UI", 14, "bold"))
        self.canvas.create_text(cx, cy + 14, text="ASTRO VAULT", fill=READY_GRAY, font=("Consolas", 9))

        self.after(30, self._animate)

    def _set_mood(self, color, speed, status: str) -> None:
        self.target_color = color
        self.sweep_speed = speed
        self.status_var.set(status)

    # ------------------------------------------------------------------ metrics
    def _refresh_metrics(self) -> None:
        m = _get_metrics()
        for name in ("CPU", "RAM", "DISK"):
            val = m.get(name.lower(), "—")
            self.metric_labels[name].set(f"{val}%")
        self.after(2000, self._refresh_metrics)

    # ------------------------------------------------------------------ chat
    def _log(self, who: str, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.after(0, self.__log, stamp, who, text)

    def __log(self, stamp, who, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"[{stamp}] {who}: {text}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    # ------------------------------------------------------------------ send
    def _send(self) -> None:
        cmd = self.entry.get().strip()
        if not cmd or self.busy:
            return
        self.entry.delete(0, "end")
        threading.Thread(target=self._process, args=(cmd,), daemon=True).start()

    def _voice_thread(self) -> None:
        if self.busy:
            return
        threading.Thread(target=self._listen_once, daemon=True).start()

    def _listen_once(self) -> None:
        try:
            self._set_mood(IDLE_BLUE, 3.0, "LISTENING")
            text = _listen_with_retries()
            if text:
                self._log("YOU", text)
                self._process(text)
            else:
                self._log("SYSTEM", "Didn't catch that — try again.")
        except Exception as e:
            self._log("SYSTEM", f"Couldn't hear audio clearly: {e}")
        finally:
            self._set_mood(IDLE_BLUE, 1.6, "READY")

    def _process(self, cmd: str) -> None:
        if self.busy:
            return
        self.busy = True
        self._set_mood(THINK_AMBER, 2.4, "THINKING")
        try:
            response = respond(cmd)
            self._log("JARVIS", response)
            self._set_mood(SPEAK_PINK, 3.6, "SPEAKING")
            threading.Thread(target=self._speak_and_settle, args=(response,), daemon=True).start()
        except Exception as e:
            self._log("SYSTEM", f"Error: {e}")
            traceback.print_exc()
            self.busy = False
            self._set_mood(IDLE_BLUE, 1.6, "READY")

    def _speak_and_settle(self, response: str) -> None:
        try:
            speak(response)
        except Exception:
            pass
        self.busy = False
        self.after(300, lambda: self._set_mood(IDLE_BLUE, 1.6, "READY"))

    # ------------------------------------------------------------------ wake
    def _toggle_wake(self) -> None:
        if self.wake_guard is not None:
            self.wake_guard.stop = True
            self.wake_guard = None
            self._log("SYSTEM", "Wake-word listening off.")
            return
        self.wake_guard = _WakeGuard(self)
        self.wake_guard.start()
        word = os.environ.get("JARVIS_WAKE_WORD", "jarvis")
        self._log("SYSTEM", f"Wake-word on. Say '{word}' into the mic.")

    def wake_activation(self) -> None:
        self.after(0, self._bring_front)
        self._set_mood(IDLE_BLUE, 3.0, "LISTENING")
        try:
            text = _listen_with_retries()
            if not text:
                self._log("SYSTEM", "Wake word heard — I'm listening, say your command.")
                return
            self._log("YOU (wake)", text)
            self._process(text)
        except Exception as e:
            self._log("SYSTEM", f"Couldn't hear audio clearly: {e}")
        finally:
            if not self.busy:
                self._set_mood(IDLE_BLUE, 1.6, "READY")

    def _bring_front(self) -> None:
        try:
            self.attributes("-topmost", True)
            self.focus_force()
            self.after(500, lambda: self.attributes("-topmost", self.on_top))
        except Exception:
            pass

    # ------------------------------------------------------------------ tray
    def _to_tray(self) -> None:
        try:
            self.withdraw()
            self._tray = _Tray(self)
            self._log("SYSTEM", "Minimized to tray — click the notification icon.")
        except Exception as e:
            self._log("SYSTEM", f"Tray unavailable: {e}")


def _listen_with_retries(attempts: int = 2, extra_timeout: int = 4) -> str:
    last_error = None
    for _ in range(attempts):
        try:
            text = listen()
            if text and text.strip():
                return text
        except Exception as e:
            last_error = e
        time.sleep(1.0)
    return ""


class _WakeGuard(threading.Thread):
    """Background wake-word guard with cooldown to avoid re-firing on echo."""

    def __init__(self, app: JarvisHUD):
        super().__init__(daemon=True)
        self.app = app
        self.stop = False

    def run(self) -> None:
        cooldown = 0
        while not self.stop:
            hit = False
            try:
                hit = detect_wake_word(timeout=4.0)
            except Exception:
                pass
            if hit and cooldown <= 0:
                cooldown = 8
                try:
                    self.app.wake_activation()
                except Exception as e:
                    self.app._log("SYSTEM", f"Wake guard error: {e}")
            else:
                cooldown -= 1
            time.sleep(1)


class _Tray:
    """Notification-area tray icon (pystray)."""

    def __init__(self, app: JarvisHUD):
        from pystray import Icon, Menu, MenuItem
        from PIL import Image

        img = Image.new("RGB", (64, 64), "#0a0e1a")
        from PIL import ImageDraw

        d = ImageDraw.Draw(img)
        d.ellipse([8, 8, 56, 56], outline="#3377ff", width=3)
        d.text((18, 24), "J", fill="#3377ff")
        menu = Menu(
            MenuItem("Show J.A.R.V.I.S.", action=self._show),
            MenuItem("Quit", action=self._quit),
        )
        self._icon = Icon("JARVIS", img, "JARVIS — ASTRO Local Desktop", menu)
        self.app = app
        threading.Thread(target=self._icon.run, daemon=True).start()

    def _show(self, *_a) -> None:
        self._icon.stop()
        self.app.deiconify()
        self.app._bring_front()

    def _quit(self, *_a) -> None:
        self._icon.stop()
        try:
            self.app.wake_guard.stop = True
        except Exception:
            pass
        self.app.quit()


if __name__ == "__main__":
    app = JarvisHUD()
    if os.environ.get("JARVIS_MODE", "").lower() == "wake":
        def _enable_wake():
            app.wake_var.set(True)
            app._toggle_wake()

        app.after(1500, _enable_wake)
    app.mainloop()
