import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# --- CONFIGURATION ---
PING_INTERVAL = 5  # Seconds between pings
FAILURE_THRESHOLD = 3  # Consecutive failures before ALARM
GRID_ROWS = 5
GRID_COLS = 10  # Total 50 Bunkers

# EMAIL CONFIG (Optional)
# To use, enable 'EMAIL_ENABLED' and provide real credentials
EMAIL_ENABLED = False
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"
OFFICER_EMAIL = "signal_officer@base.mil"


class Bunker:
    def __init__(self, name, ip):
        self.name = name
        self.ip = ip
        self.status = "GREEN"  # GREEN, YELLOW (Warning), RED (Outage)
        self.fail_count = 0
        self.last_seen = "Never"
        self.label_ref = None  # UI Reference


class HeartbeatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("STRATCOM // Network Heartbeat Monitor")
        self.root.geometry("1100x700")
        self.root.configure(bg="#0a0a0a")

        self.bunkers = []
        self.setup_bunkers()
        self.setup_ui()

        # Start the monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitoring_thread.start()

    def setup_bunkers(self):
        """Initializes 50 bunkers with simulated IPs."""
        for i in range(1, (GRID_ROWS * GRID_COLS) + 1):
            # Using loopback addresses for safe simulation (127.0.0.1 always pings)
            # You can change some to non-existent IPs (e.g., 192.168.1.200) to test failure
            ip = "127.0.0.1"
            if i % 7 == 0:  # Simulate some 'unstable' bunkers
                ip = f"10.0.0.{i}"

            self.bunkers.append(Bunker(f"BUNKER-{i:02d}", ip))

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#1a1a1a", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="📡 SIGNAL CORPS: BHA (Bunker Heartbeat Analyzer)",
                 font=("Courier", 20, "bold"), bg="#1a1a1a", fg="#00ff00").pack()

        self.time_lbl = tk.Label(header, text="", font=("Courier", 10), bg="#1a1a1a", fg="#aaa")
        self.time_lbl.pack()

        # Grid Container
        grid_frame = tk.Frame(self.root, bg="#0a0a0a", padx=20, pady=20)
        grid_frame.pack(fill="both", expand=True)

        # Create the visual grid
        for idx, bunker in enumerate(self.bunkers):
            r = idx // GRID_COLS
            c = idx % GRID_COLS

            lbl = tk.Label(grid_frame, text=f"{bunker.name}\nREADY",
                           font=("Arial", 8, "bold"), width=12, height=4,
                           bg="#333", fg="white", relief="flat")
            lbl.grid(row=r, column=c, padx=3, pady=3)
            bunker.label_ref = lbl

        # Console Log
        log_frame = tk.LabelFrame(self.root, text=" SIGNAL LOGS ", bg="#0a0a0a", fg="#00ff00")
        log_frame.pack(fill="x", padx=20, pady=10)
        self.log_box = tk.Text(log_frame, height=8, bg="black", fg="#00ff00", font=("Courier", 9))
        self.log_box.pack(fill="x", padx=5, pady=5)

    def log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{ts}] {message}\n")
        self.log_box.see(tk.END)

    def ping_check(self, ip):
        """Performs a single system ping."""
        # -n 1 for Windows, -c 1 for Linux/Mac
        param = '-n' if subprocess.os.name == 'nt' else '-c'
        command = ['ping', param, '1', '-w', '1000', ip]

        try:
            # Use shell=True on windows to suppress the popup window
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        except:
            return False

    def monitor_loop(self):
        """Background thread to loop through bunkers and ping."""
        while True:
            for bunker in self.bunkers:
                success = self.ping_check(bunker.ip)

                if success:
                    # Reset failure count if it was previously failing
                    if bunker.status != "GREEN":
                        self.log(f"RECOVERY: Connection restored for {bunker.name}")

                    bunker.status = "GREEN"
                    bunker.fail_count = 0
                    bunker.last_seen = datetime.now().strftime("%H:%M:%S")
                else:
                    bunker.fail_count += 1

                    if bunker.fail_count >= FAILURE_THRESHOLD:
                        if bunker.status != "RED":
                            self.log(f"!!! CRITICAL: {bunker.name} HEARTBEAT LOST ({bunker.ip})")
                            self.trigger_alert(bunker)
                        bunker.status = "RED"
                    else:
                        bunker.status = "YELLOW"
                        self.log(f"WARNING: {bunker.name} missed {bunker.fail_count} beats.")

                self.update_ui_node(bunker)

            self.root.after(0, lambda: self.time_lbl.config(
                text=f"LAST GLOBAL SCAN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
            time.sleep(PING_INTERVAL)

    def update_ui_node(self, bunker):
        """Updates the specific box color on the GUI."""
        color_map = {
            "GREEN": "#004d00",  # Dark Green
            "YELLOW": "#666600",  # Dark Yellow
            "RED": "#800000"  # Dark Red
        }
        text_color = "white"
        if bunker.status == "RED":
            text_color = "#ffcccc"

        def update():
            bunker.label_ref.config(
                bg=color_map[bunker.status],
                fg=text_color,
                text=f"{bunker.name}\n{bunker.status}\n{bunker.ip}"
            )

        self.root.after(0, update)

    def trigger_alert(self, bunker):
        """Handles the logic for notifying the officer."""
        if EMAIL_ENABLED:
            threading.Thread(target=self.send_alert_email, args=(bunker,), daemon=True).start()

        # We don't use messagebox inside the loop as it blocks execution
        # But we can flash the screen or play a sound
        print(f"ALERT: Dispatched notification for {bunker.name}")

    def send_alert_email(self, bunker):
        """Simulates sending a secure SMTP email."""
        msg_body = f"URGENT: Communication lost with {bunker.name} at IP {bunker.ip}.\n"
        msg_body += f"Time of Outage: {datetime.now()}\n"
        msg_body += "Consecutive failures: 3. Please dispatch repair team."

        msg = MIMEText(msg_body)
        msg['Subject'] = f"SIGNAL ALERT: {bunker.name} OFFLINE"
        msg['From'] = SENDER_EMAIL
        msg['To'] = OFFICER_EMAIL

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            print(f"Email sent successfully for {bunker.name}")
        except Exception as e:
            print(f"Email failed: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = HeartbeatApp(root)
    root.mainloop()