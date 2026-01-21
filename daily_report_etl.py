import mysql.connector
import pandas as pd
import sys

# DB CONFIGURATION
# UPDATE PASSWORD HERE
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'varrie75', # <--- UPDATE THIS
    'database': 'sales_db'
}

def run_etl_process():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to Database...")

        # 1. EXTRACT: Get all raw sales data
        query = "SELECT * FROM sales_raw"
        df = pd.read_sql(query, conn)

        if df.empty:
            print("No sales data found to process.")
            return

        # 2. TRANSFORM: Aggregation Logic
        # Group by Date
        summary = df.groupby('sale_date').agg(
            total_revenue=('amount', 'sum'),
            total_items=('quantity', 'sum'),
            # Logic to find top selling product by frequency
            top_product=('product_name', lambda x: x.mode().iloc[0] if not x.mode().empty else "N/A")
        ).reset_index()

        print(f"Processed {len(summary)} daily reports.")

        # 3. LOAD: Upsert into Summary Table
        insert_query = """
        INSERT INTO sales_summary (report_date, total_revenue, total_items_sold, top_product)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            total_revenue = VALUES(total_revenue),
            total_items_sold = VALUES(total_items_sold),
            top_product = VALUES(top_product),
            last_calculated = NOW()
        """

        for _, row in summary.iterrows():
            vals = (
                row['sale_date'],
                float(row['total_revenue']),
                int(row['total_items']),
                str(row['top_product'])
            )
            cursor.execute(insert_query, vals)

        conn.commit()
        print("ETL Job Finished Successfully.")

    except mysql.connector.Error as err:
        if err.errno == 1045:
            print("AUTH ERROR: Check password in daily_report_etl.py")
        else:
            print(f"Error: {err}")
        sys.exit(1)
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

if __name__ == "__main__":
    run_etl_process()