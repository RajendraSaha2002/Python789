import mysql.connector
import pandas as pd
import sys

# DB CONFIGURATION
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'varrie75',
    'database': 'school_tracker'
}


def detect_patterns():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to Database...")

        # 1. Load all attendance data
        query = "SELECT student_id, status FROM attendance"
        df = pd.read_sql(query, conn)

        if df.empty:
            print("No attendance records found.")
            return

        # 2. Calculate Absence Rate
        # Group by student and count 'Absent' vs Total records
        summary = df.groupby('student_id').agg(
            total_days=('status', 'count'),
            absent_days=('status', lambda x: (x == 'Absent').sum())
        ).reset_index()

        # Calculate percentage
        summary['risk_score'] = (summary['absent_days'] / summary['total_days']) * 100

        # 3. Identify At-Risk Students (Threshold: > 20% absence)
        at_risk_students = summary[summary['risk_score'] > 20]

        print(f"Found {len(at_risk_students)} students at risk.")

        # 4. Update Alerts Table
        # Clear old alerts first to avoid duplicates for this demo
        cursor.execute("TRUNCATE TABLE risk_alerts")

        for _, row in at_risk_students.iterrows():
            student_id = int(row['student_id'])
            score = float(row['risk_score'])

            # Determine message
            message = "High Absence Rate"
            if score > 50:
                message = "CRITICAL: Chronic Absenteeism"
            elif score > 30:
                message = "WARNING: Frequent Absences"

            insert_query = """
                           INSERT INTO risk_alerts (student_id, risk_score, message)
                           VALUES (%s, %s, %s) \
                           """
            cursor.execute(insert_query, (student_id, score, message))
            print(f"Flagged Student ID {student_id} with {score:.1f}% absence.")

        conn.commit()
        print("Alerts updated successfully.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        sys.exit(1)
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    detect_patterns()