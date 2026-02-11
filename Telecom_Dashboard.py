import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import sqlalchemy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from faker import Faker
import random
import datetime

# DB CONFIGURATION
# REPLACE with your actual credentials
db_connection_str = 'postgresql+psycopg2://postgres:varrie75@localhost/postgres'
db_engine = sqlalchemy.create_engine(db_connection_str)


class TelecomAnalyticsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Telecom CDR Analytics Platform (Big Data Mode)")
        self.root.geometry("1400x900")
        self.root.configure(bg="#e3f2fd")

        # Layout
        self.create_sidebar()
        self.create_main_area()

        # Default View
        self.show_traffic_page()

    def create_sidebar(self):
        sidebar = tk.Frame(self.root, bg="#1565c0", width=250)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Title
        tk.Label(sidebar, text="CDR\nANALYTICS", bg="#1565c0", fg="white",
                 font=("Arial", 20, "bold")).pack(pady=40)

        # Navigation Buttons
        self.create_nav_btn(sidebar, "📶 Traffic Analysis", self.show_traffic_page)
        self.create_nav_btn(sidebar, "💰 Revenue & Leakage", self.show_revenue_page)
        self.create_nav_btn(sidebar, "🚨 Fraud Detection", self.show_fraud_page)

        # Data Generator Button
        tk.Button(sidebar, text="GENERATE DATA\n(10k Records)", bg="#ff6f00", fg="white",
                  font=("Arial", 10, "bold"), command=self.generate_data).pack(side="bottom", fill="x", pady=20,
                                                                               padx=20)

    def create_nav_btn(self, parent, text, command):
        tk.Button(parent, text=text, bg="#1976d2", fg="white", font=("Arial", 12),
                  bd=0, pady=10, command=command).pack(fill="x", pady=2)

    def create_main_area(self):
        self.main_frame = tk.Frame(self.root, bg="white")
        self.main_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def run_query(self, sql):
        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn)

    # ================= PAGE 1: TRAFFIC ANALYSIS =================
    def show_traffic_page(self):
        self.clear_main_frame()
        tk.Label(self.main_frame, text="Network Traffic & Peak Load Analysis", font=("Arial", 18, "bold"),
                 bg="white").pack(pady=10)

        try:
            df = self.run_query("SELECT * FROM v_hourly_traffic ORDER BY hour_bucket LIMIT 100")
            if df.empty:
                tk.Label(self.main_frame, text="No Data. Click 'Generate Data' in sidebar.").pack()
                return

            # Plotting
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

            # Line Chart: Total Calls
            sns.lineplot(data=df, x='hour_bucket', y='total_calls', marker='o', ax=ax1, color='#0277bd')
            ax1.set_title("Hourly Call Volume")
            ax1.set_ylabel("Number of Calls")
            ax1.grid(True, linestyle='--')

            # Area Chart: Success vs Dropped
            ax2.fill_between(df['hour_bucket'], df['total_calls'], color='#81c784', label='Successful', alpha=0.5)
            ax2.fill_between(df['hour_bucket'], df['dropped_calls'], color='#e57373', label='Dropped', alpha=0.8)
            ax2.set_title("Network Stability (Success vs Dropped)")
            ax2.legend()

            self.embed_chart(fig)
        except Exception as e:
            tk.Label(self.main_frame, text=f"Error: {e}").pack()

    # ================= PAGE 2: REVENUE & LEAKAGE =================
    def show_revenue_page(self):
        self.clear_main_frame()
        tk.Label(self.main_frame, text="Revenue Assurance & Leakage", font=("Arial", 18, "bold"), bg="white").pack(
            pady=10)

        query = """
                SELECT plan_type, SUM(cost) as revenue, AVG(duration_sec) as avg_duration
                FROM cdr_logs c
                         JOIN subscribers s ON c.caller_num = s.phone_number
                GROUP BY plan_type \
                """
        try:
            df = self.run_query(query)
            if df.empty: return

            fig = plt.figure(figsize=(10, 6))
            ax = fig.add_subplot(111)

            sns.barplot(data=df, x='plan_type', y='revenue', palette='viridis', ax=ax)
            ax.set_title("Revenue by Subscriber Plan")
            ax.set_ylabel("Total Revenue ($)")

            # Add value labels
            for container in ax.containers:
                ax.bar_label(container, fmt='$%.2f')

            self.embed_chart(fig)
        except:
            pass

    # ================= PAGE 3: FRAUD DETECTION =================
    def show_fraud_page(self):
        self.clear_main_frame()
        tk.Label(self.main_frame, text="Fraud Detection Dashboard", font=("Arial", 18, "bold"), bg="white").pack(
            pady=10)

        # Run detection procedure first
        try:
            with db_engine.connect() as conn:
                conn.execute(sqlalchemy.text("CALL detect_telecom_fraud()"))
                conn.commit()
        except Exception as e:
            print(e)

        # Fetch Results
        query = """
                SELECT reason, severity, COUNT(*) as occurrence_count
                FROM billing_anomalies
                GROUP BY reason, severity
                ORDER BY occurrence_count DESC \
                """
        try:
            df = self.run_query(query)

            # Split Screen: Table and Chart
            top_frame = tk.Frame(self.main_frame)
            top_frame.pack(fill='x', pady=10)

            # Treeview
            cols = ("Reason", "Severity", "Count")
            tree = ttk.Treeview(top_frame, columns=cols, show='headings', height=8)
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=200)
            tree.pack(fill='x', padx=20)

            for _, row in df.iterrows():
                tree.insert("", "end", values=(row['reason'], row['severity'], row['occurrence_count']))

            # Chart
            fig = plt.figure(figsize=(10, 5))
            ax = fig.add_subplot(111)
            if not df.empty:
                sns.barplot(data=df, y='reason', x='occurrence_count', hue='severity', palette='Reds', ax=ax)
                ax.set_title("Top Detected Fraud Patterns")

            self.embed_chart(fig)

        except Exception as e:
            tk.Label(self.main_frame, text=f"Error: {e}").pack()

    def embed_chart(self, fig):
        canvas = FigureCanvasTkAgg(fig, master=self.main_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    # ================= DATA GENERATOR =================
    def generate_data(self):
        # Disable GUI while running
        messagebox.showinfo("Wait", "Generating 10,000 records. This may take 10-20 seconds.")

        fake = Faker()

        # 1. Create Subscribers
        subs = []
        for _ in range(500):  # 500 subscribers
            subs.append({
                'phone_number': fake.msisdn(),
                'plan_type': random.choice(['Prepaid', 'Postpaid', 'Enterprise']),
                'region': random.choice(['NA', 'EU', 'AS'])
            })
        df_subs = pd.DataFrame(subs)
        df_subs.to_sql('subscribers', db_engine, if_exists='append', index=False, method='multi')

        # 2. Create Calls
        calls = []
        phone_nums = df_subs['phone_number'].tolist()

        start_date = datetime.datetime(2024, 1, 1)

        for _ in range(10000):  # 10k Calls
            caller = random.choice(phone_nums)
            receiver = fake.msisdn()
            duration = random.randint(10, 1200)  # up to 20 mins

            # Logic: Calculate Cost
            cost = round(duration * 0.05, 2)

            # INJECT ANOMALY: Revenue Leakage (Long call, 0 cost)
            if random.random() < 0.02:
                duration = 1500
                cost = 0.00

            calls.append({
                'caller_num': caller,
                'receiver_num': receiver,
                'call_start': start_date + datetime.timedelta(minutes=random.randint(0, 120000)),
                'duration_sec': duration,
                'call_type': 'Voice',
                'cost': cost,
                'tower_id': f"TWR-{random.randint(100, 999)}",
                'status': random.choice(['Success', 'Success', 'Success', 'Dropped'])
            })

        df_calls = pd.DataFrame(calls)
        df_calls.to_sql('cdr_logs', db_engine, if_exists='append', index=False, method='multi')

        messagebox.showinfo("Success", "Data Generation Complete! Refresh the pages.")


if __name__ == "__main__":
    root = tk.Tk()
    app = TelecomAnalyticsApp(root)
    root.mainloop()