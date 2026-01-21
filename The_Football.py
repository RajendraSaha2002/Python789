import tkinter as tk
from tkinter import messagebox, simpledialog
import random
import json
import hashlib
import time
import os
from datetime import datetime

# --- Configuration ---
CODEBOOK_FILE = "daily_codes.json"
VALID_PIN_HASH = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # SHA-256 for '1234'
DURESS_PIN_HASH = "8623f73de6f92cc042dc08298759715a3bc3d67123992b963162232921509939"  # SHA-256 for '9999'

# Colors (Retro CRT Style)
BG_COLOR = "#000000"
FG_COLOR = "#33FF00"  # Phosphor Green
ALERT_COLOR = "#FF3333"  # Critical Red
FONT_MAIN = ("Consolas", 14)
FONT_HEADER = ("Consolas", 20, "bold")


class CryptoLogic:
    def __init__(self):
        self.load_or_generate_codebook()
        self.current_day = datetime.now().strftime("%A")
        self.daily_code = self.codebook.get(self.current_day, "ERROR")

    def load_or_generate_codebook(self):
        if os.path.exists(CODEBOOK_FILE):
            with open(CODEBOOK_FILE, 'r') as f:
                self.codebook = json.load(f)
        else:
            # Generate new random codes for the week
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            self.codebook = {}
            for day in days:
                # Format: 2 Letters + 2 Numbers (e.g., XK92)
                prefix = f"{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}{random.randint(10, 99)}"
                self.codebook[day] = prefix

            with open(CODEBOOK_FILE, 'w') as f:
                json.dump(self.codebook, f, indent=4)

    def generate_eam(self):
        """Generates a message. 50% chance it matches today's valid code."""
        if random.random() > 0.3:
            prefix = self.daily_code  # Valid
        else:
            prefix = "XX00"  # Invalid/Drill

        part2 = f"{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}{random.randint(10, 99)}"
        part3 = f"{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}{random.randint(10, 99)}"
        return f"{prefix}-{part2}-{part3}"

    def verify_pin(self, pin_input):
        """
        Returns:
        0: Invalid
        1: Valid (Normal)
        2: Duress (Silent Alarm)
        """
        hashed = hashlib.sha256(pin_input.encode()).hexdigest()
        if hashed == VALID_PIN_HASH:
            return 1
        elif hashed == DURESS_PIN_HASH:
            return 2
        return 0


