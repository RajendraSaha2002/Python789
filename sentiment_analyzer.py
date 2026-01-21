import psycopg2
from textblob import TextBlob
import sys

# DB CONFIGURATION
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75', # <--- UPDATE THIS
    'dbname': 'chat_db',
    'port': 5432
}

def analyze_sentiment():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to Database...")

        # --- FIX ADDED: Create Table if it doesn't exist ---
        create_table_query = """
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_name VARCHAR(50) NOT NULL,
            message_text TEXT NOT NULL,
            sentiment_score DOUBLE PRECISION,
            sentiment_icon VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)
        conn.commit()
        # ---------------------------------------------------

        # 1. Fetch messages that haven't been analyzed yet (where icon is NULL)
        query = "SELECT id, message_text FROM messages WHERE sentiment_icon IS NULL"
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            print("No new messages to analyze.")
            return

        print(f"Analyzing {len(rows)} new messages...")

        for row in rows:
            msg_id = row[0]
            text = row[1]

            # 2. NLP Analysis using TextBlob
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            # Polarity range: -1.0 (Negative) to 1.0 (Positive)

            # 3. Determine Icon/Emotion
            if polarity > 0.3:
                icon = "😃" # Happy
            elif polarity < -0.3:
                icon = "😡" # Angry/Sad
            else:
                icon = "😐" # Neutral

            # 4. Update Database
            update_sql = "UPDATE messages SET sentiment_score = %s, sentiment_icon = %s WHERE id = %s"
            cursor.execute(update_sql, (polarity, icon, msg_id))
            print(f"ID {msg_id}: Score {polarity:.2f} -> {icon}")

        conn.commit()
        print("Analysis complete.")

    except psycopg2.Error as err:
        print(f"DB Error: {err}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    analyze_sentiment()