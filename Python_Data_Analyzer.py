import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# === CONFIGURATION ===
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Change this
    'password': 'varrie75',  # Change this
    'database': 'student_db'
}


def fetch_data():
    """Connects to MySQL and fetches data into a Pandas DataFrame."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        query = "SELECT * FROM student_results"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None


def analyze_data(df):
    if df is None or df.empty:
        print("No data found to analyze.")
        return

    # Calculate Total and Average in Python (Data Processing)
    df['total_score'] = df['math'] + df['science'] + df['english']
    df['average'] = df['total_score'] / 3

    print("\n=== DATA STATISTICS ===")
    print(df.describe())

    print("\n=== TOP PERFORMERS ===")
    print(df.nlargest(3, 'total_score')[['name', 'total_score', 'average']])

    return df


def generate_charts(df):
    if df is None or df.empty:
        return

    sns.set(style="whitegrid")

    # Figure 1: Subject Performance Comparison
    plt.figure(figsize=(10, 6))
    df_melted = df.melt(id_vars=['name'], value_vars=['math', 'science', 'english'],
                        var_name='Subject', value_name='Score')

    sns.barplot(x='name', y='Score', hue='Subject', data=df_melted)
    plt.title('Student Performance by Subject')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    # Figure 2: Class Average Distribution (Histogram)
    plt.figure(figsize=(8, 5))
    sns.histplot(df['average'], bins=5, kde=True, color='purple')
    plt.title('Distribution of Average Grades')
    plt.xlabel('Average Score')
    plt.show()


if __name__ == "__main__":
    print("Fetching data from MySQL...")
    dataframe = fetch_data()

    print("Analyzing data...")
    processed_df = analyze_data(dataframe)

    print("Generating charts...")
    generate_charts(processed_df)