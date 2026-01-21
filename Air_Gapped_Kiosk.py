import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import hashlib
import shutil
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
# Simulated paths representing the 'Dirty' USB and the 'Secure' Internal Network
DIRTY_ZONE = "usb_simulation"
SECURE_ZONE = "secure_network"

# Simulated VirusTotal / Global Threat Database (MD5 Hashes)
# In a real military app, this would be an offline database of known malware signatures.
THREAT_DATABASE = {
    "d41d8cd98f00b204e9800998ecf8427e": "Null-File-Exploit",
    "5d41402abc4b2a76b9719d911017c592": "Ransomware.WannaCry.Mock",
    "098f6bcd4621d373cade4e832627b4f6": "Spyware.Keylogger.Demo"
}


class KioskApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIR-GAPPED SECURITY KIOSK v1.0")
        self.root.geometry("700x550")
        self.root.configure(bg="#1a1a1a")

        # Initialize Simulation Folders
        for path in [DIRTY_ZONE, SECURE_ZONE]:
            if not os.path.exists(path):
                os.makedirs(path)

        self.setup_ui()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#2d2d2d", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="🛡️ SECURE DATA INGRESS KIOSK",
                 font=("Courier", 20, "bold"), bg="#2d2d2d", fg="#00ff00").pack()
        tk.Label(header, text="UNAUTHORIZED ACCESS IS PROHIBITED",
                 font=("Courier", 10), bg="#2d2d2d", fg="#ff4444").pack()

        # Main Panel
        main_frame = tk.Frame(self.root, bg="#1a1a1a", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # File Selection Area
        selection_frame = tk.LabelFrame(main_frame, text=" INGRESS CONTROL ",
                                        bg="#1a1a1a", fg="#aaa", font=("Arial", 10, "bold"))
        selection_frame.pack(fill="x", pady=10)

        tk.Label(selection_frame, text="Select file from External Media:",
                 bg="#1a1a1a", fg="white").pack(pady=5)

        self.btn_browse = tk.Button(selection_frame, text="BROWSE EXTERNAL DRIVE",
                                    command=self.browse_file, bg="#444", fg="white",
                                    font=("Arial", 10, "bold"), width=30)
        self.btn_browse.pack(pady=10)

        # Progress & Status
        self.status_lbl = tk.Label(main_frame, text="SYSTEM READY: AWAITING INPUT",
                                   font=("Courier", 12, "bold"), bg="#1a1a1a", fg="#00ff00")
        self.status_lbl.pack(pady=10)

        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=600, mode='determinate')
        self.progress.pack(pady=5)

        # Scan Results / Details
        details_frame = tk.LabelFrame(main_frame, text=" SCAN ANALYSIS ",
                                      bg="#1a1a1a", fg="#aaa", font=("Arial", 10, "bold"))
        details_frame.pack(fill="both", expand=True, pady=10)

        self.txt_log = tk.Text(details_frame, bg="black", fg="#00ff00", font=("Courier", 9))
        self.txt_log.pack(fill="both", expand=True, padx=5, pady=5)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.txt_log.see(tk.END)

    def browse_file(self):
        file_path = filedialog.askopenfilename(title="Select File to Ingest")
        if file_path:
            self.process_file(file_path)

    def calculate_md5(self, file_path):
        """Generates the MD5 fingerprint of the file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def process_file(self, source_path):
        self.txt_log.delete("1.0", tk.END)
        self.progress['value'] = 0
        file_name = os.path.basename(source_path)

        self.log(f"INITIATING SCAN: {file_name}")
        self.status_lbl.config(text="ANALYZING FILE...", fg="yellow")
        self.root.update()

        # Step 1: Hashing
        time.sleep(1)  # Simulated delay
        file_hash = self.calculate_md5(source_path)
        self.log(f"MD5 HASH: {file_hash}")
        self.progress['value'] = 40
        self.root.update()

        # Step 2: Database Cross-Reference
        time.sleep(1)
        self.log("CHECKING THREAT DATABASE...")

        if file_hash in THREAT_DATABASE:
            threat_name = THREAT_DATABASE[file_hash]
            self.progress['value'] = 100
            self.status_lbl.config(text="⚠️ SECURITY ALERT: THREAT DETECTED", fg="#ff4444")
            self.log(f"!!! CRITICAL ERROR: File matches signature for {threat_name}")
            self.log("ACTION: Transfer Blocked. Source media flagged for destruction.")
            messagebox.showerror("MALWARE DETECTED",
                                 f"Threat Found: {threat_name}\n\nThis file has been blocked by the security gateway.")
        else:
            # Step 3: Secure Transfer
            self.log("STATUS: FILE CLEAN.")
            self.status_lbl.config(text="AUTHORIZING TRANSFER...", fg="#00ff00")
            self.progress['value'] = 70
            self.root.update()

            time.sleep(1.5)
            try:
                destination = os.path.join(SECURE_ZONE, file_name)
                shutil.copy2(source_path, destination)

                self.progress['value'] = 100
                self.status_lbl.config(text="TRANSFER COMPLETE", fg="#00ff00")
                self.log(f"SUCCESS: File migrated to {SECURE_ZONE}/")
                self.log("VERIFICATION: Hash match confirmed post-transfer.")
                messagebox.showinfo("SUCCESS", "File successfully transferred to the secure network.")
            except Exception as e:
                self.log(f"SYSTEM ERROR: {str(e)}")
                messagebox.showerror("Error", "Internal transfer failure.")


if __name__ == "__main__":
    # Create required folders for the simulation
    root = tk.Tk()
    app = KioskApp(root)
    root.mainloop()