import mysql.connector
import pandas as pd
from fpdf import FPDF
import os
import sys

# DB CONFIGURATION
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'varrie75',  # <--- UPDATE THIS
    'database': 'attendance_db'
}


class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Monthly Attendance Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def generate_report():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)

        # 1. Fetch Joined Data
        query = """
                SELECT e.name, e.department, a.date, a.in_time, a.out_time, a.status
                FROM attendance a
                         JOIN employees e ON a.employee_id = e.id
                ORDER BY e.name, a.date \
                """
        df = pd.read_sql(query, conn)

        if df.empty:
            print("No data found.")
            return

        # 2. Calculate Summaries
        summary = df.groupby('name').agg(
            total_days=('date', 'count'),
            late_arrivals=('status', lambda x: (x == 'Late').sum()),
            # Simple placeholder for absent logic
            present_days=('status', lambda x: (x == 'Present').sum() + (x == 'Late').sum())
        ).reset_index()

        # 3. Generate PDF
        pdf = PDFReport()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Summary Table
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 10, 'Executive Summary', 0, 1, 'L')
        pdf.set_font("Arial", 'B', 10)

        # Headers
        pdf.cell(50, 10, 'Employee Name', 1, 0, 'C', True)
        pdf.cell(40, 10, 'Total Days', 1, 0, 'C', True)
        pdf.cell(40, 10, 'Present', 1, 0, 'C', True)
        pdf.cell(40, 10, 'Late Count', 1, 1, 'C', True)

        pdf.set_font("Arial", '', 10)
        for _, row in summary.iterrows():
            pdf.cell(50, 10, str(row['name']), 1)
            pdf.cell(40, 10, str(row['total_days']), 1, 0, 'C')
            pdf.cell(40, 10, str(row['present_days']), 1, 0, 'C')
            pdf.cell(40, 10, str(row['late_arrivals']), 1, 1, 'C')

        pdf.ln(10)

        # Detailed Logs
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, 'Detailed Logs', 0, 1, 'L')
        pdf.set_font("Arial", size=9)

        # Headers
        pdf.cell(40, 10, 'Name', 1, 0, 'C', True)
        pdf.cell(30, 10, 'Date', 1, 0, 'C', True)
        pdf.cell(30, 10, 'In Time', 1, 0, 'C', True)
        pdf.cell(30, 10, 'Out Time', 1, 0, 'C', True)
        pdf.cell(30, 10, 'Status', 1, 1, 'C', True)

        pdf.set_font("Arial", '', 9)
        for _, row in df.iterrows():
            # Handle None values for times
            in_t = str(row['in_time']) if row['in_time'] else "--"
            out_t = str(row['out_time']) if row['out_time'] else "--"

            pdf.cell(40, 10, str(row['name']), 1)
            pdf.cell(30, 10, str(row['date']), 1)
            pdf.cell(30, 10, in_t, 1)
            pdf.cell(30, 10, out_t, 1)

            # Color code Status
            if row['status'] == 'Late':
                pdf.set_text_color(255, 0, 0)
            else:
                pdf.set_text_color(0, 0, 0)
            pdf.cell(30, 10, str(row['status']), 1, 1, 'C')
            pdf.set_text_color(0, 0, 0)

        # Save PDF
        output_filename = os.path.abspath("attendance_report.pdf")
        pdf.output(output_filename)

        # PRINT THE FILENAME so Java can read it
        print(output_filename)

    except mysql.connector.Error as err:
        if err.errno == 1045:
            print("AUTH ERROR")
        else:
            print(f"Error: {err}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    generate_report()