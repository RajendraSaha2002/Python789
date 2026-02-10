import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import sqlalchemy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from math import pi

# 1. DB CONNECTION
# REPLACE with your actual credentials
db_connection_str = 'postgresql+psycopg2://postgres:varrie75@localhost/postgres'
db_engine = sqlalchemy.create_engine(db_connection_str)


class UniversityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart University Analytics Platform")
        self.root.geometry("1100x700")

        # Style
        style = ttk.Style()
        style.theme_use('clam')

        # Tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create Tab Frames
        self.tab_student = ttk.Frame(self.notebook)
        self.tab_corr = ttk.Frame(self.notebook)
        self.tab_dept = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_student, text="Student Risk & Performance")
        self.notebook.add(self.tab_corr, text="Attendance Analysis")
        self.notebook.add(self.tab_dept, text="Department Rankings")

        # Load Tabs
        self.setup_student_tab()
        self.setup_corr_tab()
        self.setup_dept_tab()

    def get_data(self, query):
        try:
            with db_engine.connect() as conn:
                return pd.read_sql(query, conn)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            return pd.DataFrame()

    # ================= STUDENT TAB =================
    def setup_student_tab(self):
        # Controls
        control_frame = ttk.Frame(self.tab_student)
        control_frame.pack(side='left', fill='y', padx=10, pady=10)

        ttk.Label(control_frame, text="Select Student ID:", font=('Arial', 12, 'bold')).pack(pady=5)

        # Populate Listbox
        df_students = self.get_data("SELECT student_id, last_name, current_gpa FROM students ORDER BY student_id")
        self.student_list = tk.Listbox(control_frame, height=25, width=20)
        for _, row in df_students.iterrows():
            self.student_list.insert(tk.END, f"ID {row['student_id']}: {row['last_name']} ({row['current_gpa']})")
        self.student_list.pack(pady=5)
        self.student_list.bind('<<ListboxSelect>>', self.analyze_student)

        # Risk Display
        self.risk_frame = ttk.LabelFrame(control_frame, text="Dropout Risk Analysis")
        self.risk_frame.pack(fill='x', pady=20)
        self.lbl_risk = ttk.Label(self.risk_frame, text="Select a student...", font=('Arial', 10))
        self.lbl_risk.pack(padx=5, pady=5)

        # Chart Area
        self.student_chart_frame = ttk.Frame(self.tab_student)
        self.student_chart_frame.pack(side='right', fill='both', expand=True)

    def analyze_student(self, event):
        selection = self.student_list.curselection()
        if not selection: return

        s_str = self.student_list.get(selection[0])
        s_id = s_str.split(":")[0].replace("ID ", "")

        # 1. Fetch Performance Logic
        query = f"""
            SELECT c.name as subject, er.score, a.attendance_pct
            FROM exam_results er
            JOIN courses c ON er.course_id = c.course_id
            JOIN attendance a ON er.student_id = a.student_id AND er.course_id = a.course_id
            WHERE er.student_id = {s_id}
        """
        df = self.get_data(query)

        # 2. Risk Logic (Python Side)
        avg_score = df['score'].mean()
        avg_att = df['attendance_pct'].mean()
        risk_level = "LOW"
        color = "green"

        if avg_att < 60 or avg_score < 50:
            risk_level = "CRITICAL"
            color = "red"
        elif avg_att < 75 or avg_score < 65:
            risk_level = "MODERATE"
            color = "orange"

        self.lbl_risk.config(
            text=f"GPA Score: {avg_score:.1f}\nAvg Attendance: {avg_att:.1f}%\n\nRisk Level: {risk_level}",
            foreground=color
        )

        # 3. Radar Chart Visualization
        for widget in self.student_chart_frame.winfo_children():
            widget.destroy()

        # Radar Chart Prep
        categories = list(df['subject'])
        values = list(df['score'])

        # Close the loop for radar chart
        values += values[:1]
        angles = [n / float(len(categories)) * 2 * pi for n in range(len(categories))]
        angles += angles[:1]

        fig = plt.figure(figsize=(5, 5))
        ax = fig.add_subplot(111, polar=True)
        ax.plot(angles, values, linewidth=1, linestyle='solid')
        ax.fill(angles, values, 'b', alpha=0.1)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_title(f"Performance Profile: Student {s_id}")

        canvas = FigureCanvasTkAgg(fig, master=self.student_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    # ================= CORRELATION TAB =================
    def setup_corr_tab(self):
        query = """
                SELECT s.student_id, s.current_gpa, AVG(a.attendance_pct) as avg_attendance
                FROM students s
                         JOIN attendance a ON s.student_id = a.student_id
                GROUP BY s.student_id, s.current_gpa \
                """
        df = self.get_data(query)

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.scatterplot(data=df, x='avg_attendance', y='current_gpa', hue='current_gpa', palette='viridis', ax=ax,
                        s=100)
        ax.set_title("Correlation: Attendance vs GPA (Real-time DB Data)")
        ax.set_xlabel("Average Attendance %")
        ax.set_ylabel("Student GPA")
        ax.grid(True)

        canvas = FigureCanvasTkAgg(fig, master=self.tab_corr)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True, padx=20, pady=20)

    # ================= DEPT TAB =================
    def setup_dept_tab(self):
        query = "SELECT * FROM v_dept_performance"
        df = self.get_data(query)

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.barplot(data=df, x='department', y='avg_dept_gpa', palette='magma', ax=ax)
        ax.set_title("Department Performance Ranking")
        ax.set_ylabel("Average GPA")

        # Add values on top of bars
        for container in ax.containers:
            ax.bar_label(container)

        canvas = FigureCanvasTkAgg(fig, master=self.tab_dept)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True, padx=20, pady=20)


if __name__ == "__main__":
    root = tk.Tk()
    app = UniversityApp(root)
    root.mainloop()