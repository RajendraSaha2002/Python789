import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
import threading
import random
import time
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from concurrent.futures import ThreadPoolExecutor

# DB CONFIGURATION
# REPLACE with your actual credentials
db_config = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "varrie75",
    "host": "localhost"
}


class BankingSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("High-Concurrency Banking Engine Simulator")
        self.root.geometry("1300x850")
        self.root.configure(bg="#f0f2f5")

        # State Variables
        self.is_running = False
        self.tx_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.start_time = 0

        self.setup_ui()

    def setup_ui(self):
        # --- Header ---
        header = tk.Frame(self.root, bg="#1a237e", height=80)
        header.pack(fill='x')
        tk.Label(header, text="CORE BANKING STRESS TESTER", bg="#1a237e", fg="white",
                 font=("Helvetica", 24, "bold")).pack(pady=20)

        # --- Control Panel ---
        control_frame = tk.Frame(self.root, bg="white", bd=2, relief="groove")
        control_frame.pack(fill='x', padx=20, pady=10)

        tk.Label(control_frame, text="Threads:", font=("Arial", 12)).pack(side="left", padx=10)
        self.slider_threads = tk.Scale(control_frame, from_=1, to=50, orient="horizontal", length=200)
        self.slider_threads.set(10)
        self.slider_threads.pack(side="left", padx=10)

        tk.Label(control_frame, text="Tx Volume:", font=("Arial", 12)).pack(side="left", padx=10)
        self.entry_volume = tk.Entry(control_frame, width=10)
        self.entry_volume.insert(0, "500")
        self.entry_volume.pack(side="left", padx=10)

        self.btn_start = tk.Button(control_frame, text="START SIMULATION", bg="#00c853", fg="white",
                                   font=("Arial", 12, "bold"), command=self.start_simulation)
        self.btn_start.pack(side="right", padx=20, pady=15)

        # --- Dashboard Area ---
        dash_frame = tk.Frame(self.root)
        dash_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Left: Live Log
        # FIX: width=400 is moved inside the LabelFrame constructor
        log_frame = tk.LabelFrame(dash_frame, text="Transaction Stream (Live)", font=("Arial", 10, "bold"), width=400)

        # FIX: Removed 'width' from pack()
        log_frame.pack(side="left", fill="y")

        # This prevents the frame from shrinking to fit the text content
        log_frame.pack_propagate(False)

        self.log_text = tk.Text(log_frame, bg="black", fg="#00ff00", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        # Right: Charts
        self.chart_frame = tk.Frame(dash_frame, bg="white")
        self.chart_frame.pack(side="right", fill="both", expand=True, padx=10)

    def log_msg(self, msg):
        self.log_text.insert(tk.END, f"> {msg}\n")
        self.log_text.see(tk.END)

    def execute_single_transaction(self, tx_id):
        # Simulate a random transfer
        sender = random.randint(1, 100)
        receiver = random.randint(1, 100)
        while receiver == sender:
            receiver = random.randint(1, 100)

        amount = round(random.uniform(10, 500), 2)

        try:
            conn = psycopg2.connect(**db_config)
            # Autocommit must be ON for CALL to work in some driver versions
            conn.autocommit = True
            cur = conn.cursor()

            # Start timer for latency check
            t0 = time.time()

            # Call the Stored Procedure
            cur.execute(f"CALL transfer_funds({sender}, {receiver}, {amount})")

            latency = (time.time() - t0) * 1000  # ms
            conn.close()

            return ("SUCCESS", latency)
        except Exception as e:
            return ("FAILED", str(e))

    def run_stress_test(self, num_threads, total_tx):
        self.log_msg(f"Initializing {num_threads} threads for {total_tx} transactions...")

        results = []
        self.start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(self.execute_single_transaction, i) for i in range(total_tx)]

            for i, future in enumerate(futures):
                res = future.result()
                results.append(res)

                # Live update every 50 tx
                if i % 50 == 0:
                    self.log_msg(f"Processed {i}/{total_tx}...")

        self.process_results(results)

    def start_simulation(self):
        if self.is_running: return
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.log_text.delete(1.0, tk.END)

        threads = self.slider_threads.get()
        volume = int(self.entry_volume.get())

        # Run in separate thread to keep GUI responsive
        threading.Thread(target=self.run_stress_test, args=(threads, volume)).start()

    def process_results(self, results):
        self.log_msg("Simulation Complete. Calculating Stats...")

        success = [r for r in results if r[0] == "SUCCESS"]
        failures = [r for r in results if r[0] == "FAILED"]
        latencies = [r[1] for r in success]

        self.success_count = len(success)
        self.fail_count = len(failures)

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        total_time = time.time() - self.start_time
        tps = len(results) / total_time if total_time > 0 else 0

        summary = f"""
        --------------------------
        TOTAL TIME: {total_time:.2f}s
        THROUGHPUT: {tps:.2f} Tx/sec
        SUCCESS: {self.success_count}
        FAILED: {self.fail_count}
        AVG LATENCY: {avg_latency:.2f}ms
        --------------------------
        """
        self.log_msg(summary)

        # Update UI Charts
        self.root.after(0, self.update_charts, success, failures)
        self.is_running = False
        self.root.after(0, lambda: self.btn_start.config(state="normal"))

    def update_charts(self, success_data, fail_data):
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        fig = plt.figure(figsize=(8, 6))

        # Chart 1: Success vs Fail Pie
        ax1 = fig.add_subplot(221)
        ax1.pie([len(success_data), len(fail_data)], labels=['Success', 'Failed'],
                autopct='%1.1f%%', colors=['#00c853', '#d50000'], startangle=90)
        ax1.set_title("Transaction Integrity")

        # Chart 2: Latency Histogram
        ax2 = fig.add_subplot(212)
        if success_data:
            latencies = [x[1] for x in success_data]
            ax2.hist(latencies, bins=30, color='#2962ff', alpha=0.7)
            ax2.set_title("Latency Distribution (ms)")
            ax2.set_xlabel("Time (ms)")
            ax2.set_ylabel("Count")

        # Chart 3: Database Balance Check (Consistency Validation)
        # Verify that money wasn't created or destroyed
        ax3 = fig.add_subplot(222)
        try:
            conn = psycopg2.connect(**db_config)
            df = pd.read_sql("SELECT SUM(balance) as total FROM accounts", conn)
            total_money = df['total'][0]
            conn.close()

            # Since we only do transfers, total money in system must remain constant ($1,000,000)
            ax3.bar(['Expected', 'Actual'], [1000000, total_money], color=['gray', 'orange'])
            ax3.set_title(f"Global Ledger Consistency\nTarget: $1M | Actual: ${total_money:,.0f}")
            ax3.set_ylim(900000, 1100000)
        except Exception as e:
            print(f"Error checking balance: {e}")

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = BankingSimulatorApp(root)
    root.mainloop()