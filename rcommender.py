import mysql.connector
import pandas as pd
import sys

# DB CONFIGURATION
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'varrie75',  # <--- UPDATE THIS
    'database': 'ecommerce_db'
}


def generate_recommendations():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to Database...")

        # 1. Fetch Purchase History
        query = "SELECT user_id, product_id FROM orders"
        df = pd.read_sql(query, conn)

        if df.empty:
            print("No order history found.")
            return

        # 2. Collaborative Filtering Logic (User-Based)
        # Find users who are "similar" (bought the same things)

        # Get list of unique users and products
        users = df['user_id'].unique()

        recommendations = []  # List of tuples: (user_id, product_id, score)

        for user in users:
            # Products bought by current user
            my_products = set(df[df['user_id'] == user]['product_id'])

            if not my_products:
                continue

            scores = {}  # ProductID -> Count

            # Compare with every other user
            for other_user in users:
                if user == other_user:
                    continue

                other_products = set(df[df['user_id'] == other_user]['product_id'])

                # Intersection: What did we both buy?
                common = my_products.intersection(other_products)

                if common:
                    # If we have common interests, look at what they bought that I didn't
                    potential_recs = other_products - my_products

                    # Weight by how similar we are (len(common))
                    for product in potential_recs:
                        if product not in scores:
                            scores[product] = 0
                        scores[product] += len(common)

            # Store top recommendations
            for pid, score in scores.items():
                recommendations.append((int(user), int(pid), float(score)))

        # 3. Save to Database
        print(f"Generated {len(recommendations)} recommendations.")

        # Clear old recommendations
        cursor.execute("TRUNCATE TABLE recommendations")

        insert_sql = "INSERT INTO recommendations (user_id, product_id, score) VALUES (%s, %s, %s)"
        cursor.executemany(insert_sql, recommendations)

        conn.commit()
        print("Database updated successfully.")

    except mysql.connector.Error as err:
        if err.errno == 1045:
            print("AUTH ERROR: Check password in recommender.py")
        else:
            print(f"Error: {err}")
        sys.exit(1)
    finally:
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    generate_recommendations()