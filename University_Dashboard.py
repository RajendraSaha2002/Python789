import sys
import pandas as pd
import sqlalchemy
# We use PyQt6 here
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                             QPushButton, QTabWidget, QHeaderView)
from PyQt6.QtCore import Qt
# Matplotlib backend for PyQt6
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

# DB CONFIG
# REPLACE with your actual credentials
db_connection_str = 'postgresql+psycopg2://postgres:varrie75@localhost/postgres'
db_engine = sqlalchemy.create_engine(db_connection_str)


class UniversityDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("University ERP - Student & Faculty Portal")
        self.setGeometry(100, 100, 1200, 800)
        # Fix for some high DPI displays
        self.setStyleSheet("background-color: #f5f5f5; font-size: 12px;")

        # Main Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Header
        header = QLabel("🎓 University Analytics Dashboard")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab 1: Academic Performance
        self.tab_performance = QWidget()
        self.setup_performance_tab()
        tabs.addTab(self.tab_performance, "📈 Performance Analytics")

        # Tab 2: Financial Status
        self.tab_finance = QWidget()
        self.setup_finance_tab()
        tabs.addTab(self.tab_finance, "💰 Fee Status")

    def run_query(self, sql):
        try:
            with db_engine.connect() as conn:
                return pd.read_sql(sql, conn)
        except Exception as e:
            print(f"Database Error: {e}")
            return pd.DataFrame()

    def setup_performance_tab(self):
        layout = QHBoxLayout(self.tab_performance)

        # Left: Data Table
        table_layout = QVBoxLayout()
        lbl_table = QLabel("Student Course Data")
        lbl_table.setStyleSheet("font-size: 16px; font-weight: bold;")
        table_layout.addWidget(lbl_table)

        self.perf_table = QTableWidget()
        self.perf_table.setColumnCount(3)
        self.perf_table.setHorizontalHeaderLabels(["Student", "Course", "Avg Score"])
        self.perf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.perf_table)

        btn_refresh = QPushButton("Refresh Data")
        btn_refresh.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        btn_refresh.clicked.connect(self.load_performance_data)
        table_layout.addWidget(btn_refresh)

        layout.addLayout(table_layout, 1)

        # Right: Chart
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, 1)

        self.load_performance_data()

    def load_performance_data(self):
        # Fetch Data from View
        df = self.run_query("SELECT * FROM v_student_performance")

        # Populate Table
        self.perf_table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.perf_table.setItem(i, 0, QTableWidgetItem(str(row['student_name'])))
            self.perf_table.setItem(i, 1, QTableWidgetItem(str(row['course_name'])))
            self.perf_table.setItem(i, 2, QTableWidgetItem(f"{row['avg_score']:.2f}"))

        # Update Chart
        self.ax.clear()
        if not df.empty:
            # Bar chart: Avg Score per Course
            courses = df['course_name'].unique()
            scores = df.groupby('course_name')['avg_score'].mean()
            self.ax.bar(courses, scores, color=['#e74c3c', '#2ecc71', '#f1c40f'])
            self.ax.set_title("Average Course Performance")
            self.ax.set_ylabel("Score")
            self.ax.grid(True, axis='y', linestyle='--', alpha=0.7)

        self.canvas.draw()

    def setup_finance_tab(self):
        layout = QVBoxLayout(self.tab_finance)

        lbl = QLabel("Fee Payment Status")
        lbl.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        layout.addWidget(lbl)

        self.fee_table = QTableWidget()
        self.fee_table.setColumnCount(4)
        self.fee_table.setHorizontalHeaderLabels(["Student ID", "Amount Due", "Due Date", "Status"])
        self.fee_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.fee_table)

        # Load Fee Data
        df = self.run_query("SELECT student_id, amount, due_date, status FROM fees")
        self.fee_table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.fee_table.setItem(i, 0, QTableWidgetItem(str(row['student_id'])))
            self.fee_table.setItem(i, 1, QTableWidgetItem(f"${row['amount']}"))
            self.fee_table.setItem(i, 2, QTableWidgetItem(str(row['due_date'])))

            status_item = QTableWidgetItem(row['status'])
            if row['status'] == 'Pending':
                status_item.setBackground(Qt.GlobalColor.yellow)
            elif row['status'] == 'Paid':
                status_item.setBackground(Qt.GlobalColor.green)

            self.fee_table.setItem(i, 3, status_item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UniversityDashboard()
    window.show()
    sys.exit(app.exec())