class FootballTerminal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("STRATCOM // EAM DECODER TERMINAL")
        self.geometry("800x600")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)

        self.logic = CryptoLogic()
        self.eam_string = ""
        self.state = "STANDBY"  # STANDBY, AUTH_1, AUTH_2, ARMED

        self.build_ui()
        self.print_boot_sequence()

    def build_ui(self):
        # Scanlines overlay (Simulated with canvas lines if needed, but simple frame preferred for clarity)
        self.main_frame = tk.Frame(self, bg=BG_COLOR, padx=20, pady=20)
        self.main_frame.pack(expand=True, fill='both')

        # Header
        self.lbl_header = tk.Label(self.main_frame, text="*** US STRATEGIC COMMAND ***",
                                   bg=BG_COLOR, fg=FG_COLOR, font=FONT_HEADER)
        self.lbl_header.pack(pady=10)

        # Terminal Screen (Text Output)
        self.terminal = tk.Text(self.main_frame, height=15, width=70,
                                bg="#111", fg=FG_COLOR, font=FONT_MAIN,
                                relief="flat", state="disabled")
        self.terminal.pack(pady=10)

        # Status Bar
        self.lbl_status = tk.Label(self.main_frame, text="SYSTEM READY // SECURE LINK ESTABLISHED",
                                   bg=BG_COLOR, fg="#008800", font=("Consolas", 10))
        self.lbl_status.pack(fill="x", pady=5)

        # Input Area
        self.input_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.input_frame.pack(pady=20)

        self.lbl_prompt = tk.Label(self.input_frame, text="COMMAND >",
                                   bg=BG_COLOR, fg=FG_COLOR, font=FONT_MAIN)
        self.lbl_prompt.pack(side="left")

        self.entry_cmd = tk.Entry(self.input_frame, bg="#222", fg=FG_COLOR,
                                  font=FONT_MAIN, insertbackground=FG_COLOR, width=30)
        self.entry_cmd.pack(side="left", padx=10)
        self.entry_cmd.bind("<Return>", self.process_input)
        self.entry_cmd.focus()

        # Physical Buttons Simulation
        btn_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        btn_frame.pack(side="bottom", pady=20)

        tk.Button(btn_frame, text="RECEIVE TRANSMISSION", command=self.receive_message,
                  bg="#222", fg=FG_COLOR, font=("Consolas", 10, "bold"), width=25).pack(side="left", padx=10)

        tk.Button(btn_frame, text="RESET TERMINAL", command=self.reset_system,
                  bg="#222", fg=ALERT_COLOR, font=("Consolas", 10, "bold"), width=25).pack(side="left", padx=10)

    # --- Terminal Utilities ---

    def log(self, text, delay=0.0):
        """Typing effect for text."""
        self.terminal.config(state="normal")
        self.terminal.insert("end", f"{text}\n")
        self.terminal.see("end")
        self.terminal.config(state="disabled")
        self.update()
        if delay > 0:
            time.sleep(delay)

    def print_boot_sequence(self):
        self.log("BIOS CHECK... OK")
        self.log("LOADING KERNEL... OK")
        self.log("MOUNTING CRYPTO MODULE... OK")
        self.log(f"CURRENT DATE: {datetime.now().strftime('%Y-%m-%d')}")
        self.log(f"CODEBOOK: {self.logic.current_day.upper()} KEY LOADED.")
        self.log("-" * 60)
        self.log("WAITING FOR EAM TRANSMISSION...")

    # --- Core Logic ---

    def receive_message(self):
        if self.state != "STANDBY": return

        # Audio cue placeholder (beep)
        self.bell()

        self.eam_string = self.logic.generate_eam()

        self.log("\n!!! INCOMING TRAFFIC !!!", 0.2)
        self.log("RECEIVING SKYKING MESSAGE...", 0.5)
        self.log(f"MESSAGE: [ {self.eam_string} ]")
        self.log("-" * 60)
        self.log("ACTION REQUIRED: VERIFY PREAMBLE AGAINST DAILY CODEBOOK.")
        self.log(f"ENTER TODAY'S ({self.logic.current_day.upper()}) VALIDATION CODE:")

        self.state = "AUTH_1"
        self.lbl_status.config(text="STATUS: AUTHENTICATION IN PROGRESS", fg=ALERT_COLOR)

    def process_input(self, event):
        user_input = self.entry_cmd.get().strip().upper()
        self.entry_cmd.delete(0, 'end')

        if not user_input: return
        self.log(f"> {user_input}")

        if self.state == "AUTH_1":
            self.check_preamble(user_input)
        elif self.state == "AUTH_2":
            self.check_pin(user_input)
        elif self.state == "ARMED":
            self.log("SYSTEM ALREADY ARMED. WAITING FOR RELEASE KEY.")
        else:
            self.log("UNKNOWN COMMAND. SYSTEM IN STANDBY.")

    def check_preamble(self, code):
        # User checks their physical book (we generated it) and types the code
        expected = self.logic.daily_code

        if code == expected:
            # Check if the Message actually matches the valid code
            if self.eam_string.startswith(expected):
                self.log("VALIDATION SUCCESSFUL. MESSAGE IS AUTHENTIC.")
                self.log("STEP 2: ENTER SEALED AUTHENTICATOR PIN.")
                self.state = "AUTH_2"
            else:
                self.log("WARNING: MESSAGE PREAMBLE MISMATCH.")
                self.log(f"MSG PREAMBLE: {self.eam_string[:4]}")
                self.log(f"VALID CODE:   {expected}")
                self.log("DISCARD MESSAGE AS EXERCISE/SPAM.")
                self.reset_system()
        else:
            self.log("ERROR: INCORRECT DAILY CODE.")
            self.log(f"HINT: Check {CODEBOOK_FILE} for {self.logic.current_day}.")

    def check_pin(self, pin):
        result = self.logic.verify_pin(pin)

        if result == 1:
            # VALID
            self.trigger_unlock(duress=False)
        elif result == 2:
            # DURESS
            self.trigger_unlock(duress=True)
        else:
            # INVALID
            self.log("AUTHENTICATION FAILED. INCORRECT PIN.")
            self.lbl_status.config(text="STATUS: SECURITY LOCKOUT", fg=ALERT_COLOR)
            self.state = "LOCKED"

    def trigger_unlock(self, duress=False):
        self.state = "ARMED"
        self.log("\n*** AUTHORIZATION CONFIRMED ***")
        self.log("PAL (PERMISSIVE ACTION LINK) UNLOCKED.")
        self.log("WEAPONS FREE.")

        self.lbl_status.config(text="STATUS: ARMED // WAITING RELEASE", fg=ALERT_COLOR)

        if duress:
            # The User Interface looks normal...
            # But we log the secret alert
            print("\n[!!!] SILENT ALARM TRIGGERED: DURESS CODE USED [!!!]")
            # In a real app, this would send a network packet to HQ
            self.lbl_header.config(text="*** US STRATEGIC COMMAND (LINK MONITORED) ***")
        else:
            print("\n[OK] NORMAL AUTHENTICATION")

    def reset_system(self):
        self.state = "STANDBY"
        self.lbl_status.config(text="SYSTEM READY // SECURE LINK ESTABLISHED", fg="#008800")
        self.log("\n--- TERMINAL RESET ---")
        self.lbl_header.config(text="*** US STRATEGIC COMMAND ***")


if __name__ == "__main__":
    # Create the app
    app = FootballTerminal()
    app.mainloop()