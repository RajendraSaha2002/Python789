import mysql.connector
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import datetime
import sys

# DB CONFIGURATION
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'varrie75',
    'database': 'inventory_ml'
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def train_and_predict():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Fetching product IDs...")
    cursor.execute("SELECT id FROM products")
    product_ids = [row[0] for row in cursor.fetchall()]

    for pid in product_ids:
        # Fetch history for this product
        query = "SELECT recorded_date, price FROM price_history WHERE product_id = %s ORDER BY recorded_date ASC"
        df = pd.read_sql(query, conn, params=(pid,))

        if len(df) < 2:
            print(f"Skipping Product {pid}: Not enough data points (needs at least 2).")
            continue

        # Data Preprocessing
        # Linear Regression needs numbers, not dates. Convert date to ordinal.
        df['date_ordinal'] = pd.to_datetime(df['recorded_date']).apply(lambda date: date.toordinal())

        X = df[['date_ordinal']]
        y = df['price']

        # Train Model
        model = LinearRegression()
        model.fit(X, y)

        # Predict for 'Tomorrow'
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        tomorrow_ordinal = np.array([[tomorrow.toordinal()]])

        predicted_price = model.predict(tomorrow_ordinal)[0]

        # Round to 2 decimal places
        predicted_price = round(float(predicted_price), 2)

        print(f"Product {pid}: Trend predicted price is ${predicted_price}")

        # Update Database
        update_query = "UPDATE products SET predicted_next_price = %s WHERE id = %s"
        cursor.execute(update_query, (predicted_price, pid))
        conn.commit()

    print("All predictions updated successfully.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    try:
        train_and_predict()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)