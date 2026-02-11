import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import sqlalchemy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
import threading
import time
import random

from sqlalchemy.dialects.postgresql import psycopg2

# DB CONNECTION
# REPLACE with your actual credentials
db_connection_str = 'postgresql+psycopg2://postgres:varrie75@localhost/postgres'
db_engine = sqlalchemy.create_engine(db_connection_str)


class DBMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PostgreSQL Internal Performance Intelligence")
        self.root.geometry("1400x900")
        self.root.configure(bg="#212121")  # Dark Mode for "Hacker" feel

        self.setup_ui()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#000000", height=80)
        header.pack(fill='x')
        tk.Label(header, text="🐘 PG-INTEL: Database Internals Monitor", bg="#000000", fg="#00e676",
                 font=("Consolas", 20, "bold")).pack(side="left", padx=20, pady=20)

        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.tab_overview = tk.Frame(self.notebook, bg="white")
        self.tab_indexes = tk.Frame(self.notebook, bg="white")
        self.tab_stress = tk.Frame(self.notebook, bg="#424242")

        self.notebook.add(self.tab_overview, text="🔥 Live Health & Bloat")
        self.notebook.add(self.tab_indexes, text="⚡ Index Efficiency")
        self.notebook.add(self.tab_stress, text="💀 Stress Test Engine")

        # Load Views
        self.setup_stress_tab()
        self.refresh_overview()

    def run_query(self, sql):
        try:
            with db_engine.connect() as conn:
                return pd.read_sql(sql, conn)
        except Exception as e:
            return pd.DataFrame()

    # ================= TAB 1: OVERVIEW (Bloat & Locks) =================
    def refresh_overview(self):
        # Clear old widgets
        for w in self.tab_overview.winfo_children(): w.destroy()

        # Frame for Controls
        ctrl = tk.Frame(self.tab_overview)
        ctrl.pack(fill='x', pady=5)
        tk.Button(ctrl, text="Refresh Metrics", command=self.refresh_overview, bg="#2196f3", fg="white").pack()

        # FETCH DATA
        df_bloat = self.run_query("SELECT * FROM v_table_bloat LIMIT 10")

        # VISUALIZATION
        fig = plt.figure(figsize=(12, 8))
        gs = fig.add_gridspec(2, 2)

        # Chart 1: Dead Tuples (Bloat)
        ax1 = fig.add_subplot(gs[0, :])
        if not df_bloat.empty:
            sns.barplot(data=df_bloat, x='table_name', y='bloat_pct', palette='Reds', ax=ax1)
            ax1.set_title("Table Bloat % (Dead Rows vs Live Rows)")
            ax1.set_ylabel("Bloat % (Need Vacuum?)")
            for container in ax1.containers:
                ax1.bar_label(container, fmt='%.1f%%')
        else:
            ax1.text(0.5, 0.5, "No Data / Clean DB", ha='center')

        # Chart 2: Connection States
        ax2 = fig.add_subplot(gs[1, 0])
        df_conn = self.run_query("SELECT state, count(*) FROM pg_stat_activity GROUP BY state")
        if not df_conn.empty:
            # Handle None/Null states
            df_conn['state'] = df_conn['state'].fillna('Idle')
            ax2.pie(df_conn['count'], labels=df_conn['state'], autopct='%1.1f%%', colors=sns.color_palette("pastel"))
            ax2.set_title("Active Connections")

        # Chart 3: Lock Wait Analysis
        ax3 = fig.add_subplot(gs[1, 1])
        df_locks = self.run_query("SELECT * FROM v_lock_monitor")
        if not df_locks.empty:
            # Simple count of locks
            ax3.bar(["Blocked Queries"], [len(df_locks)], color="orange")
            ax3.set_title(f"CRITICAL: {len(df_locks)} Queries Blocked/Waiting")
        else:
            ax3.text(0.5, 0.5, "System Healthy (No Locks)", ha='center', color='green', fontsize=14)
            ax3.set_title("Lock Contention Monitor")

        canvas = FigureCanvasTkAgg(fig, master=self.tab_overview)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    # ================= TAB 2: INDEX EFFICIENCY =================
    def show_index_stats(self):
        # Refresh Logic for Tab 2 (Similar structure to Tab 1)
        pass  # Placeholder for brevity, logic exists in SQL view v_index_efficiency

    # ================= TAB 3: STRESS TESTER =================
    def setup_stress_tab(self):
        lbl = tk.Label(self.tab_stress, text="WARNING: These actions impact database performance.",
                       bg="#424242", fg="#ff5252", font=("Arial", 14, "bold"))
        lbl.pack(pady=20)

        # Action 1: Mass Insert
        btn_insert = tk.Button(self.tab_stress, text="GENERATE 1 MILLION ROWS (Bulk Insert)",
                               bg="#00c853", fg="white", font=("Arial", 12), height=2,
                               command=self.trigger_mass_insert)
        btn_insert.pack(fill='x', padx=50, pady=10)

        # Action 2: Simulate Bloat (Update Churn)
        btn_bloat = tk.Button(self.tab_stress, text="SIMULATE BLOAT (Update 50k Rows Rapidly)",
                              bg="#ff9800", fg="black", font=("Arial", 12), height=2,
                              command=self.trigger_bloat)
        btn_bloat.pack(fill='x', padx=50, pady=10)

        # Action 3: Simulate Deadlocks
        btn_lock = tk.Button(self.tab_stress, text="SIMULATE LOCK CONTENTION (Threads Fighting)",
                             bg="#d50000", fg="white", font=("Arial", 12), height=2,
                             command=self.trigger_locks)
        btn_lock.pack(fill='x', padx=50, pady=10)

        # Log Area
        self.log_text = tk.Text(self.tab_stress, height=15, bg="black", fg="#00ff00")
        self.log_text.pack(fill='both', padx=20, pady=20)

    def log(self, msg):
        self.log_text.insert(tk.END, f"> {msg}\n")
        self.log_text.see(tk.END)

    def trigger_mass_insert(self):
        def run():
            self.log("Starting Bulk Insert of 1,000,000 rows...")
            start = time.time()
            try:
                with db_engine.connect() as conn:
                    conn.execute(sqlalchemy.text("CALL generate_load(1000000)"))
                    conn.commit()
                self.log(f"Success! Inserted 1M rows in {time.time() - start:.2f}s")
            except Exception as e:
                self.log(f"Error: {e}")

        threading.Thread(target=run).start()

    def trigger_bloat(self):
        def run():
            self.log("Starting Update Churn (creating dead tuples)...")
            try:
                # Update same rows multiple times to create dead versions
                with db_engine.connect() as conn:
                    for _ in range(50):  # 5 batches
                        conn.execute(
                            sqlalchemy.text("UPDATE stress_test_data SET updated_at = NOW() WHERE id % 10 = 0"))
                        conn.commit()
                        self.log("Batch update committed...")
                self.log("Bloat generation complete. Check 'Overview' tab.")
            except Exception as e:
                self.log(f"Error: {e}")

        threading.Thread(target=run).start()

    def trigger_locks(self):
        # Starts 2 threads that try to update the SAME row at the SAME time
        def worker(t_id):
            try:
                conn = psycopg2.connect(db_connection_str)
                cur = conn.cursor()
                self.log(f"Thread {t_id}: Acquired Transaction...")
                # Lock a row
                cur.execute("BEGIN;")
                cur.execute("SELECT * FROM stress_test_data WHERE id = 1 FOR UPDATE;")
                self.log(f"Thread {t_id}: Locked Row ID 1. Sleeping 5s...")
                time.sleep(5)
                cur.execute("COMMIT;")
                self.log(f"Thread {t_id}: Released Lock.")
                conn.close()
            except Exception as e:
                self.log(f"Thread {t_id} Error: {e}")

        self.log("Spawning contending threads...")
        threading.Thread(target=worker, args=(1,)).start()
        threading.Thread(target=worker, args=(2,)).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = DBMonitorApp(root)
    root.mainloop()