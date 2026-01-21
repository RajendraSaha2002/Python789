import mysql.connector
import pandas as pd
from sklearn.ensemble import IsolationForest
import sys

# DB CONFIGURATION
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'varrie75',  # <--- UPDATE THIS
    'database': 'banking_db'
}


def detect_fraud():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to Database...")

        # 1. Fetch Data
        # We need unchecked transactions to flag, AND historical data to train the model
        query = "SELECT id, amount FROM transactions"
        df = pd.read_sql(query, conn)

        if df.empty:
            print("No transactions found.")
            return

        # 2. Train ML Model (Isolation Forest)
        # Isolation Forest is great for detecting anomalies (outliers)
        model = IsolationForest(contamination=0.1, random_state=42)

        # We train on 'amount'. In a real app, you'd use frequency, location, etc.
        # Reshape data for sklearn
        X = df[['amount']]
        model.fit(X)

        # 3. Predict Anomalies
        df['anomaly'] = model.predict(X)
        # -1 is anomaly (fraud), 1 is normal

        # 4. Process Unchecked Transactions
        unchecked_query = "SELECT id, amount FROM transactions WHERE is_checked_for_fraud = FALSE"
        unchecked_df = pd.read_sql(unchecked_query, conn)

        if unchecked_df.empty:
            print("No new transactions to check.")
            return

        print(f"Checking {len(unchecked_df)} new transactions...")

        for _, row in unchecked_df.iterrows():
            tid = row['id']
            amount = row['amount']

            # Use the trained model to predict this specific transaction
            is_anomaly = model.predict([[amount]])[0]

            reason = "Normal"
            if is_anomaly == -1:
                reason = "ML Alert: Unusual Amount (Anomaly)"

            # Hard Rule: Any transaction > $10,000 is automatically flagged
            if amount > 10000:
                reason = "Rule Alert: High Value Transaction (>$10k)"
                is_anomaly = -1  # Force flag

            # If flagged, insert into alerts
            if is_anomaly == -1:
                print(f"!!! Fraud Detected on Transaction {tid}: ${amount} ({reason})")
                alert_sql = "INSERT INTO fraud_alerts (transaction_id, reason) VALUES (%s, %s)"
                cursor.execute(alert_sql, (tid, reason))

            # Mark as checked
            mark_sql = "UPDATE transactions SET is_checked_for_fraud = TRUE WHERE id = %s"
            cursor.execute(mark_sql, (tid,))

        conn.commit()
        print("Fraud Detection Complete.")

    except mysql.connector.Error as err:
        if err.errno == 1045:
            print("AUTH ERROR: Check password in fraud_detector.py")
        else:
            print(f"Error: {err}")
        sys.exit(1)
    finally:
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    detect_fraud()