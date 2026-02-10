import pandas as pd
import sqlalchemy
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx

# 1. DB SETUP
# REPLACE with your actual credentials
db_connection_str = 'postgresql+psycopg2://postgres:varrie75@localhost/postgres'
db_engine = sqlalchemy.create_engine(db_connection_str)


def run_query(sql):
    with db_engine.connect() as conn:
        return pd.read_sql(sql, conn)


def main():
    print("--- SQL-Driven Recommendation Engine ---")

    # INPUT: Select a User ID to recommend for
    target_user_id = 5
    print(f"Generating Recommendations for User ID: {target_user_id}...")

    # 1. GET RECOMMENDATIONS (Calling SQL Function)
    sql_rec = f"SELECT * FROM get_recommendations({target_user_id})"
    df_recs = run_query(sql_rec)

    print("\nTop Recommendations:")
    print(df_recs[['movie_title', 'predicted_score', 'reasoning']])

    # ==========================================
    # VISUALIZATION 1: User Similarity Cluster (Network Graph)
    # Shows which users are "neighbors" in the database
    # ==========================================
    print("\nGenerating Cluster Map...")
    sql_sim = """
              SELECT user_a, user_b, similarity_score
              FROM mv_user_similarity
              WHERE similarity_score > 0.5 LIMIT 100; \
              """
    df_sim = run_query(sql_sim)

    if not df_sim.empty:
        plt.figure(figsize=(10, 8))
        G = nx.from_pandas_edgelist(df_sim, 'user_a', 'user_b', ['similarity_score'])
        pos = nx.spring_layout(G, k=0.3)

        nx.draw_networkx_nodes(G, pos, node_size=500, node_color='skyblue')
        nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5)
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")

        plt.title(f"User Similarity Network (Who shares taste with whom?)", fontsize=14)
        plt.axis('off')
        plt.show()
    else:
        print("Not enough similarity data for graph.")

    # ==========================================
    # VISUALIZATION 2: Recommendation Confidence (Bar Chart)
    # ==========================================
    if not df_recs.empty:
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df_recs, x='predicted_score', y='movie_title', palette='viridis')
        plt.title(f'Recommendation Confidence Score for User {target_user_id}', fontsize=14)
        plt.xlabel('Predicted Rating (1-5)')
        plt.ylabel('Movie Title')
        plt.xlim(0, 5)  # Rating scale
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.show()
    else:
        print("No recommendations found (User might have watched everything or has no similar peers).")


if __name__ == "__main__":
    main()