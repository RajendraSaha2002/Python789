import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
import psycopg2
import random
import time
import threading

# DB CONFIG
DB_CONFIG = {"dbname": "postgres", "user": "postgres", "password": "varrie75", "host": "localhost"}


class SonarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("INS-VIKRANT: SONAR ARRAY INTERFACE")
        self.root.geometry("800x600")
        self.root.configure(bg="#001f3f")  # Navy Blue

        # Header
        lbl = tk.Label(root, text="UNDERWATER ACOUSTIC ANALYSIS", font=("Arial", 16, "bold"), bg="#001f3f",
                       fg="#7FDBFF")
        lbl.pack(pady=10)

        # Matplotlib Figure
        self.fig, self.ax = plt.subplots(facecolor='#001f3f')
        self.ax.set_facecolor('#000000')  # Black sonar screen
        self.ax.set_ylim(-2, 2)
        self.line, = self.ax.plot([], [], color='#39FF14', lw=2)  # Radar Green

        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.x_data = np.linspace(0, 10, 100)
        self.running = True

        # Start Analysis Thread
        self.thread = threading.Thread(target=self.scan_ocean)
        self.thread.start()

    def log_threat(self, classification, freq):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("INSERT INTO sonar_logs (ship_id, detected_freq_hz, classification) VALUES (%s, %s, %s)",
                        ('INS-VIKRANT', int(freq), classification))
            conn.commit()
            conn.close()
            print(f"logged: {classification} at {freq}Hz")
        except Exception as e:
            print(f"DB Error: {e}")

    def scan_ocean(self):
        while self.running:
            # 1. Generate Signal
            freq = random.randint(100, 1000)  # Random frequency
            noise = np.random.normal(0, 0.5, 100)

            # Create waveform
            y_data = np.sin(2 * np.pi * freq * self.x_data / 1000) + noise

            # 2. Update Graph
            self.line.set_ydata(y_data)
            self.canvas.draw_idle()

            # 3. Classify
            # Logic: Low freq = Biological (Whales), High freq = Mechanical (Subs)
            if freq > 800:
                classification = "MECHANICAL"
                print("⚠️ THREAT DETECTED: MECHANICAL SIGNATURE")
                self.log_threat("MECHANICAL", freq)
                # Flash the GUI Red momentarily (Simulated)
                self.ax.set_facecolor('#330000')
            else:
                self.ax.set_facecolor('#000000')

            time.sleep(1.0)  # Scan every second


if __name__ == "__main__":
    root = tk.Tk()
    app = SonarApp(root)
    root.mainloop()