import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import sqlalchemy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns

# DB CONNECTION
# REPLACE with your actual credentials
db_connection_str = 'postgresql+psycopg2://postgres:varrie75@localhost/postgres'
db_engine = sqlalchemy.create_engine(db_connection_str)


class LegalAnalyticsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LexiAnalytics: Judicial Intelligence Platform")
        self.root.geometry("1400x900")
        self.root.configure(bg="#2c3e50")

        self.setup_header()
        self.setup_navigation()
        self.main_container = tk.Frame(self.root, bg="white")
        self.main_container.pack(fill='both', expand=True, padx=10, pady=10)

        # Load Landing Page
        self.show_dashboard()

    def setup_header(self):
        header = tk.Frame(self.root, bg="#34495e", height=70)
        header.pack(fill='x')
        tk.Label(header, text="⚖️ LexiAnalytics System", bg="#34495e", fg="#ecf0f1",
                 font=("Georgia", 24)).pack(side="left", padx=20, pady=15)

        tk.Button(header, text="Initialize 1M Records (DB)", bg="#e74c3c", fg="white",
                  font=("Arial", 10, "bold"), command=self.generate_db_data).pack(side="right", padx=20)

    def setup_navigation(self):
        nav_frame = tk.Frame(self.root, bg="#2c3e50")
        nav_frame.pack(fill='x')

        btn_style = {"bg": "#2c3e50", "fg": "white", "font": ("Arial", 12), "bd": 0, "activebackground": "#95a5a6"}

        tk.Button(nav_frame, text="🏛️ Court Overview", command=self.show_dashboard, **btn_style).pack(side="left",
                                                                                                      padx=20, pady=10)
        tk.Button(nav_frame, text="👨‍⚖️ Judge Performance", command=self.show_judge_analysis, **btn_style).pack(
            side="left", padx=20, pady=10)
        tk.Button(nav_frame, text="📈 Litigation Trends", command=self.show_trends, **btn_style).pack(side="left",
                                                                                                     padx=20, pady=10)

    def clear_container(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def run_query(self, sql):
        try:
            with db_engine.connect() as conn:
                return pd.read_sql(sql, conn)
        except Exception as e:
            # We fail silently here or return empty DF because alerts are handled elsewhere
            return pd.DataFrame()

    def generate_db_data(self):
        response = messagebox.askyesno("Confirm",
                                       "This will delete old data and generate 1,000,000 new records.\nThis takes about 30-60 seconds. Proceed?")
        if response:
            try:
                with db_engine.connect() as conn:
                    conn.execute(sqlalchemy.text("CALL generate_legal_data()"))
                    conn.commit()
                messagebox.showinfo("Success", "1 Million Records Generated Successfully!")
                # Refresh dashboard after generation
                self.show_dashboard()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ================= VIEW 1: COURT DASHBOARD =================
    def show_dashboard(self):
        self.clear_container()
        tk.Label(self.main_container, text="Court System Overview (Real-Time Aggregation)", font=("Arial", 18, "bold"),
                 bg="white").pack(pady=10)

        # 1. KPI Cards
        kpi_frame = tk.Frame(self.main_container, bg="white")
        kpi_frame.pack(fill='x', padx=20)

        # Get Counts (Fast due to Partitioning)
        try:
            total_cases = self.run_query("SELECT COUNT(*) as c FROM cases")['c'][0]
            avg_result = self.run_query("SELECT AVG(compensation_amount) as a FROM verdicts")['a'][0]

            # FIX: Check if result is None (which happens if table is empty)
            if avg_result is None:
                avg_comp = 0.0
            else:
                avg_comp = float(avg_result)

        except Exception as e:
            print(f"Data fetch error: {e}")
            total_cases = 0
            avg_comp = 0.0

        self.create_kpi_card(kpi_frame, "Total Case Archive", f"{total_cases:,.0f}", "#3498db")
        self.create_kpi_card(kpi_frame, "Avg Settlement", f"${avg_comp:,.2f}", "#27ae60")
        self.create_kpi_card(kpi_frame, "Active Judges", "50", "#8e44ad")

        # 2. Case Category Chart
        df_cat = self.run_query("SELECT category, COUNT(*) as count FROM cases GROUP BY category")

        if not df_cat.empty:
            fig = plt.figure(figsize=(10, 6))
            ax = fig.add_subplot(111)
            # Pie Chart
            ax.pie(df_cat['count'], labels=df_cat['category'], autopct='%1.1f%%', startangle=90,
                   colors=sns.color_palette("pastel"))
            ax.set_title("Distribution of Case Types")

            canvas = FigureCanvasTkAgg(fig, master=self.main_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=20, pady=20)
        else:
            tk.Label(self.main_container, text="No Data Available. Click 'Initialize 1M Records' above.",
                     font=("Arial", 12), bg="white", fg="red").pack(pady=20)

    def create_kpi_card(self, parent, title, value, color):
        frame = tk.Frame(parent, bg=color, width=250, height=100)
        frame.pack(side="left", padx=20, fill='both', expand=True)
        frame.pack_propagate(False)
        tk.Label(frame, text=title, bg=color, fg="white", font=("Arial", 10)).pack(pady=(20, 5))
        tk.Label(frame, text=value, bg=color, fg="white", font=("Arial", 20, "bold")).pack()

    # ================= VIEW 2: JUDGE PERFORMANCE =================
    def show_judge_analysis(self):
        self.clear_container()
        tk.Label(self.main_container, text="Judge Decision Patterns & Bias Analysis", font=("Arial", 18, "bold"),
                 bg="white").pack(pady=10)

        # Fetch Data from View
        query = "SELECT * FROM v_judge_stats ORDER BY total_cases DESC LIMIT 15"
        df = self.run_query(query)

        if df.empty:
            tk.Label(self.main_container, text="No Data Available. Click 'Initialize 1M Records' above.",
                     font=("Arial", 12), bg="white", fg="red").pack(pady=20)
            return

        fig = plt.figure(figsize=(12, 6))

        # Scatter Plot: Win Rate vs Complexity
        # Does the judge favor Plaintiffs in complex cases?
        ax = fig.add_subplot(111)
        sns.scatterplot(data=df, x='avg_complexity', y='plaintiff_win_rate',
                        size='total_cases', sizes=(100, 1000), hue='specialty', alpha=0.7, ax=ax)

        ax.set_title("Judge Behavior: Complexity vs Plaintiff Win Rate")
        ax.set_xlabel("Average Case Complexity (1-10)")
        ax.set_ylabel("Plaintiff Win Rate (0.0 - 1.0)")
        ax.axhline(0.5, color='gray', linestyle='--')  # Neutral line

        # Annotate top judges
        for line in range(0, df.shape[0]):
            ax.text(df.avg_complexity[line], df.plaintiff_win_rate[line],
                    df.name[line].split()[-1], horizontalalignment='left', size='small', color='black')

        canvas = FigureCanvasTkAgg(fig, master=self.main_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    # ================= VIEW 3: TRENDS =================
    def show_trends(self):
        self.clear_container()
        tk.Label(self.main_container, text="Historical Verdict Trends (5-Year)", font=("Arial", 18, "bold"),
                 bg="white").pack(pady=10)

        # Time Series Query
        query = """
                SELECT TO_CHAR(verdict_date, 'YYYY-MM') as month, outcome, COUNT(*) as count
                FROM verdicts
                WHERE verdict_date > '2020-01-01'
                GROUP BY 1, 2
                ORDER BY 1 \
                """
        df = self.run_query(query)
        if df.empty:
            tk.Label(self.main_container, text="No Data Available. Click 'Initialize 1M Records' above.",
                     font=("Arial", 12), bg="white", fg="red").pack(pady=20)
            return

        fig = plt.figure(figsize=(12, 6))
        ax = fig.add_subplot(111)

        sns.lineplot(data=df, x='month', y='count', hue='outcome', ax=ax)
        ax.set_title("Verdict Outcomes Over Time")
        ax.set_xticks(ax.get_xticks()[::6])  # Show fewer x-labels
        plt.xticks(rotation=45)

        canvas = FigureCanvasTkAgg(fig, master=self.main_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = LegalAnalyticsApp(root)
    root.mainloop()