import customtkinter as ctk
import threading
import speech_recognition as sr
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AstroDesktopApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ASTRO — Local AI Desktop")
        self.geometry("450x550")
        self.resizable(False, False)

        # Title Header
        self.label = ctk.CTkLabel(self, text="ASTRO AI ASSISTANT", font=ctk.CTkFont(size=20, weight="bold"))
        self.label.pack(pady=(20, 10))

        # Status Indicator
        self.status_label = ctk.CTkLabel(self, text="Status: Ready", text_color="gray")
        self.status_label.pack(pady=5)

        # Output Text Box
        self.output_box = ctk.CTkTextbox(self, width=380, height=300)
        self.output_box.pack(pady=10)
        self.output_box.insert("0.0", "Welcome to ASTRO Local Desktop.\nClick 'Listen' to talk or type your prompt below.\n\n")

        # Command Input Field
        self.entry = ctk.CTkEntry(self, width=280, placeholder_text="Type command here...")
        self.entry.pack(side="left", padx=(35, 5), pady=15)

        # Send Button
        self.send_btn = ctk.CTkButton(self, text="Send", width=70, command=self.send_text_command)
        self.send_btn.pack(side="left", padx=5, pady=15)

        # Voice Button
        self.voice_btn = ctk.CTkButton(self, text="🎙️ Listen", fg_color="#1f538d", command=self.start_voice_thread)
        self.voice_btn.pack(side="bottom", pady=(0, 20))

    def append_text(self, text):
        self.output_box.insert("end", text + "\n")
        self.output_box.see("end")

    def send_text_command(self):
        cmd = self.entry.get()
        if cmd.strip():
            self.append_text(f"You: {cmd}")
            self.entry.delete(0, "end")
            # Here ASTRO processes the command via local Llama 3
            self.append_text("ASTRO: Processing local query...")

    def start_voice_thread(self):
        threading.Thread(target=self.listen_voice, daemon=True).start()

    def listen_voice(self):
        self.status_label.configure(text="Status: Listening...", text_color="#00FF00")
        r = sr.Recognizer()
        m = sr.Microphone()
        try:
            with m as source:
                r.adjust_for_ambient_noise(source, duration=0.8)
                audio = r.listen(source, timeout=5)
            text = r.recognize_google(audio)
            self.append_text(f"You (Voice): {text}")
        except Exception as e:
            self.append_text(f"[System]: Couldn't hear audio clearly ({e})")
        finally:
            self.status_label.configure(text="Status: Ready", text_color="gray")

if __name__ == "__main__":
    app = AstroDesktopApp()
    app.mainloop()