import mysql.connector
import sys

# DB CONFIGURATION
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'varrie75',  # <--- UPDATE THIS
    'database': 'health_db'
}


def calculate_risk(age, bmi, hr):
    # SIMPLE LOGIC MODEL (Rule-based AI)
    score = 0

    # BMI Factors
    if bmi > 30:
        score += 3  # Obese
    elif bmi > 25:
        score += 1  # Overweight

    # Heart Rate Factors
    if hr > 100:
        score += 2  # Tachycardia
    elif hr < 60:
        score += 1  # Bradycardia (simplified)

    # Age Factors
    if age > 50: score += 1
    if age > 70: score += 2

    # Determine Level
    if score >= 4: return "High"
    if score >= 2: return "Medium"
    return "Low"


def process_data():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to Database...")

        # Find logs where risk has not been calculated yet
        query = "SELECT id, age, bmi, heart_rate FROM health_logs WHERE risk_level = 'Pending'"
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            print("No new logs to analyze.")
            return

        print(f"Analyzing {len(rows)} new health logs...")

        for row in rows:
            log_id = row[0]
            age = row[1]
            bmi = row[2]
            hr = row[3]

            risk = calculate_risk(age, bmi, hr)

            # Update DB
            update_sql = "UPDATE health_logs SET risk_level = %s WHERE id = %s"
            cursor.execute(update_sql, (risk, log_id))
            print(f"Log ID {log_id}: Risk set to {risk}")

        conn.commit()
        print("All updates saved.")

    except mysql.connector.Error as err:
        if err.errno == 1045:
            print("AUTH ERROR: Check password in risk_predictor.py")
        else:
            print(f"Error: {err}")
        sys.exit(1)
    finally:
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    process_data()