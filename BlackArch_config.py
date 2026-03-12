import psycopg2

def get_db_connection():
    # Update these credentials to match your PostgreSQL setup
    conn = psycopg2.connect(
        host="localhost",
        database="blackarch_dash",
        user="postgres",
        password="varrie75"
    )
    return conn